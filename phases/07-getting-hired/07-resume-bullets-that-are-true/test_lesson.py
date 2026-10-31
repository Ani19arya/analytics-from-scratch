"""Tests for lesson 07: resume bullets that are true.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The committed resume is checked against findings written out by hand. Generated resumes
(another seed, built in memory) are checked against a reference tracer written separately
below, in plain Python.
"""
import csv
import importlib.util
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

sys.path.insert(0, HERE)
import make_data  # noqa: E402

# What a careful reader finds on the committed resume: (bullet, number, kind, status).
COMMITTED = [
    (1, "100", "number", "untraceable"),
    (2, "30", "number", "ok"),
    (3, "6.5", "number", "ok"), (3, "4.25", "number", "ok"), (3, "40", "percent", "inflated"),
    (4, "3.2", "percent", "points_as_percent"),
    (5, "1400", "number", "ok"), (5, "224", "number", "ok"), (5, "779", "number", "ok"), (5, "28.8", "percent", "ok"),
    (6, "4.6", "percent", "points_as_percent"), (6, "90", "number", "ok"),
    (7, "4.0", "points", "ok"), (7, "80.5", "percent", "ok"), (7, "84.5", "percent", "ok"), (7, "1771", "number", "ok"),
]


def committed():
    with open(os.path.join(HERE, "data", "resume.txt")) as f:
        resume = f.read()
    with open(os.path.join(HERE, "data", "evidence.csv"), newline="") as f:
        return resume, list(csv.DictReader(f))


def ref_findings(resume, rows):
    """Reference: a second, separate implementation of the rules in the README."""
    values = {}
    for r in rows:
        bucket = values.setdefault(r["project"], {"number": [], "percent": [], "points": []})
        b = float(r["to_value"])
        if r["from_value"] == "":
            bucket[{"number": "number", "pct": "percent", "pts": "points"}[r["unit"]]].append(b)
            continue
        a = float(r["from_value"])
        if r["unit"] == "number":
            bucket["number"].extend([a, b, abs(b - a)])
        else:
            bucket["percent"].extend([a, b])
            bucket["points"].append(abs(b - a))
        if a:
            bucket["percent"].append(abs(b - a) * 100 / a)
    out, project, n = [], None, 0
    for raw in resume.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("- "):
            project = line[line.rindex("(") + 1:-1] if line.endswith(")") and "(" in line else None
            continue
        n += 1
        bucket = values.get(project, {"number": [], "percent": [], "points": []})
        for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", line):
            before = line[m.start() - 1] if m.start() else " "
            rest = line[m.end():]
            if before.isalpha() or before in "._," or (rest[:1].isalnum()):
                continue
            text = m.group().replace(",", "")
            low = rest.lower().strip()
            if low.startswith(("percentage point", "point", "pts", "pp ")) or low in ("pp", "pts"):
                kind = "points"
            elif low.startswith(("%", "percent")):
                kind = "percent"
            else:
                kind = "number"
            places = len(text.split(".")[1]) if "." in text else 0
            hit = lambda v: abs(v - float(text)) <= 0.5 / 10 ** places + 1e-9
            if any(hit(v) for v in bucket[kind]):
                status = "ok"
            elif kind == "percent" and any(hit(v) for v in bucket["points"]):
                status = "points_as_percent"
            elif not bucket[kind]:
                status = "untraceable"
            else:
                best = sorted(bucket[kind], key=lambda v: (abs(v - float(text)), v))[0]
                status = "inflated" if float(text) > best else "understated"
            out.append((n, text, kind, status))
    return out


def as_tuples(findings):
    return [(f["bullet"], f["claim"], f["kind"], f["status"]) for f in findings]


def ev(project, metric, unit, frm, to):
    return {"project": project, "metric": metric, "unit": unit, "from_value": frm, "to_value": to, "source": "test"}


class TestClaims(unittest.TestCase):
    def test_kinds(self):
        self.assertEqual(lesson.extract_claims("Cut it by 35%, from 6.5 to 4.25 hours, for 1,400 users"),
                         [("35", "percent"), ("6.5", "number"), ("4.25", "number"), ("1400", "number")])
        self.assertEqual(lesson.extract_claims("up 4.6 points, 4.6 pts, 4.6 pp and 4.6 percentage points"),
                         [("4.6", "points"), ("4.6", "points"), ("4.6", "points"), ("4.6", "points")],
                         "'percentage points' is points, not percent: check for points first")
        self.assertEqual(lesson.extract_claims("a 12 percent lift"), [("12", "percent")])
        self.assertEqual(lesson.extract_claims("Used by 30."), [("30", "number")], "a full stop after a number is not a decimal")

    def test_no_numbers(self):
        self.assertEqual(lesson.extract_claims("Built a PowerBI dashboard in GA4 for Q3"), [],
                         "the 4 in GA4 and the 3 in Q3 are part of a name, not claims")
        self.assertEqual(lesson.extract_claims(""), [])

    def test_candidates(self):
        c = lesson.candidates([ev("p", "hours", "number", "6.5", "4.25"), ev("p", "rate", "pct", "20.0", "25.0"),
                               ev("p", "gap", "pts", "", "4.6"), ev("p", "users", "number", "", "30")])
        self.assertEqual(sorted(round(v, 4) for v, _ in c["number"]), [2.25, 4.25, 6.5, 30.0],
                         "a number comparison gives from, to and the change; a single fact gives its value")
        self.assertEqual(sorted(round(v, 4) for v, _ in c["points"]), [4.6, 5.0],
                         "a rate comparison gives a change in points; a pts fact is a points value")
        self.assertEqual(sorted(round(v, 4) for v, _ in c["percent"]), [20.0, 25.0, 25.0, 34.6154],
                         "percent values: the two rates, and the relative change of each comparison")

    def test_zero_base(self):
        c = lesson.candidates([ev("p", "errors", "number", "0", "12")])
        self.assertEqual(c["percent"], [], "a change from 0 has no relative change: do not divide by zero")


class TestTrace(unittest.TestCase):
    def setUp(self):
        self.c = lesson.candidates([ev("p", "hours", "number", "6.5", "4.25"), ev("p", "rate", "pct", "20.0", "26.8")])

    def test_rounding_is_allowed(self):
        self.assertEqual(lesson.trace("35", "percent", self.c)[0], "ok", "34.6% rounds to 35%: that is honest")
        self.assertEqual(lesson.trace("34.6", "percent", self.c)[0], "ok")
        self.assertEqual(lesson.trace("6.8", "points", self.c)[0], "ok", "20.0% to 26.8% is 6.8 points")

    def test_inflated_and_understated(self):
        status, value = lesson.trace("40", "percent", self.c)
        self.assertEqual(status, "inflated", "40% against a computed 34.6% is inflated")
        self.assertAlmostEqual(value, 2.25 / 6.5 * 100, places=6, msg="return the evidence value the claim was compared with")
        self.assertEqual(lesson.trace("33", "percent", self.c)[0], "understated", "33% is below 34.6% by more than rounding")

    def test_points_as_percent(self):
        self.assertEqual(lesson.trace("6.8", "percent", self.c)[0], "points_as_percent",
                         "a rate moving from 20.0% to 26.8% rose 6.8 points, which is 34% in relative terms, not 6.8%")

    def test_untraceable(self):
        empty = {"number": [], "percent": [], "points": []}
        self.assertEqual(lesson.trace("100", "number", empty), ("untraceable", None))
        self.assertEqual(lesson.trace("3.0", "points", lesson.candidates([ev("p", "users", "number", "", "30")])),
                         ("untraceable", None), "no points evidence at all for this project")

    def test_tie_goes_to_the_smaller_value(self):
        c = {"number": [(10.0, "a"), (20.0, "b")], "percent": [], "points": []}
        self.assertEqual(lesson.trace("15", "number", c), ("inflated", 10.0),
                         "15 is equally far from 10 and 20: compare with the smaller, so the claim reads as inflated")


class TestResume(unittest.TestCase):
    def test_parse(self):
        text = "Name\n\nSummary\n- one\nJob (job-a)\n- two\n- three\nProjects\nSide (side-b)\n- four\n"
        self.assertEqual(lesson.parse_resume(text), [(None, "one"), ("job-a", "two"), ("job-a", "three"), ("side-b", "four")])

    def test_committed(self):
        resume, rows = committed()
        got = as_tuples(lesson.check_resume(resume, rows))
        self.assertEqual(got, COMMITTED, "the committed resume: one finding per number, in order")
        self.assertEqual(ref_findings(resume, rows), COMMITTED, "the reference agrees with the hand-written findings")

    def test_second_dataset(self):
        statuses = set()
        for seed in (5, 23, 77):
            data = make_data.build(seed=seed)
            rows = [dict(zip(make_data.HEADER, r)) for r in data["evidence"]]
            want = ref_findings(data["resume"], rows)
            statuses.update(s for *_, s in want)
            self.assertEqual(as_tuples(lesson.check_resume(data["resume"], rows)), want,
                             "seed %d: a generated resume, traced against its own evidence" % seed)
        self.assertEqual(statuses, {"ok", "inflated", "understated", "points_as_percent", "untraceable"},
                         "the generated resumes should cover every status")

    def test_empty_resume(self):
        self.assertEqual(lesson.check_resume("", []), [], "no bullets, no findings")
        self.assertEqual(lesson.check_resume("Name\n- No numbers here.\n", []), [])


if __name__ == "__main__":
    unittest.main()
