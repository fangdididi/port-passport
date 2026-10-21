# Hazard map

Walk this map layer by layer for each target. For every hazard that applies, write one row:
*layer · hazard · where · likely fix · cost (S/M/L) · blocks which rung*. `scripts/portscan.py` finds
many of these mechanically; the rest need reading.

## 1. Build & toolchain
- Target compiler/SDK/toolchain installed and pinned? Cross-compile or native build?
- Compiler-specific extensions (`__declspec`, `__attribute__`, MSVC pragmas), warnings promoted to errors.
- Native extensions / prebuilt binaries in dependencies: is there a build for this OS **and** architecture?
- Build scripts that call shell tools (`sed`, `cp`, PowerShell) or assume a case-insensitive filesystem.
- Generated code or caches checked in for one platform.
- Reproducibility: can two clean machines produce the same artifact hash?

## 2. CPU & ABI
- Intrinsics and inline assembly (SSE/AVX vs NEON vs none in wasm); dispatch on CPU features.
- Data model: LP64 (Linux/macOS), LLP64 (Windows), wasm32 — `long`, pointers, `size_t`, pointer↔int casts.
- Endianness in file formats, network code, hashing, `reinterpret_cast` of buffers.
- Alignment and packed structs; unaligned loads that trap on some targets.
- Plain `char` signedness (signed on x86, unsigned on most ARM Linux).
- Reserved registers and calling conventions when patching or calling generated code.
- Executable memory / JIT: forbidden or entitlement-gated on iOS, restricted in browsers.
- Floating point: denormals, fused multiply-add, `long double` size — results can differ in the last bits.

## 3. OS API
- Windows-only (registry, `CreateFile`, COM) vs POSIX-only (`fork`, `mmap`, `dlopen`, `ioctl`, `/proc`).
- Every `#ifdef`/`sys.platform`/`process.platform` branch: does the new target fall into a sensible arm,
  or into a default that assumes something else?
- Environment variables (`HOME` vs `USERPROFILE`, `XDG_*`, `TMPDIR`).
- Permissions model: sandbox, user prompts, entitlements, background execution limits.

## 4. Filesystem
- Absolute paths, drive letters, `~`, separators, path length limits, reserved names (`CON`, `NUL`).
- Case sensitivity (Linux yes, macOS/Windows usually no) — imports and asset names that differ only in case.
- Where data may live: app containers, per-user dirs, read-only bundles, browser storage quotas.
- File locking, atomic rename semantics, symlinks, permissions bits, timestamps resolution.

## 5. Text & locale
- Default encoding when opening files or consoles; BOMs; UTF-16 APIs on Windows.
- Line endings (CRLF vs LF), including what git converts on checkout.
- Locale-dependent formatting and case mapping (decimal comma, Turkish dotless i), collation and sort order.

## 6. Process
- Spawning programs: does the program exist, are its flags the same, is there a shell at all (not on iOS/wasm)?
- Signals and termination (`SIGTERM` vs console control events), exit codes, zombie reaping.
- `fork`/`exec`, daemons, services, launch agents — different on every OS.

## 7. Time & threads
- Wall clock vs monotonic clock; timer resolution; sleep granularity.
- Busy loops and sleep-polling; main/UI thread rules (browsers and mobile must not block it).
- Thread priorities, affinity, core counts (big.LITTLE), memory model (ARM is weaker than x86).
- Races that only appear with a different scheduler: lost wake-ups, missing barriers, init ordering.

## 8. Media & input
- Graphics: OpenGL (deprecated on Apple), Direct3D (Windows), Metal (Apple), Vulkan (not native on Apple),
  WebGL/WebGPU (browser). Shader languages and precompiled shader formats per platform.
- Present/submit/vsync paths; read-backs; colour space and pixel format; HiDPI scaling.
- Audio backends and formats, sample rates, interruptions (calls, backgrounding), latency.
- Input: keyboard layouts, mouse vs touch, controllers and hot-plug, IME/text input, focus loss with keys held.

## 9. Network & storage
- Local IPC (Unix sockets, named pipes) — absent in browsers.
- Synchronous I/O on UI threads; browser CORS and mixed content; mobile background networking.
- Databases and file formats written by one platform and read by another (byte order, path fields).

## 10. Packaging & distribution
- Code signing, notarisation, provisioning, entitlements; installer formats (MSI/MSIX, pkg/dmg, APK/AAB, IPA).
- Store policies (no downloaded executable code, required permissions copy).
- Bundle content: are you allowed to redistribute every asset and library inside it?
- Update path: can the new build read data written by the old one?

## Routes, cheapest first
1. **Recompile with small shims** — portable code, a handful of platform calls.
2. **Replace a platform layer behind an interface** — files, clock, windowing, audio, input.
3. **Adopt an existing compatibility library** — only if licensed, maintained and covering your calls.
4. **Translate / transpile** — e.g. shader conversion, API translation layers; verify semantics separately.
5. **Rewrite one module** — last resort, scoped to the module, verified against golden scenarios.
