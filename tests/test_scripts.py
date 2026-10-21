#!/usr/bin/env python3
"""Self-tests for portscan.py and passport.py. Run: python3 tests/test_scripts.py"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "scripts")


def run(script, *args, cwd=None):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def test_portscan():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "app.py"), "w") as f:
            f.write('import os, subprocess\nCFG = "/etc/myapp/config.ini"\nsubprocess.run(["grep", "x"])\n'
                    'data = open("notes.txt", "r")\nif os.name == "nt": pass\n')
        with open(os.path.join(d, "fast.c"), "w") as f:
            f.write('#include <immintrin.h>\n#include <unistd.h>\nint main(){ long x = sizeof(long); fork(); }\n')
        os.makedirs(os.path.join(d, "node_modules"))
        with open(os.path.join(d, "node_modules", "skip.js"), "w") as f:
            f.write('require("child_process")\n')
        rc, out = run("portscan.py", d, "--json")
        assert rc == 0, out
        rules = {h["rule"] for h in json.loads(out)["hazards"]}
        for expected in ["abs-unix-path", "shell-out", "unix-tool", "no-encoding-open", "platform-branch",
                         "x86-intrinsic", "posix-api", "word-size", "fork"]:
            assert expected in rules, (expected, rules)
        files = {w["file"] for h in json.loads(out)["hazards"] for w in h["where"]}
        assert not any("node_modules" in f for f in files), files
        rc, out = run("portscan.py", d, "--target", "linux", "--json")
        rules_linux = {h["rule"] for h in json.loads(out)["hazards"]}
        assert "fork" not in rules_linux and "abs-unix-path" not in rules_linux, rules_linux
        rc, md = run("portscan.py", d)
        assert "## cpu-abi" in md and "fast.c:1" in md, md
    print("portscan ok")


def test_passport():
    with tempfile.TemporaryDirectory() as d:
        P = lambda *a: run("passport.py", *a, cwd=d)
        assert P("init", "--project", "demo", "--source", "linux x86_64 CLI")[0] == 0
        assert P("target", "macos-arm64", "--desc", "macOS 15 on M-series")[0] == 0
        rc, out = P("stamp", "macos-arm64", "builds", "--evidence", "cargo build exited 0")
        assert rc != 0 and "build first" in out, out
        P("build", "macos-arm64", "b1")
        rc, out = P("stamp", "macos-arm64", "launches", "--evidence", "process started and printed banner")
        assert rc != 0 and "builds" in out, out              # gap refused
        rc, out = P("stamp", "macos-arm64", "builds", "--evidence", "ok")
        assert rc != 0 and "evidence" in out, out            # thin evidence refused
        assert P("stamp", "macos-arm64", "builds", "--evidence", "cargo build --release exited 0")[0] == 0
        assert P("stamp", "macos-arm64", "launches", "--evidence", "binary printed --version on M2")[0] == 0
        rc, out = P("claim", "macos-arm64")
        assert "'launches'" in out and "does not yet show" in out, out
        rc, out = P("build", "macos-arm64", "b2")
        assert "stale" in out, out
        rc, out = P("claim", "macos-arm64")
        assert "nothing earned" in out, out
        rc, out = P("show", "--md")
        assert "stale" in out, out
        assert P("stamp", "macos-arm64", "builds", "--evidence", "rebuilt b2, exit 0")[0] == 0
        rc, out = P("revoke", "macos-arm64", "builds", "--reason", "signing broke")
        assert "builds" in out and "launches" in out, out
        base, cand = os.path.join(d, "base"), os.path.join(d, "cand")
        os.makedirs(base); os.makedirs(cand)
        open(os.path.join(base, "a.txt"), "w", newline="").write("one\ntwo\n")
        open(os.path.join(cand, "a.txt"), "w", newline="").write("one\r\ntwo\r\n")
        open(os.path.join(base, "b.txt"), "w").write("x\n")
        rc, out = P("parity", base, cand)
        assert rc == 1 and "MISSING b.txt" in out and "1 differ" in out, out
        open(os.path.join(cand, "b.txt"), "w").write("x\n")
        rc, out = P("parity", base, cand, "--eol")
        assert rc == 0 and "2 match" in out, out
    print("passport ok")


if __name__ == "__main__":
    test_portscan(); test_passport(); print("all tests passed")
