# Portability hazard scan

- Path: `before`
- Target: `windows`
- Files scanned: 1
- Rules hit: 6 (7 lines)

> A hit means *look here*. Silence does not mean *portable*.

| Layer | Rule | Hits | Why it matters |
| --- | --- | ---: | --- |
| os-api | `env-var` | 1 | Environment variable whose name or presence is OS-specific. |
| os-api | `platform-branch` | 1 | Existing platform branch: inventory every arm and decide what the new target takes. |
| filesystem | `abs-unix-path` | 1 | Hard-coded Unix absolute path; missing or sandboxed on other systems. |
| text | `no-encoding-open` | 2 | Text file opened without an explicit encoding; default differs per OS locale. |
| text | `crlf-assume` | 1 | Line-ending assumption; CRLF vs LF differs by OS and git settings. |
| process | `shell-out` | 1 | Spawns an external program; the program, its flags or a shell may not exist on the target (and not at all on iOS/wasm). |

## os-api
### `env-var` (1)
- `csvtidy.py:5` — `CONFIG = os.path.join(os.environ["HOME"], ".csvtidy")`

### `platform-branch` (1)
- `csvtidy.py:24` — `if sys.platform == "linux":`

## filesystem
### `abs-unix-path` (1)
- `csvtidy.py:4` — `CACHE = "/tmp/csvtidy-cache"`

## text
### `no-encoding-open` (2)
- `csvtidy.py:14` — `data = open(path, "r").read()`
- `csvtidy.py:19` — `with open(path, "w") as fh:`

### `crlf-assume` (1)
- `csvtidy.py:15` — `return data.split("\n")`

## process
### `shell-out` (1)
- `csvtidy.py:10` — `return subprocess.run(["sort", "-u", path], capture_output=True, text=True).stdout`

