"""Tests for tools/placement.py. Run from the repo root:

    python3 -m unittest discover -s tools -p "test_*.py"
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import placement as p  # noqa: E402

ROOT = p.ROOT
LESSONS = p.load_curriculum()
RIGHT = {
    "q01": "6", "q02": "select region, sum(amount) as total from sales group by region having total > 100",
    "q03": "b", "q04": "b", "q05": "6", "q06": "b", "q07": "b", "q08": "30", "q09": "1 200",
    "q10": "b", "q11": "50", "q12": "b", "q13": "b",
}
WRONG = {
    "q01": "4", "q02": "SELECT region, SUM(amount) FROM sales GROUP BY region HAVING SUM(amount) >= 100",
    "q03": "a", "q04": "a", "q05": "21.7", "q06": "a", "q07": "a", "q08": "100", "q09": "2 120",
    "q10": "a", "q11": "75", "q12": "a", "q13": "a",
}


def q(qid):
    return next(x for x in p.QUESTIONS if x["id"] == qid)


def scores_from(counts):
    """counts: {area: (correct, total)} -> a scores dict as grade() returns it."""
    areas = dict((a, {"correct": 0, "total": 0}) for a in p.AREAS)
    for a, (c, t) in counts.items():
        areas[a] = {"correct": c, "total": t}
    return {"areas": areas, "correct": sum(v["correct"] for v in areas.values()),
            "total": sum(v["total"] for v in areas.values()), "results": []}


class TestQuestions(unittest.TestCase):
    def test_about_twelve_questions_with_unique_ids_covering_every_area(self):
        self.assertTrue(10 <= len(p.QUESTIONS) <= 15)
        self.assertEqual(len({x["id"] for x in p.QUESTIONS}), len(p.QUESTIONS))
        self.assertEqual({x["area"] for x in p.QUESTIONS}, set(p.AREAS))
        self.assertEqual(set(RIGHT), {x["id"] for x in p.QUESTIONS})

    def test_join_answer_matches_sqlite(self):
        import sqlite3
        conn = sqlite3.connect(":memory:")
        for stmt in p.JOIN_SETUP:
            conn.execute(stmt)
        self.assertEqual(conn.execute(p.JOIN_SQL).fetchone()[0], q("q01")["answer"])

    def test_python_answer_matches_running_the_snippet(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(p.PYTHON_SNIPPET, {})
        self.assertEqual(buf.getvalue().strip(), q("q09")["answer"])

    def test_sort_answer_matches_python(self):
        self.assertEqual(sorted(["9", "10", "100"]), ["10", "100", "9"])


class TestGrade(unittest.TestCase):
    def test_all_correct(self):
        s = p.grade(RIGHT)
        self.assertEqual((s["correct"], s["total"]), (len(p.QUESTIONS), len(p.QUESTIONS)))
        for a in p.AREAS:
            self.assertEqual(s["areas"][a]["correct"], s["areas"][a]["total"])

    def test_all_wrong(self):
        s = p.grade(WRONG)
        self.assertEqual(s["correct"], 0)
        self.assertTrue(all(not r["correct"] for r in s["results"]))

    def test_blank_and_missing_are_wrong(self):
        self.assertEqual(p.grade({})["correct"], 0)
        self.assertEqual(p.grade(dict((k, "") for k in RIGHT))["correct"], 0)

    def test_mixed(self):
        mixed = dict(WRONG)
        for k in ("q01", "q02", "q11", "q12"):
            mixed[k] = RIGHT[k]
        s = p.grade(mixed)
        self.assertEqual(s["correct"], 4)
        self.assertEqual(s["areas"]["sql"], {"correct": 2, "total": 2})
        self.assertEqual(s["areas"]["ai"], {"correct": 2, "total": 3})
        self.assertEqual(s["areas"]["metrics"], {"correct": 0, "total": 2})

    def test_choice_forms(self):
        for ok in ("b", "B", " b ", "b)", "(b)", "b) the median"):
            self.assertTrue(p.check_answer(q("q03"), ok), ok)
        for bad in ("a", "bb", "banana", "", None):
            self.assertFalse(p.check_answer(q("q03"), bad), bad)

    def test_numeric_tolerance(self):
        q05 = q("q05")  # 6.0 with tolerance 0.1, percent
        for ok in ("6", "6.0", "6%", " 6.1 ", "5.9", "0.06"):
            self.assertTrue(p.check_answer(q05, ok), ok)
        for bad in ("6.2", "5.8", "21.7", "six", "0.6"):
            self.assertFalse(p.check_answer(q05, bad), bad)
        q01 = q("q01")  # exact count
        self.assertTrue(p.check_answer(q01, "6"))
        self.assertTrue(p.check_answer(q01, "6.0"))
        self.assertFalse(p.check_answer(q01, "6.5"))

    def test_text_answer_ignores_extra_spaces(self):
        self.assertTrue(p.check_answer(q("q09"), "  1   200 "))
        self.assertFalse(p.check_answer(q("q09"), "1 120"))

    def test_sql_graded_by_result_not_text(self):
        q02 = q("q02")
        for ok in (
            "SELECT region, SUM(amount) FROM sales GROUP BY region HAVING SUM(amount) > 100",
            "select sum(amount) t, region from sales group by 2 having t > 100",
            "WITH t AS (SELECT region, SUM(amount) AS s FROM sales GROUP BY region) SELECT region, s FROM t WHERE s > 100",
            "SELECT region, total FROM (SELECT region, SUM(amount) total FROM sales GROUP BY region) WHERE total > 100.0 ORDER BY total DESC",
        ):
            self.assertTrue(p.check_answer(q02, ok), ok)
        for bad in (
            "SELECT region, SUM(amount) FROM sales GROUP BY region HAVING SUM(amount) >= 100",
            "SELECT region, SUM(amount) FROM sales GROUP BY region",
            "SELECT region FROM sales GROUP BY region HAVING SUM(amount) > 100",
            "SELECT region, amount FROM sales WHERE amount > 100",
            "not sql at all",
        ):
            self.assertFalse(p.check_answer(q02, bad), bad)

    def test_sql_cannot_write_or_run_two_statements(self):
        q02 = q("q02")
        self.assertFalse(p.check_answer(q02, "DELETE FROM sales"))
        self.assertFalse(p.check_answer(q02, "DROP TABLE sales"))
        self.assertFalse(p.check_answer(q02, RIGHT["q02"] + "; DELETE FROM sales"))
        with self.assertRaises(ValueError):
            p.run_sql("WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) SELECT COUNT(*) FROM n",
                      step_limit=50)


class TestThresholds(unittest.TestCase):
    def test_strong_boundary(self):
        self.assertTrue(p.is_strong({"correct": 2, "total": 3}))   # exactly 2/3
        self.assertFalse(p.is_strong({"correct": 1, "total": 2}))  # 1/2 is below 2/3
        self.assertTrue(p.is_strong({"correct": 2, "total": 2}))
        self.assertFalse(p.is_strong({"correct": 0, "total": 0}))

    def test_beginner_boundary(self):
        self.assertFalse(p.is_beginner({"correct": 4, "total": 10}))  # exactly 40% is not beginner
        self.assertTrue(p.is_beginner({"correct": 3, "total": 10}))
        self.assertTrue(p.is_beginner({"correct": 5, "total": 13}))   # 38%
        self.assertFalse(p.is_beginner({"correct": 6, "total": 13}))  # 46%


class TestRecommend(unittest.TestCase):
    def test_every_track_all_correct(self):
        s = p.grade(RIGHT)
        for track in p.TRACK_ORDER:
            rec = p.recommend(s, track, LESSONS)
            self.assertFalse(rec["beginner"])
            self.assertEqual(set(rec["strong_areas"]), set(p.AREAS))
            skips = [k["id"] for k in rec["skip"]]
            self.assertEqual(skips, [i for i, _, _ in p.FAST_TRACK[track]["skip"]])
            self.assertEqual(rec["do_not_skip_yet"], [])
            first_core = next(i for i, a, _ in p.FAST_TRACK[track]["do"] if a is None)
            self.assertEqual(rec["start"]["id"], first_core)
            self.assertEqual(rec["start"]["path"], LESSONS[first_core]["path"])

    def test_all_wrong_sends_everyone_to_the_beginning(self):
        s = p.grade(WRONG)
        for track in p.TRACK_ORDER:
            rec = p.recommend(s, track, LESSONS)
            self.assertTrue(rec["beginner"])
            self.assertEqual(rec["start"]["id"], "00-01")
            self.assertEqual(rec["skip"], [])
            self.assertEqual(len(rec["do_not_skip_yet"]), len(p.FAST_TRACK[track]["skip"]))

    def test_start_is_first_gap_and_depends_on_track(self):
        # Strong in SQL and dashboards, weak elsewhere, 6 of 13 (not beginner).
        s = scores_from({"sql": (2, 2), "dashboards": (2, 2), "statistics": (1, 2), "metrics": (1, 2),
                         "python": (0, 2), "ai": (0, 3)})
        expect = {"data-analyst": "02-03", "bi-analyst": "03-05", "business-analyst": "03-05",
                  "interview-prep": "07-02"}
        for track, start in expect.items():
            rec = p.recommend(s, track, LESSONS)
            self.assertEqual(rec["start"]["id"], start, track)
            self.assertEqual(rec["strong_areas"], ["sql", "dashboards"])
            for k in rec["skip"]:
                self.assertIn(k["area"], ("sql", "dashboards"))
        bi = p.recommend(s, "bi-analyst", LESSONS)
        self.assertIn("04-04", [k["id"] for k in bi["skip"]])
        da = p.recommend(s, "data-analyst", LESSONS)
        self.assertIn("02-01", [k["id"] for k in da["do_not_skip_yet"]])

    def test_dashboards_gap_starts_bi_at_grain(self):
        s = scores_from({"sql": (2, 2), "dashboards": (0, 2), "statistics": (2, 2), "metrics": (2, 2),
                         "python": (2, 2), "ai": (3, 3)})
        self.assertEqual(p.recommend(s, "bi-analyst", LESSONS)["start"]["id"], "00-03")
        self.assertEqual(p.recommend(s, "data-analyst", LESSONS)["start"]["id"], "10-01")

    def test_unknown_track(self):
        with self.assertRaises(ValueError):
            p.recommend(p.grade(RIGHT), "astronaut", LESSONS)


class TestReferences(unittest.TestCase):
    def test_every_referenced_id_exists_and_is_live(self):
        p.validate(LESSONS)
        for lid in p.referenced_ids():
            self.assertIn(lid, LESSONS)
            self.assertEqual(LESSONS[lid]["status"], "live")
            self.assertTrue(os.path.isdir(os.path.join(ROOT, LESSONS[lid]["path"])))

    def test_validate_fails_loudly(self):
        broken = dict(LESSONS)
        del broken["01-03"]
        planned = dict(LESSONS)
        planned["04-02"] = dict(planned["04-02"], status="planned")
        for lessons, word in ((broken, "01-03 is not in curriculum.json"), (planned, "04-02 is planned")):
            with self.assertRaises(ValueError) as ctx:
                p.validate(lessons)
            self.assertIn(word, str(ctx.exception))

    def test_docs_match_the_table(self):
        with open(os.path.join(ROOT, "LEARNING_ROADMAP.md"), encoding="utf-8") as f:
            self.assertIn(p.render_roadmap_markdown(LESSONS), f.read())
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            self.assertIn(p.render_readme_markdown(LESSONS), f.read())


class TestCli(unittest.TestCase):
    def run_cli(self, args, stdin=None):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([sys.executable, os.path.join(HERE, "placement.py")] + args, input=stdin,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
                              cwd=ROOT, env=env, timeout=60)
        return proc

    def write_answers(self, data):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        self.addCleanup(os.remove, path)
        return path

    def test_answers_json(self):
        path = self.write_answers({"track": "bi-analyst", "answers": RIGHT})
        proc = self.run_cli(["--answers", path, "--json"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual(out["scores"]["correct"], len(p.QUESTIONS))
        self.assertEqual(out["recommendation"]["track"], "bi-analyst")
        self.assertEqual(out["recommendation"]["start"]["id"], "08-01")

    def test_track_flag_overrides_file_and_text_report(self):
        path = self.write_answers({"track": "bi-analyst", "answers": WRONG})
        proc = self.run_cli(["--answers", path, "--track", "interview-prep"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Interview prep", proc.stdout)
        self.assertIn("Start here: 00-01", proc.stdout)

    def test_interactive_reveals_nothing_until_the_end(self):
        stdin = "2\n" + "\n".join(RIGHT[x["id"]] for x in p.QUESTIONS) + "\n"
        proc = self.run_cli([], stdin=stdin)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        before, _, after = proc.stdout.partition("Placement result")
        self.assertNotIn("answer: ", before)
        self.assertNotIn("Score per area", before)
        for x in p.QUESTIONS:
            self.assertNotIn(x["explanation"], before)
        self.assertIn("13 / 13", after)
        self.assertIn("BI analyst", after)

    def test_template_and_markdown(self):
        proc = self.run_cli(["--template"])
        self.assertEqual(set(json.loads(proc.stdout)["answers"]), set(RIGHT))
        proc = self.run_cli(["--markdown"])
        self.assertIn("## Fast track", proc.stdout)


if __name__ == "__main__":
    unittest.main()
