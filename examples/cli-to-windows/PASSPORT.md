# Port passport — csvtidy

Source today: Python 3.11 CLI on Ubuntu 24.04 x86_64

| Target | Build | builds | launches | first-light | interacts | round-trip | parity | endures | ships |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| windows-x64 | a1f3-r3 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| macos-arm64 | a1f3-r3 | ✅ | — | — | — | — | — | — | — |

## Honest claims

- windows-x64 (build a1f3-r3) has reached 'parity' on Win11 VM: passport.py parity golden out/windows-x64 --eol: 3 match, 0 differ. Evidence: port/evidence/r3/parity.txt. This does not yet show that it holds up over time or under load.
- macos-arm64 (build a1f3-r3) has reached 'builds': pip install . succeeded on M2, pure-Python wheel. This does not yet show that it launches or works.
