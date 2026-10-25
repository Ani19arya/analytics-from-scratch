#!/usr/bin/env python3
"""Run every lesson test against its solution and print a pass/fail table.

Usage (from the repo root):  python3 tools/run_all_tests.py
Add --exercise to also confirm each shipped exercise still fails, as it should.
Exits 1 if any solution fails (or, with --exercise, if any exercise passes).
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHASES = os.path.join(ROOT, "phases")


def lesson_dirs():
    out = []
    for phase in sorted(os.listdir(PHASES)):
        pdir = os.path.join(PHASES, phase)
        if not os.path.isdir(pdir):
            continue
        for lesson in sorted(os.listdir(pdir)):
            ldir = os.path.join(pdir, lesson)
            if os.path.isfile(os.path.join(ldir, "test_lesson.py")):
                out.append(ldir)
    return out


def run(ldir, solution):
    env = dict(os.environ)
    env.pop("CHECK_SOLUTION", None)
    if solution:
        env["CHECK_SOLUTION"] = "1"
    proc = subprocess.run(
        [sys.executable, "test_lesson.py"],
        cwd=ldir, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True, timeout=300,
    )
    return proc.returncode == 0, proc.stdout


def main():
    check_exercise = "--exercise" in sys.argv[1:]
    lessons = lesson_dirs()
    if not lessons:
        print("No lessons found under phases/.")
        return 1
    rows, failed = [], []
    for ldir in lessons:
        name = os.path.relpath(ldir, PHASES)
        ok, output = run(ldir, solution=True)
        row = [name, "PASS" if ok else "FAIL"]
        if not ok:
            failed.append((name, "solution", output))
        if check_exercise:
            ex_ok, _ = run(ldir, solution=False)
            row.append("fails (ok)" if not ex_ok else "PASSES (bad)")
            if ex_ok:
                failed.append((name, "exercise", "The shipped exercise passes the test.\n"))
        rows.append(row)
    header = ["lesson", "solution"] + (["exercise"] if check_exercise else [])
    widths = [max(len(r[i]) for r in rows + [header]) for i in range(len(header))]
    line = lambda r: "  ".join(c.ljust(w) for c, w in zip(r, widths))
    print(line(header))
    print("  ".join("-" * w for w in widths))
    for r in rows:
        print(line(r))
    print()
    print("%d lessons, %d problems" % (len(rows), len(failed)))
    for name, kind, output in failed:
        print("\n=== %s (%s) ===\n%s" % (name, kind, output[-2000:]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
