---
name: port-passport
description: >-
  An evidence-first porting skill for moving working software onto a new target — another OS
  (Linux/macOS/Windows), CPU architecture (x86_64 to ARM64/Apple Silicon), mobile (iOS/iPadOS/Android),
  the browser (WebAssembly/HTML5), a new runtime or language version (Python 3.x, Node, JDK), or a new
  major framework version. It pins down exactly what runs today, records golden behaviour on the source
  platform before touching anything, maps hazards layer by layer (build, CPU/ABI, OS API, filesystem,
  text, process, time & threads, media & input, network & storage, packaging), drives one thin
  end-to-end slice to "first light", fixes one blocker per round with a falsifiable hypothesis, and lets
  each target earn rungs on an eight-step evidence ladder (builds > launches > first-light > interacts >
  round-trip > parity > endures > ships) — never claiming a rung it did not observe on the current build.
  Use it when someone asks to port, migrate, re-platform, cross-compile, "make it run on Mac/ARM/Windows/
  iPad/the web", upgrade a runtime across a breaking version, judge how far along a port really is, or
  debug a port that builds but shows a black screen, hangs, or behaves differently from the original.
---

# port-passport

A port fails in a recognisable way. It builds on the new machine, someone sees a window, and the word
"done" escapes into a status update. A week later it turns out input never worked on the tablet, saves
silently went to a temp folder, the Mac result was quoted for the phone, and the "passing" log came
from the previous build. Nobody lied; they just let a lower kind of evidence stand in for a higher one.

port-passport is a working method that makes that slide impossible. Each target the software is being
moved to gets a **passport**: a short record of which rungs of an evidence ladder it has earned, on
which build, on which device, with what proof. A rung is stamped only from something actually observed;
a new build makes old stamps stale until they are earned again; a Mac stamp says nothing about an iPad.
Around the passport sits a disciplined loop: pin the inputs, record how the original behaves, map the
hazards, get one thin path working end to end, and then remove one real blocker at a time.

It works for any kind of port, small or brutal:

- a Python or Node CLI going from Linux to Windows and macOS;
- a C/C++ or Rust desktop app moving from x86_64 to ARM64 / Apple Silicon;
- a desktop game or tool going to the browser through WebAssembly;
- an app moving onto iOS, iPadOS or Android;
- a service jumping a breaking runtime or framework version (Python 3.8 → 3.12, JDK 11 → 21, a major
  web framework release) where "the platform" is the runtime.

## What problem it solves

1. **Fake progress.** "It compiles" quietly becomes "it works". The ladder names exactly what each kind
   of evidence proves and — just as important — what it does *not* prove.
2. **Nothing to compare against.** Teams change the code first and only later ask "is this what it did
   before?" The skill records golden behaviour on the source platform *before* the first edit.
3. **Wandering debugging.** Ports fail deep in a stack. Every failure is first located to a layer, then
   attacked with one hypothesis that a single observation can falsify.
4. **Platform blur.** Results from one OS, chip, device, or build get merged into a claim no single run
   supports. Each target has its own passport; each stamp names its build and device.
5. **Silent fakes.** Unimplemented calls that "return success", skipped draws, hard-coded values to make a
   symptom vanish. The skill treats these as defects, not progress.

## When to use it

- "Port / migrate / re-platform this to X." "Make it run on Apple Silicon / Windows / the web / iPad."
- "We upgraded to <runtime> N+1 and things break." "Plan the move from <framework> A to B."
- "How far along is the port, really?" — use the passport alone as an audit (read-only).
- "It builds but shows a black screen / hangs / crashes on start / behaves differently on the new target."
- Before you promise a date for a port: run Steps 1–3 to expose the real size of the job.

Not for: writing a brand-new app for a new platform from scratch (nothing to port), or installing and
configuring an existing emulator or compatibility layer for personal use.

## Ground rules

- **Evidence before claims.** No rung is stamped, and no status sentence is written, without an
  observation from the *current* build on the *named* target.
- **The source stays untouched.** Treat original sources, binaries, assets and user data as read-only.
  Work in separate build, cache and data directories, keyed by target and build.
- **Preserve behaviour, don't reinvent it.** A port keeps the original logic. Replacing a feature with a
  demo, stubbing it to "succeed", or tuning values until a symptom disappears is not porting.
- **Fail loudly on the unknown.** An unimplemented API, syscall, opcode or format must stop with a clear
  message that says what and where, unless you have shown the caller tolerates a meaningful fallback.
- **Respect rights.** Only port, package and distribute what the user is entitled to. Keys, firmware,
  licensed assets and credentials never go into logs, commands, commits or the skill's outputs.
- **Ask before you run.** Building is usually fine; running the program on a user's device, signing,
  installing or publishing follows the user's explicit scope. If testing was not allowed, record the rung
  as *not verified* — never as passed.

## The evidence ladder

| # | Rung | Earned when you have observed… | Does **not** prove |
|---|------|--------------------------------|--------------------|
| 1 | **builds** | the target toolchain producing an artifact (exit 0, artifact identity/hash, signature if required) | that it starts |
| 2 | **launches** | the artifact starting on the target and reaching its own entry point (log line, trace, banner) | that it shows anything meaningful |
| 3 | **first-light** | the first meaningful output on the target — a correct frame, page, response or CLI result | that it reacts to input |
| 4 | **interacts** | a real input causing the expected visible state change (before/after) | that state survives a restart |
| 5 | **round-trip** | state saved, the process fully exited, a *new* process restoring that state | that it behaves like the original |
| 6 | **parity** | the golden scenarios from Step 2 matching on the target within the agreed tolerance | that it holds up over time or load |
| 7 | **endures** | a soak run, a performance budget, and lifecycle events (background/foreground, suspend/resume, kill, low memory, disconnect) passing | that a stranger can install it |
| 8 | **ships** | a packaged, signed build installing and passing the smoke path on a clean target that never saw a dev build | anything about another target |

Rungs are climbed in order, per target, per build. A new build makes every older stamp *stale*.
Success on "macOS arm64" says nothing about "iPadOS"; a simulator is not a device; a CI runner is not a
user's machine. `scripts/passport.py` enforces all of this mechanically (see Tools).

## Step-by-step

### Step 1 — Pin the inputs (the identity sheet)

Before planning anything, write down exactly what you are porting *from* and *to*. Read the repo's
README, build files, CI config, lockfiles, any AGENTS.md or contributor notes, and git status.

- **Source identity:** commit or version, build command, runtime/toolchain versions, OS and CPU it runs
  on today, dependency lock, data/asset versions, any native modules and their own architectures.
- **Target identity:** OS + version, CPU architecture, device class (desktop, phone, tablet, browser,
  container), runtime/toolchain version, signing/sandbox rules, distribution channel.
- **Ask:** is the job to *implement*, to *diagnose*, or only to *assess*? Assessment stays read-only.

Confirm identity from the real artifacts, not from names. A file called `app-arm64` can still be x86;
a "Python 3" project can pin 3.7 behaviour; a dependency can ship only one architecture's binary. Check
with tools such as `file`, `lipo -info`, `otool -L` / `ldd`, `objdump -f`, package metadata, or the
runtime's own version flag.

### Step 2 — Record golden behaviour on the source

Pick **3–7 golden scenarios** that represent what users actually do: e.g. "open sample project, export
PDF", "start, reach main menu, start level 1, move, save, quit, reload". For each, capture the
inputs and the observable outputs on the *source* platform: output files, CLI stdout, screenshots at a
fixed resolution, response bodies, timings if performance matters. Store them under
`port/golden/<scenario>/`. These become the parity rung later; without them "behaves the same" is an
opinion. Note anything non-deterministic (timestamps, random seeds, thread ordering) and how you will
normalise or fix it.

### Step 3 — Map the hazards

Run `python3 scripts/portscan.py <repo> --target <os|arch|wasm>` for a fast first pass, then walk
[`references/hazard-map.md`](references/hazard-map.md) layer by layer for the target. Produce a short
table: *layer · hazard · where · likely fix · cost (S/M/L) · blocks which rung*. Typical findings:

- **build:** toolchain or SDK missing, compiler extensions, native extensions with one architecture;
- **cpu-abi:** x86 intrinsics/asm, pointer-size or `long` assumptions, endianness in binary formats,
  signed `char`, unaligned access, reserved registers, JIT/executable memory;
- **os-api:** Win32 or POSIX-only calls, `/proc`, registry, platform `#ifdef` arms with no case for the
  new target;
- **filesystem & text:** hard-coded paths, separators, case sensitivity, sandboxed locations, encodings,
  line endings, locale;
- **process / time & threads:** shell-outs to tools that don't exist, signals, `fork`, wall-clock timing,
  sleep-polling, affinity, lost-wakeup races that a faster or slower scheduler exposes;
- **media & input:** graphics API (OpenGL on Apple, D3D off Windows), audio backends, input devices,
  touch vs mouse, controller hot-plug;
- **network & storage:** local IPC, sync file I/O in browsers, permissions, background limits;
- **packaging:** signing, entitlements, notarisation, store rules, installer formats.

Then choose a **route** and say why: *recompile with shims*, *replace a platform layer behind an
interface*, *use an existing compatibility library*, *translate/transpile*, or *rewrite one module*. Prefer
the route that reuses the most proven code; borrow nothing that cannot be licensed.

### Step 4 — Carve a seam

Put the platform-specific parts behind a narrow interface (a "platform layer" or "port layer"): files,
clock, threads, windowing, graphics, audio, input, process, storage. Core logic should not learn the new
target's name. Per-target facts — versions, feature flags, known quirks, build IDs — live in one config
per target, not scattered constants. Keep unsafe or FFI code in small, auditable modules with explicit
sizes, alignment, ownership and lifetimes; never let a panic or exception cross a foreign boundary.

### Step 5 — Thinnest slice to first light

Choose the shortest path that crosses every layer once — for a game: launch → title → one scene → one
input → save → quit → reload; for a CLI: parse args → read one real input → write one real output; for a
service: boot → one request → one persisted change → restart → read it back. Make *only* that path real.
Do not pre-build every service or API "for completeness": unimplemented areas should fail loudly so the
slice tells you the next blocker honestly.

### Step 6 — The blocker loop

Repeat until the slice reaches the rung you are aiming for:

1. **Locate the layer.** Walk the chain in order — inputs/identity → build → load/link → platform layer →
   service/API → rendering/IO → what the user actually sees → app behaviour. The first layer whose
   output is wrong is the one you fix.
2. **State one falsifiable hypothesis.** "Frames are recorded but never submitted, because the present
   call is a stub." One observation must be able to kill it.
3. **Collect the smallest evidence.** A targeted log line with a bounded size, a trace around one call,
   one GPU read-back, one minimal repro. Diagnostics default off and never print secrets.
4. **Fix the semantics, not the symptom.** Repair the real behaviour (ordering, sizes, ownership, timing).
   If you catch yourself hard-coding a height, colour, delay or "return OK", stop: that is a mask.
5. **Re-verify in a fresh process** with diagnostics off — tracing and single-stepping change timing.
6. **Log the round** in `port/log.md` using [`references/port-log-template.md`](references/port-log-template.md),
   including the counter-examples you ruled out.

Rebuild only what changed, and key every cache by input identity, tool version, target and options so a
stale artefact can never masquerade as a new result.

### Step 7 — Stamp the passport

For each target, after each meaningful round:

```bash
python3 scripts/passport.py build macos-arm64 "$(git rev-parse --short HEAD)-r3"
python3 scripts/passport.py stamp macos-arm64 first-light \
  --evidence "title screen renders at 1280x720; matches golden/title.png by eye" \
  --where port/evidence/r3/title.png --device "MacBook Air M2, macOS 15.1"
python3 scripts/passport.py parity port/golden/export port/out/macos-arm64/export --eol
python3 scripts/passport.py show --md > port/PASSPORT.md
```

`parity` compares golden outputs to target outputs file by file (with optional line-ending and
trailing-space normalisation) and exits non-zero on any difference. Regressions are recorded with
`revoke`, which drops that rung and everything above it.

### Step 8 — Hand over honestly

Finish every session with a report built from the passport, not from memory:

- **What changed** (files, modules, configs) and why.
- **Where each target stands** — the sentence from `passport.py claim <target>`, which states the rung
  reached *and* what that rung does not prove.
- **Evidence trail** — build IDs, devices, log/screenshot paths, linked to the round that produced them.
- **Not verified / known failures** — named plainly, with the build they were seen on.
- **Next blocker** and the single check that will tell whether it is fixed.

Never use completion percentages or phrases like "fully compatible" that no rung can back.

## Examples

**Example 1 — Python CLI to Windows.** A data-cleaning CLI runs on Linux. Identity sheet: Python 3.11,
Ubuntu x86_64; target Windows 11 x64, Python 3.11. Golden: three input CSVs and their outputs. portscan
flags `"/tmp/"` paths, `subprocess.run(["sort", ...])`, `open(path, "r")` without encoding and a
`split("\n")`. Route: recompile-free; replace the shell-out with the standard library, use
`tempfile` and `pathlib`, open with `encoding="utf-8", newline=""`. Passport after round 2:
builds ✅ launches ✅ first-light ✅ (help text prints) interacts ✅ (`--dry-run` lists rows) — then
`parity` fails on one file because of CRLF in output; fix by writing with `newline="\n"`; parity ✅.
Honest claim: "windows-x64 has reached parity on build a1f3-r3; endures and ships are not yet shown."

**Example 2 — desktop game to the browser.** A small C + SDL game targets WebAssembly. Hazards: a busy
`while` main loop (browsers need the loop to yield each frame), blocking file reads, desktop OpenGL
calls that WebGL lacks, threads that need cross-origin isolation headers. Slice: boot → title → level 1
→ move → save to browser storage → reload tab. Round 4 hypothesis: "black canvas because the loop never
yields" — confirmed by a frame counter stuck at 0; fix by registering the per-frame callback. Stamps:
first-light on Chromium only; the Firefox target stays at builds until it is run there.

**Example 3 — audit a port that "is 90% done".** Read-only. Build the passport from existing logs: the
only proof of "plays" is a video from three builds ago, the current build has a signature check
log, and the iPad result was never on hardware. Honest status: macOS = builds (current), iPad = nothing
on the current build. The report names the two checks that would move each target up a rung.

More worked material lives in [`examples/`](examples/).

## Tools

- `scripts/portscan.py PATH [--target linux|macos|windows|ios|android|wasm|arm64] [--json]` — fast
  hazard triage across ~35 patterns grouped by layer; skips vendored folders. A hit means "look here";
  silence never means "portable".
- `scripts/passport.py` — `init`, `target`, `build`, `stamp`, `revoke`, `show [--md]`, `claim`,
  `parity`, `rungs`. Refuses stamps without evidence, with a gap below, or before a build is recorded;
  marks older stamps stale on a new build.
- `tests/test_scripts.py` — self-tests for both tools (`python3 tests/test_scripts.py`).
- Standard library only; Python 3.8+.

## Tips

- **Same architecture is not the same platform.** ARM64 to ARM64 still changes OS ABI, memory model,
  threading, graphics, audio, input and signing.
- **"Initialised" is not "running".** Creating hundreds of GPU objects, opening an audio device or
  registering handlers proves setup — not draw, sound or input.
- **Input means a visible result.** "I sent the key" is not interaction; "the cursor moved one row" is.
  Release held keys and test focus loss.
- **Restart means a new process.** Hot reload and cached state hide save bugs.
- **Keep counter-examples.** A wrong theory you disproved saves the next person a day; log it.
- **Concurrency bugs love new schedulers.** If a port hangs intermittently, suspect ordering (e.g. a
  waiter registered after the lock is released) before adding sleeps.
- **Measure performance only after correctness**, on release builds, warm and cold caches, same scene.
- **Platforms change.** Check current official docs for signing, sandbox and store rules instead of
  trusting a memory of last year's limits.
