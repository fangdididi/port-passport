#!/usr/bin/env python3
"""portscan.py - find portability hazards in a source tree before you port it.

Walks a directory, matches each text file against a catalogue of patterns that
commonly break when code moves to another OS, CPU architecture, runtime or
browser, and prints a hazard inventory grouped by layer.

Usage:
  python3 scripts/portscan.py PATH [--target linux|macos|windows|ios|android|wasm|arm64|any]
                                   [--json] [--max-per-rule N] [--exclude DIR ...]

The scan is a triage aid, not a verdict: a hit means "look here", and silence
does not mean "portable". Standard library only, Python 3.8+.
"""
import argparse, json, os, re, sys
from collections import OrderedDict

# (rule_id, layer, regex, why, targets-it-matters-for)
RULES = [
    # filesystem
    ("abs-unix-path", "filesystem", r"""["'](/usr/|/etc/|/var/|/tmp/|/home/|/opt/|/proc/|/sys/)""",
     "Hard-coded Unix absolute path; missing or sandboxed on other systems.", {"windows", "ios", "android", "wasm", "macos"}),
    ("abs-win-path", "filesystem", r"""["'][A-Za-z]:\\\\""",
     "Hard-coded Windows drive path.", {"linux", "macos", "ios", "android", "wasm"}),
    ("backslash-join", "filesystem", r"""\+\s*["']\\\\["']|["']\\\\["']\s*\+""",
     "Path built with a literal backslash; use the platform path API.", {"linux", "macos", "ios", "android", "wasm"}),
    ("slash-join", "filesystem", r"""\+\s*["']/["']\s*\+""",
     "Path built by string concatenation with '/'; prefer a path-join API.", {"windows"}),
    ("home-tilde", "filesystem", r"""["']~/""",
     "Literal '~/' is not expanded by most APIs and has no meaning in sandboxes.", {"windows", "ios", "android", "wasm"}),
    ("dev-null", "filesystem", r"""/dev/null|\bNUL\b""",
     "Null device name differs per OS.", {"any"}),
    # text & encoding
    ("crlf-assume", "text", r"""\\r\\n|split\(\s*["']\\n["']\s*\)""",
     "Line-ending assumption; CRLF vs LF differs by OS and git settings.", {"any"}),
    ("no-encoding-open", "text", r"""\bopen\([^)]*["'][rwa]t?["']\s*\)""",
     "Text file opened without an explicit encoding; default differs per OS locale.", {"windows", "any"}),
    ("locale-dependent", "text", r"""\bsetlocale\b|\blocale\.getpreferredencoding\b|toLocale(Lower|Upper)Case|\.lower\(\)\s*==""",
     "Locale-dependent behaviour; results change with system language.", {"any"}),
    # process & shell
    ("shell-out", "process", r"""\b(os\.system|subprocess\.(run|call|Popen|check_output)|child_process|exec\.Command|Runtime\.getRuntime\(\)\.exec|popen|system\()""",
     "Spawns an external program; the program, its flags or a shell may not exist on the target (and not at all on iOS/wasm).", {"any"}),
    ("unix-tool", "process", r"""["'](sh|bash|grep|sed|awk|cp|rm|mv|ls|chmod|which|open|xdg-open|cmd(\.exe)?|powershell)\b""",
     "Invokes a platform-specific command-line tool by name.", {"any"}),
    ("signals", "process", r"""\bSIG(KILL|TERM|HUP|USR1|USR2|CHLD|PIPE|ALRM)\b|\bsignal\.signal\b|\bkill\(""",
     "POSIX signal use; semantics differ or are absent on Windows/wasm/mobile.", {"windows", "wasm", "ios", "android"}),
    ("fork", "process", r"""\bfork\(\)|\bos\.fork\b|\bexecv[pe]?\(""",
     "fork/exec is unavailable on Windows, iOS and wasm.", {"windows", "ios", "wasm"}),
    # OS api
    ("platform-branch", "os-api", r"""sys\.platform|os\.name\s*==|process\.platform|runtime\.GOOS|#\s*if(def)?\s+(_WIN32|__APPLE__|__linux__|__ANDROID__|TARGET_OS_\w+)|cfg\(target_os|Environment\.OSVersion""",
     "Existing platform branch: inventory every arm and decide what the new target takes.", {"any"}),
    ("win-api", "os-api", r"""#include\s*<windows\.h>|\bwinreg\b|\bHKEY_|\bCreateFile[AW]?\b|\bLoadLibrary[AW]?\b""",
     "Windows-only API.", {"linux", "macos", "ios", "android", "wasm"}),
    ("posix-api", "os-api", r"""#include\s*<(unistd|sys/mman|sys/ioctl|dlfcn|pthread)\.h>|\bdlopen\b|\bmmap\(|\bioctl\(""",
     "POSIX/Unix API; needs a shim on Windows and is restricted on wasm/iOS.", {"windows", "wasm", "ios"}),
    ("procfs", "os-api", r"""/proc/(self|cpuinfo|meminfo|\d)""",
     "Linux procfs; absent on macOS, Windows, iOS, wasm.", {"macos", "windows", "ios", "wasm", "android"}),
    ("env-var", "os-api", r"""["'](HOME|USERPROFILE|APPDATA|XDG_\w+|TMPDIR|TEMP|PATH)["']""",
     "Environment variable whose name or presence is OS-specific.", {"any"}),
    # cpu / abi
    ("x86-intrinsic", "cpu-abi", r"""#include\s*<(immintrin|emmintrin|xmmintrin|x86intrin)\.h>|\b_mm\d*_\w+|__asm__|\basm\s*\(|\b__cpuid""",
     "x86 intrinsics or inline assembly; will not build for ARM64/wasm.", {"arm64", "ios", "android", "wasm", "macos"}),
    ("word-size", "cpu-abi", r"""\bsizeof\s*\(\s*(long|void\s*\*|size_t)\s*\)|\bunsigned\s+long\b|\(int\)\s*\(?\w*ptr|\bint\s*\)\s*&""",
     "Size of long/pointer differs (LP64 vs LLP64 vs wasm32); pointer-to-int casts truncate.", {"windows", "wasm", "any"}),
    ("endianness", "cpu-abi", r"""\bstruct\.(pack|unpack)\(\s*["'][^<>!=@]|\bhtonl\b|\bntohl\b|__BYTE_ORDER|reinterpret_cast<\s*(uint|int)\d+_t\s*\*>""",
     "Byte-order-sensitive binary I/O or reinterpretation.", {"any"}),
    ("packed-struct", "cpu-abi", r"""#pragma\s+pack|__attribute__\s*\(\(\s*packed|#\[repr\(packed""",
     "Packed/explicit layout; check alignment rules and unaligned-access faults on the target.", {"arm64", "wasm", "any"}),
    ("char-sign", "cpu-abi", r"""\bchar\s+\w+\s*=\s*-\d|\(char\)\s*0x[89a-fA-F]""",
     "Plain char signedness differs between x86 and ARM.", {"arm64", "android", "ios"}),
    # concurrency & time
    ("busy-sleep", "time-threads", r"""\bsleep\(\s*0(\.\d+)?\s*\)|\bSleep\(\s*\d+\s*\)|\busleep\(""",
     "Sleep-based timing or polling; schedulers and timer resolution differ per OS.", {"any"}),
    ("thread-affinity", "time-threads", r"""\bsched_setaffinity\b|\bSetThreadAffinityMask\b|\bpthread_setaffinity_np\b|\bthread_policy_set\b""",
     "Thread affinity API is OS-specific and often unavailable on mobile.", {"any"}),
    ("wall-clock", "time-threads", r"""\btime\.time\(\)|\bDate\.now\(\)|\bgettimeofday\b|\bGetTickCount\b""",
     "Wall-clock used for timing; prefer a monotonic clock that exists on every target.", {"any"}),
    # graphics / audio / input
    ("graphics-api", "media-io", r"""\b(OpenGL|glBegin|glDraw\w*|GL_\w+|Direct3D|D3D1[12]|ID3D\w+|Vulkan|vk[A-Z]\w+|MTLDevice|DirectX)\b""",
     "Graphics API tied to specific platforms (OpenGL deprecated on Apple, D3D Windows-only, Metal Apple-only).", {"any"}),
    ("audio-api", "media-io", r"""\b(ALSA|snd_pcm_\w+|PulseAudio|WASAPI|DirectSound|CoreAudio|AudioUnit|OpenSL)\b""",
     "Platform audio backend.", {"any"}),
    ("input-api", "media-io", r"""\b(XInput|DirectInput|evdev|GetAsyncKeyState|IOHIDManager)\b""",
     "Platform input backend.", {"any"}),
    # build & packaging
    ("native-ext", "build", r"""\.(so|dll|dylib)["']|ctypes\.(CDLL|WinDLL)|\bffi\.|System\.loadLibrary""",
     "Loads a native binary; needs a build per target architecture and OS.", {"any"}),
    ("compiler-specific", "build", r"""__declspec|__attribute__|#pragma\s+(warning|comment)|_MSC_VER|__GNUC__""",
     "Compiler-specific extension; check the target toolchain.", {"any"}),
    ("jit-or-eval", "build", r"""\bmprotect\(.*PROT_EXEC|\bVirtualProtect\b|MAP_JIT|\bnew Function\(|\beval\(""",
     "Runtime code generation; forbidden or entitlement-gated on iOS, restricted in browsers.", {"ios", "wasm"}),
    # network & storage
    ("localhost-socket", "network-storage", r"""\b(AF_UNIX|unix://|named pipe|\\\\\\\\\.\\\\pipe)""",
     "Local IPC mechanism differs per OS; absent in browsers.", {"any"}),
    ("sync-fs-in-browser", "network-storage", r"""\breadFileSync\b|\bwriteFileSync\b|\bfs\.\w+Sync\b""",
     "Synchronous filesystem access; no real filesystem in browsers and blocks UI threads on mobile.", {"wasm", "ios", "android"}),
]

TEXT_EXT = {'.c', '.h', '.cc', '.cpp', '.cxx', '.hpp', '.hh', '.m', '.mm', '.rs', '.go', '.py', '.js', '.mjs',
            '.cjs', '.ts', '.tsx', '.jsx', '.java', '.kt', '.kts', '.swift', '.cs', '.rb', '.php', '.lua', '.sh',
            '.bash', '.ps1', '.bat', '.cmd', '.cmake', '.mk', '.gradle', '.toml', '.yaml', '.yml', '.json', '.ini',
            '.cfg', '.dart', '.zig', '.scala', '.pl'}
TEXT_NAMES = {'Makefile', 'CMakeLists.txt', 'Dockerfile', 'Cargo.toml', 'package.json', 'build.gradle'}
DEFAULT_EXCLUDE = {'.git', 'node_modules', 'vendor', 'third_party', 'build', 'dist', 'target', '.venv', 'venv',
                   '__pycache__', '.idea', '.vscode', 'Pods', 'DerivedData'}
LAYER_ORDER = ["build", "cpu-abi", "os-api", "filesystem", "text", "process", "time-threads", "media-io",
               "network-storage"]
COMPILED = [(rid, layer, re.compile(rx), why, tg) for rid, layer, rx, why, tg in RULES]


def applies(rule_targets, target):
    return target == "any" or "any" in rule_targets or target in rule_targets


def scan(root, target="any", excludes=(), max_per_rule=20):
    excl = DEFAULT_EXCLUDE | set(excludes)
    hits = OrderedDict()
    files_scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in excl and not d.startswith('.'))
        for fn in sorted(filenames):
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT and fn not in TEXT_NAMES:
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding='utf-8', errors='replace') as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            files_scanned += 1
            rel = os.path.relpath(path, root)
            for no, line in enumerate(lines, 1):
                if len(line) > 2000:
                    continue
                for rid, layer, rx, why, tg in COMPILED:
                    if not applies(tg, target):
                        continue
                    if rx.search(line):
                        entry = hits.setdefault(rid, {"rule": rid, "layer": layer, "why": why, "count": 0, "where": []})
                        entry["count"] += 1
                        if len(entry["where"]) < max_per_rule:
                            entry["where"].append({"file": rel, "line": no, "text": line.strip()[:160]})
    return files_scanned, list(hits.values())


def render_md(root, target, files_scanned, hits):
    out = [f"# Portability hazard scan", "", f"- Path: `{root}`", f"- Target: `{target}`",
           f"- Files scanned: {files_scanned}", f"- Rules hit: {len(hits)} "
           f"({sum(h['count'] for h in hits)} lines)", "",
           "> A hit means *look here*. Silence does not mean *portable*.", ""]
    if not hits:
        out.append("No pattern hits. Still walk the hazard map by hand for this target.")
        return "\n".join(out) + "\n"
    by_layer = OrderedDict((l, []) for l in LAYER_ORDER)
    for h in hits:
        by_layer.setdefault(h["layer"], []).append(h)
    out += ["| Layer | Rule | Hits | Why it matters |", "| --- | --- | ---: | --- |"]
    for layer, hs in by_layer.items():
        for h in sorted(hs, key=lambda x: -x["count"]):
            out.append(f"| {layer} | `{h['rule']}` | {h['count']} | {h['why']} |")
    out.append("")
    for layer, hs in by_layer.items():
        if not hs:
            continue
        out.append(f"## {layer}")
        for h in sorted(hs, key=lambda x: -x["count"]):
            out.append(f"### `{h['rule']}` ({h['count']})")
            for w in h["where"]:
                out.append(f"- `{w['file']}:{w['line']}` — `{w['text'].replace('`', "'")}`")
            if h["count"] > len(h["where"]):
                out.append(f"- … {h['count'] - len(h['where'])} more")
            out.append("")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path")
    ap.add_argument("--target", default="any",
                    choices=["any", "linux", "macos", "windows", "ios", "android", "wasm", "arm64"])
    ap.add_argument("--json", action="store_true", help="emit JSON instead of Markdown")
    ap.add_argument("--max-per-rule", type=int, default=20)
    ap.add_argument("--exclude", nargs="*", default=[])
    a = ap.parse_args(argv)
    if not os.path.isdir(a.path):
        print(f"not a directory: {a.path}", file=sys.stderr)
        return 2
    n, hits = scan(a.path, a.target, a.exclude, a.max_per_rule)
    if a.json:
        print(json.dumps({"path": a.path, "target": a.target, "files_scanned": n, "hazards": hits}, indent=2))
    else:
        sys.stdout.write(render_md(a.path, a.target, n, hits))
    return 0


if __name__ == "__main__":
    sys.exit(main())
