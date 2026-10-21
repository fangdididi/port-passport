# Port log templates

Copy these into `port/identity.md` and `port/log.md` in the project being ported.

## Identity sheet (`port/identity.md`)

```markdown
# Identity — <project>
## Source (what runs today)
- Version / commit:
- Build command:
- Runtime / toolchain versions:
- OS + CPU:
- Dependency lock (file + hash):
- Native modules and their architectures:
- Data / asset versions:

## Targets
| Target id | OS + version | CPU | Device class | Runtime/toolchain | Signing / sandbox | Channel |
| --- | --- | --- | --- | --- | --- | --- |

## Job type
implement / diagnose / assess-only   (assess-only = read-only)

## Golden scenarios
| id | Steps | Captured outputs (port/golden/<id>/) | Non-determinism + normalisation |
| --- | --- | --- | --- |
```

## Round entry (`port/log.md`)

```markdown
## Round <n> — <target> — <date>
- Build: <build id>  (source commit + dirty summary, artifact hash)
- Device / OS: 
- Data dir / cache key / diagnostics config:
- Failing layer: identity | build | load/link | platform layer | service/API | render/IO | presentation | behaviour
- Hypothesis (falsifiable): 
- Evidence collected (bounded): 
- Result: confirmed / refuted
- Counter-examples ruled out:
- Change made (semantic, not a mask):
- Re-verified in a fresh process with diagnostics off: yes / no
- Passport: stamped <rung> / revoked <rung> / unchanged
- Not verified / known failures:
- Next blocker + the one check that will show it fixed:
```

## Handover (end of session)

```markdown
## Handover — <date>
- Changed:
- Status per target (paste `passport.py claim <target>`):
- Evidence trail:
- Not verified / known failures:
- Next blocker and check:
```
