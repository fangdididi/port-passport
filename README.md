# port-passport

**English** · [简体中文](./README.zh-CN.md)

> Move working software to a new platform — and never claim more than you actually saw run there.

**port-passport** is an agent skill for *porting*: taking software that already works and making it work
somewhere new — another OS, another CPU architecture, a phone or tablet, the browser via WebAssembly, or
a runtime/framework version with breaking changes. Point your coding agent at a repo and a target, and it
pins down exactly what runs today, records the original's golden behaviour, maps the hazards layer by
layer, drives one thin end-to-end path to "first light", and removes one real blocker per round.

Every target gets a **passport**: an eight-rung evidence ladder —
`builds → launches → first-light → interacts → round-trip → parity → endures → ships` — where each rung
is stamped only with written evidence from the *current* build on a *named* device. A new build makes
old stamps stale. A Mac result never counts for an iPad. The agent's status report is generated from the
passport, so "it compiles" can never quietly become "it works".

## Why it's different

- **Evidence ladder, not percentages.** Each rung says what it proves *and what it does not*. Status
  sentences come out like: "macos-arm64 (build 7c09-r4) has reached first-light … This does not yet
  show that it reacts to input."
- **Golden behaviour first.** It records what the original does *before* the first edit, so "behaves the
  same" becomes a file-by-file parity check instead of an opinion.
- **Layer-located debugging.** Every failure is pinned to a layer (identity → build → load → platform layer
  → API → render/IO → presentation → behaviour) and attacked with one falsifiable hypothesis.
- **No masks.** "Return success" stubs, skipped draws and hard-coded values are treated as defects.
- **Works for any port** — CLI, desktop app, game, mobile app, service — and any stack.

## Features

- **Identity sheet** for source and every target (versions, architectures, signing, channel), verified
  from real artifacts, not file names.
- **Golden scenarios** captured on the source platform with notes on non-determinism.
- **Hazard map** across ten layers: build, CPU/ABI, OS API, filesystem, text & locale, process, time &
  threads, media & input, network & storage, packaging — plus a cheapest-first route ladder.
- **`scripts/portscan.py`** — fast, dependency-free hazard triage (~35 patterns, grouped by layer,
  filterable by target: linux, macos, windows, ios, android, wasm, arm64; Markdown or JSON output).
- **`scripts/passport.py`** — the passport itself: refuses stamps without evidence, with gaps below, or
  before a build is recorded; marks stamps stale on a new build; `revoke` for regressions; `claim` for
  an honest one-sentence status; `parity` to compare golden vs target outputs (with optional
  line-ending/whitespace normalisation, non-zero exit on difference).
- **Port log & handover templates** so every round records hypothesis, evidence, counter-examples and the
  next check.
- **Worked examples**: a Python CLI moved to Windows (real scan output + passport) and a C/SDL game moved
  to the browser (Chinese log).
- **Full English and Chinese versions** of the skill and docs.

## Installation

```bash
git clone https://github.com/fangdididi/port-passport.git
```

### Claude Code
Copy the skill into a skills directory (project-level `.claude/skills/` or user-level `~/.claude/skills/`):

```bash
mkdir -p .claude/skills/port-passport
cp -r port-passport/* .claude/skills/port-passport/
```

Claude Code discovers it from the frontmatter; ask it to "port", "migrate" or "make this run on …", or
call the skill by name.

### Codex
Put the folder where your Codex setup loads skills (for example a `skills/` directory it reads, such as
`~/.codex/skills/port-passport`), or reference `SKILL.md` from your `AGENTS.md`.

### Cursor
Drop the folder into your repo (e.g. `.cursor/skills/port-passport/`) and reference `SKILL.md`, or paste
its guidance into a rule under `.cursor/rules/`. Then ask the agent to port or audit a port.

### Any other agent
`SKILL.md` is plain Markdown with YAML frontmatter. Give it to any agent that follows instructions
(Gemini CLI, OpenCode, Copilot, Windsurf, Aider…) and run the helpers with Python 3.8+.

## Usage

Tell the agent what runs today, where it must run next, and how far you allow it to go:

```
Port this repo to macOS on Apple Silicon and to Windows x64 using port-passport.
Today it runs on Ubuntu x86_64. You may build and run locally; don't sign or publish.
```

The agent fills `port/identity.md`, records golden scenarios under `port/golden/`, scans and maps
hazards, picks a route, carves the platform seam, drives the thin slice, and logs each round in
`port/log.md` while stamping `port/passport.json`.

### The helpers

```bash
# Hazard triage for a target
python3 scripts/portscan.py path/to/repo --target windows > port/scan.md
python3 scripts/portscan.py path/to/repo --target wasm --json

# Passport
python3 scripts/passport.py init --project myapp --source "Ubuntu 24.04 x86_64, Python 3.11"
python3 scripts/passport.py target windows-x64 --desc "Windows 11, Python 3.11"
python3 scripts/passport.py build windows-x64 a1f3-r1
python3 scripts/passport.py stamp windows-x64 builds --evidence "pip install . exited 0"
python3 scripts/passport.py claim windows-x64
python3 scripts/passport.py parity port/golden port/out/windows-x64 --eol
python3 scripts/passport.py show --md > port/PASSPORT.md

# Self-test
python3 tests/test_scripts.py
```

## Example

**Before:** "The Windows port is basically done — it builds and the help text shows."

**After (generated passport):**

```
| Target      | Build   | builds | launches | first-light | interacts | round-trip | parity | endures | ships |
| windows-x64 | a1f3-r3 | ✅     | ✅       | ✅          | ✅        | ✅         | ✅     | —       | —     |
| macos-arm64 | a1f3-r3 | ✅     | —        | —           | —         | —          | —      | —       | —     |

- windows-x64 (build a1f3-r3) has reached 'parity' on Win11 VM: passport.py parity golden
  out/windows-x64 --eol: 3 match, 0 differ. This does not yet show that it holds up over time or under load.
- macos-arm64 (build a1f3-r3) has reached 'builds': pip install . succeeded on M2.
  This does not yet show that it launches or works.
```

See [`examples/cli-to-windows/`](examples/cli-to-windows/) for the full scan, log and passport, and
[`examples/game-to-web/`](examples/game-to-web/) for a browser port.

## File structure

```
port-passport/
├── SKILL.md                         # The skill (English)
├── SKILL.zh-CN.md                   # The skill (Chinese)
├── README.md                        # This file
├── README.zh-CN.md                  # README (Chinese)
├── LICENSE                          # MIT
├── references/
│   ├── hazard-map.md                # Ten-layer hazard checklist + route ladder
│   └── port-log-template.md         # Identity sheet, round entry, handover templates
├── scripts/
│   ├── portscan.py                  # Portability hazard triage
│   └── passport.py                  # Evidence-ladder passport + parity diff
├── tests/
│   └── test_scripts.py              # Self-tests for both scripts
└── examples/
    ├── cli-to-windows/              # Python CLI → Windows/macOS (scan, log, passport)
    └── game-to-web/                 # C + SDL game → WebAssembly (Chinese log)
```

## License

MIT — see [LICENSE](./LICENSE).
