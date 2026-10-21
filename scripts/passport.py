#!/usr/bin/env python3
"""passport.py - keep an honest, evidence-stamped passport for every port target.

A port target (e.g. "macos-arm64", "web-wasm", "python3.12") climbs a fixed
ladder of rungs. A rung can only be stamped with written evidence, from a named
build, after every rung below it is stamped. When a new build is recorded,
older stamps go stale until they are re-earned. The passport therefore never
claims more than was actually observed.

Commands:
  init     --project NAME --source "what runs today"   create passport.json
  target   NAME --desc "os/arch/runtime/device"        add a target
  build    TARGET BUILD_ID                             record the current build
  stamp    TARGET RUNG --evidence TEXT [--where PATH] [--device TEXT]
  revoke   TARGET RUNG --reason TEXT                   drop a rung and all above
  show     [--md]                                       print status
  claim    TARGET                                       print the strongest honest sentence
  parity   BASELINE_DIR CANDIDATE_DIR [--eol] [--strip] compare golden outputs
  rungs                                                 list the ladder

Use --file PATH to point at a passport other than ./passport.json.
Standard library only, Python 3.8+.
"""
import argparse, datetime, difflib, hashlib, json, os, sys

RUNGS = [
    ("builds", "The toolchain produces an artifact for this target.",
     "it launches or works"),
    ("launches", "The artifact starts on the target and reaches its own entry point.",
     "it shows anything meaningful"),
    ("first-light", "The first meaningful output appears on the target (a frame, a page, a response, real CLI output).",
     "it reacts to input"),
    ("interacts", "A real input causes the expected, visible change of state.",
     "state survives a restart"),
    ("round-trip", "State is saved, the process is fully restarted, and the state comes back intact.",
     "it behaves like the original"),
    ("parity", "Golden scenarios recorded on the source platform match on the target within the agreed tolerance.",
     "it holds up over time or under load"),
    ("endures", "A soak run, performance budget and lifecycle events (suspend, resume, kill, low memory) pass on the target.",
     "it installs cleanly for someone else"),
    ("ships", "A packaged, signed artifact installs and passes the smoke path on a clean target that never saw a dev build.",
     "any other target works"),
]
RUNG_NAMES = [r[0] for r in RUNGS]


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path):
    if not os.path.exists(path):
        sys.exit(f"no passport at {path}; run `init` first")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def get_target(data, name):
    t = data["targets"].get(name)
    if t is None:
        sys.exit(f"unknown target '{name}'; known: {', '.join(data['targets']) or '(none)'}")
    return t


def fresh_level(t):
    """Index+1 of the highest rung that is stamped on the current build with no gaps; 0 if none."""
    level = 0
    for i, rung in enumerate(RUNG_NAMES):
        s = t["stamps"].get(rung)
        if not s or s["build"] != t.get("build"):
            break
        level = i + 1
    return level


def cmd_init(a):
    if os.path.exists(a.file) and not a.force:
        sys.exit(f"{a.file} exists; use --force to overwrite")
    save(a.file, {"project": a.project, "source": a.source, "created": now(), "targets": {}, "log": []})
    print(f"created {a.file}")


def cmd_target(a):
    d = load(a.file)
    if a.name in d["targets"]:
        sys.exit(f"target '{a.name}' already exists")
    d["targets"][a.name] = {"desc": a.desc, "build": None, "stamps": {}}
    d["log"].append({"at": now(), "event": "target", "target": a.name, "desc": a.desc})
    save(a.file, d)
    print(f"added target {a.name}")


def cmd_build(a):
    d = load(a.file)
    t = get_target(d, a.target)
    before = fresh_level(t)
    t["build"] = a.build_id
    d["log"].append({"at": now(), "event": "build", "target": a.target, "build": a.build_id})
    save(a.file, d)
    stale = [r for r, s in t["stamps"].items() if s["build"] != a.build_id]
    print(f"{a.target}: current build is now {a.build_id}")
    if stale:
        print(f"  {len(stale)} stamp(s) are now stale and must be re-earned: {', '.join(stale)}")
    if before:
        print(f"  fresh level dropped from {RUNG_NAMES[before-1]} to "
              f"{RUNG_NAMES[fresh_level(t)-1] if fresh_level(t) else 'nothing'}")


def cmd_stamp(a):
    d = load(a.file)
    t = get_target(d, a.target)
    if a.rung not in RUNG_NAMES:
        sys.exit(f"unknown rung '{a.rung}'; ladder: {' > '.join(RUNG_NAMES)}")
    if not t.get("build"):
        sys.exit(f"record a build first: passport.py build {a.target} <BUILD_ID>")
    ev = (a.evidence or "").strip()
    if len(ev) < 12:
        sys.exit("evidence is required and must say what was observed (at least a short sentence)")
    idx = RUNG_NAMES.index(a.rung)
    missing = [r for r in RUNG_NAMES[:idx]
               if not t["stamps"].get(r) or t["stamps"][r]["build"] != t["build"]]
    if missing:
        sys.exit(f"cannot stamp '{a.rung}' on build {t['build']}: lower rung(s) not earned on this build: "
                 f"{', '.join(missing)}")
    t["stamps"][a.rung] = {"build": t["build"], "evidence": ev, "where": a.where, "device": a.device, "at": now()}
    d["log"].append({"at": now(), "event": "stamp", "target": a.target, "rung": a.rung, "build": t["build"]})
    save(a.file, d)
    print(f"{a.target}: stamped {a.rung} on build {t['build']}")


def cmd_revoke(a):
    d = load(a.file)
    t = get_target(d, a.target)
    if a.rung not in RUNG_NAMES:
        sys.exit(f"unknown rung '{a.rung}'")
    idx = RUNG_NAMES.index(a.rung)
    dropped = [r for r in RUNG_NAMES[idx:] if r in t["stamps"]]
    for r in dropped:
        del t["stamps"][r]
    d["log"].append({"at": now(), "event": "revoke", "target": a.target, "rung": a.rung,
                     "dropped": dropped, "reason": a.reason})
    save(a.file, d)
    print(f"{a.target}: revoked {', '.join(dropped) or '(nothing stamped)'} — {a.reason}")


def claim_sentence(name, t):
    lvl = fresh_level(t)
    if not t.get("build"):
        return f"{name}: no build recorded yet — nothing can be claimed."
    if lvl == 0:
        return f"{name} (build {t['build']}): nothing earned on this build yet."
    rung, meaning, not_implied = RUNGS[lvl - 1]
    s = t["stamps"][rung]
    where = f" Evidence: {s['where']}." if s.get("where") else ""
    dev = f" on {s['device']}" if s.get("device") else ""
    return (f"{name} (build {t['build']}) has reached '{rung}'{dev}: {s['evidence']}.{where} "
            f"This does not yet show that {not_implied}.")


def cmd_claim(a):
    d = load(a.file)
    print(claim_sentence(a.target, get_target(d, a.target)))


def cmd_show(a):
    d = load(a.file)
    if a.md:
        out = [f"# Port passport — {d['project']}", "", f"Source today: {d['source']}", ""]
        header = "| Target | Build | " + " | ".join(RUNG_NAMES) + " |"
        out += [header, "|" + " --- |" * (len(RUNG_NAMES) + 2)]
        for name, t in d["targets"].items():
            cells = []
            for r in RUNG_NAMES:
                s = t["stamps"].get(r)
                cells.append("—" if not s else ("✅" if s["build"] == t.get("build") else "⚠️ stale"))
            out.append(f"| {name} | {t.get('build') or '—'} | " + " | ".join(cells) + " |")
        out += ["", "## Honest claims", ""]
        for name, t in d["targets"].items():
            out.append(f"- {claim_sentence(name, t)}")
        print("\n".join(out))
        return
    print(f"{d['project']} — source: {d['source']}")
    for name, t in d["targets"].items():
        lvl = fresh_level(t)
        print(f"\n[{name}] {t['desc']}  build={t.get('build')}  level={RUNG_NAMES[lvl-1] if lvl else 'none'}")
        for r in RUNG_NAMES:
            s = t["stamps"].get(r)
            mark = "  " if not s else ("OK" if s["build"] == t.get("build") else "ST")
            print(f"  [{mark}] {r}" + (f"  ({s['build']}) {s['evidence']}" if s else ""))


def _read(path, eol, strip):
    with open(path, "rb") as fh:
        raw = fh.read()
    if not (eol or strip):
        return raw
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    if eol:
        text = text.replace("\r\n", "\n").replace("\r", "\n")
    if strip:
        text = "\n".join(l.rstrip() for l in text.split("\n")).rstrip("\n") + "\n"
    return text.encode("utf-8")


def _files(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            out[os.path.relpath(p, root).replace(os.sep, "/")] = p
    return out


def cmd_parity(a):
    base, cand = _files(a.baseline), _files(a.candidate)
    same, diff, missing, extra = [], [], [], sorted(set(cand) - set(base))
    for rel, bp in base.items():
        if rel not in cand:
            missing.append(rel)
            continue
        b, c = _read(bp, a.eol, a.strip), _read(cand[rel], a.eol, a.strip)
        (same if hashlib.sha256(b).digest() == hashlib.sha256(c).digest() else diff).append((rel, b, c))
    print(f"parity: {len(same)} match, {len(diff)} differ, {len(missing)} missing, {len(extra)} unexpected")
    for rel, b, c in diff:
        print(f"\n--- DIFF {rel}")
        try:
            bl, cl = b.decode("utf-8").splitlines(), c.decode("utf-8").splitlines()
            for line in list(difflib.unified_diff(bl, cl, "baseline", "candidate", lineterm="", n=1))[:40]:
                print(line)
        except UnicodeDecodeError:
            print(f"  binary: {len(b)} vs {len(c)} bytes")
    for rel in missing:
        print(f"MISSING {rel}")
    for rel in extra:
        print(f"UNEXPECTED {rel}")
    return 0 if not (diff or missing) else 1


def cmd_rungs(a):
    for i, (r, meaning, ni) in enumerate(RUNGS, 1):
        print(f"{i}. {r:<12} {meaning}\n   does NOT prove: {ni}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--file", default="passport.json")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("init"); p.add_argument("--project", required=True); p.add_argument("--source", required=True)
    p.add_argument("--force", action="store_true"); p.set_defaults(fn=cmd_init)
    p = sp.add_parser("target"); p.add_argument("name"); p.add_argument("--desc", default=""); p.set_defaults(fn=cmd_target)
    p = sp.add_parser("build"); p.add_argument("target"); p.add_argument("build_id"); p.set_defaults(fn=cmd_build)
    p = sp.add_parser("stamp"); p.add_argument("target"); p.add_argument("rung"); p.add_argument("--evidence", required=True)
    p.add_argument("--where"); p.add_argument("--device"); p.set_defaults(fn=cmd_stamp)
    p = sp.add_parser("revoke"); p.add_argument("target"); p.add_argument("rung"); p.add_argument("--reason", required=True)
    p.set_defaults(fn=cmd_revoke)
    p = sp.add_parser("show"); p.add_argument("--md", action="store_true"); p.set_defaults(fn=cmd_show)
    p = sp.add_parser("claim"); p.add_argument("target"); p.set_defaults(fn=cmd_claim)
    p = sp.add_parser("parity"); p.add_argument("baseline"); p.add_argument("candidate")
    p.add_argument("--eol", action="store_true", help="treat CRLF/CR/LF as equal")
    p.add_argument("--strip", action="store_true", help="ignore trailing whitespace")
    p.set_defaults(fn=cmd_parity)
    p = sp.add_parser("rungs"); p.set_defaults(fn=cmd_rungs)
    a = ap.parse_args(argv)
    rc = a.fn(a)
    return rc or 0


if __name__ == "__main__":
    sys.exit(main())
