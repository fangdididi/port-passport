# csvtidy → Windows / macOS — port log

## Identity (abridged)
- Source: csvtidy 0.4.0 @ a1f3, Python 3.11.9, Ubuntu 24.04 x86_64, pure Python, no native modules.
- Targets: `windows-x64` (Windows 11 23H2 VM, Python 3.11.9), `macos-arm64` (M2, macOS 15, Python 3.11.9).
- Job type: implement.
- Golden scenarios (captured on Ubuntu before any edit): `orders` (clean 1,204-row CSV), `dedupe`
  (sort + unique), `config` (set → new shell → get). Non-determinism: none; outputs are byte-compared.

## Hazards (from `scan.md` + hazard map)
| Layer | Hazard | Where | Fix | Cost | Blocks |
| --- | --- | --- | --- | --- | --- |
| process | shells out to GNU `sort` | `csvtidy.py:10` | `sorted(set(lines))` in Python | S | first-light |
| filesystem | `/tmp/` cache path | `csvtidy.py:4` | `tempfile.gettempdir()` | S | launches |
| os-api | `HOME` env var | `csvtidy.py:5` | `pathlib.Path.home()` | S | launches |
| text | open without encoding; `split("\n")` | `csvtidy.py:14-15, 19` | `encoding="utf-8", newline=""`; `splitlines()` | S | parity |
| os-api | `sys.platform == "linux"` branch skips cache dir elsewhere | `csvtidy.py:24` | create cache on every platform | S | interacts |

Route: recompile-free; replace each platform assumption with the standard library.

## Round 1 — windows-x64 — build a1f3-r1
- Failing layer: platform layer. `KeyError: 'HOME'` on start.
- Hypothesis: config path reads `HOME`, which Windows does not set. Refutable by printing `os.environ.get("HOME")`.
- Result: confirmed (None). Fix: `Path.home()`. Passport: builds, launches.

## Round 2 — windows-x64 — build a1f3-r2
- Failing layer: service/API. `dedupe` raises `FileNotFoundError: sort`.
- Hypothesis: GNU `sort` is not on PATH (Windows `sort.exe` has different flags). Confirmed by `where sort`.
- Counter-example ruled out: not a quoting problem — same error with a path without spaces.
- Fix: in-process sort. Passport: first-light, interacts.

## Round 3 — windows-x64 — build a1f3-r3
- Failing layer: behaviour. `passport.py parity` → `orders.csv` differs on every line.
- Hypothesis: text mode writes CRLF on Windows. Confirmed: diff disappears with `--eol`, hex dump shows `0d 0a`.
- Fix (semantic): write with `newline="\n"` so output bytes match the original tool; re-ran parity *without*
  `--eol`: 3 match, 0 differ. All lower rungs re-stamped on r3. Passport: round-trip, parity.
- Not verified: endures (no large-file soak yet), ships (no signed installer yet).
- Next blocker: macos-arm64 launches — run `csvtidy --version` on the M2 with build r3.
