"""Tests for tools/placement.py. Run from the repo root:

    python3 -m unittest discover -s tools -p "test_*.py"
"""
import json
import math
import os
import sqlite3
import statistics
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
RIGHT_FU = {
    "q01b": "370", "q02b": "select region, max(amount) m from sales group by region having m >= 60",
    "h-sql": "select region, sum(coalesce(amount, 0)) / count(*) a from sales group by region having a > 25",
    "q03b": "b", "q04b": "b", "h-statistics": "2.4",
    "q05b": "4.9", "q06b": "b", "h-metrics": "4.2",
    "q07b": "b", "q08b": "25", "h-dashboards": "76",
    "q09b": "2 7 2", "q10b": "b", "h-python": "3 15.0 3",
    "q11b": "60", "q12b": "b", "q13b": "b", "h-ai": "68.6",
}
WRONG_FU = {
    "q01b": "180", "q02b": "select region, max(amount) from sales group by region having max(amount) > 60",
    "h-sql": "select region, avg(amount) from sales group by region having avg(amount) > 25",
    "q03b": "a", "q04b": "a", "h-statistics": "1.25",
    "q05b": "47", "q06b": "a", "h-metrics": "6.75",
    "q07b": "a", "q08b": "100", "h-dashboards": "60",
    "q09b": "3 3 2", "q10b": "a", "h-python": "4 25.0 10",
    "q11b": "75", "q12b": "a", "q13b": "a", "h-ai": "70",
}


def q(qid):
    return p.BY_ID[qid]


def with_(base, **changes):
    out = dict(base)
    out.update(changes)
    return out


def sequence(answers, max_questions=p.MAX_QUESTIONS):
    """Run the interactive loop with a fixed answer key and return the ids asked, in order."""
    asked = {}
    order = []
    while True:
        nid = p.next_question(asked, None, max_questions)
        if nid is None:
            return order
        asked[nid] = answers.get(nid, "")
        order.append(nid)


def scores_from(counts):
    """counts: {area: (correct, total)} of base-only answers -> a scores dict as grade() returns it."""
    areas = {}
    for a in p.AREAS:
        c, t = counts.get(a, (0, 0))
        items = [{"role": "base", "correct": i < c} for i in range(t)]
        level, confidence, why = p.judge_area(items)
        areas[a] = {"correct": c, "total": t, "level": level, "confidence": confidence, "why": why}
    correct = sum(v["correct"] for v in areas.values())
    total = sum(v["total"] for v in areas.values())
    return {"areas": areas, "correct": correct, "total": total, "base_correct": correct, "base_total": total,
            "results": []}


def run_on(setup, query):
    conn = sqlite3.connect(":memory:")
    try:
        for stmt in setup:
            conn.execute(stmt)
        return conn.execute(query).fetchone()[0]
    finally:
        conn.close()


def run_snippet(code):
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        exec(code, {})
    return buf.getvalue().strip()


class TestQuestions(unittest.TestCase):
    def test_thirteen_base_questions_with_unique_ids_covering_every_area(self):
        self.assertEqual(len(p.QUESTIONS), 13)
        self.assertEqual(len(p.BY_ID), len(p.ALL_QUESTIONS))
        self.assertEqual({x["area"] for x in p.QUESTIONS}, set(p.AREAS))
        self.assertEqual(set(RIGHT), {x["id"] for x in p.QUESTIONS})
        self.assertEqual(set(RIGHT_FU), {x["id"] for x in p.FOLLOW_UPS})
        self.assertEqual(set(WRONG_FU), set(RIGHT_FU))

    def test_every_base_question_has_a_reframe_and_every_area_a_harder_one(self):
        for base in p.QUESTIONS:
            reframes = [x for x in p.FOLLOW_UPS if x["follows"] == base["id"]]
            self.assertEqual(len(reframes), 1, base["id"])
            self.assertEqual(reframes[0]["area"], base["area"])
            self.assertEqual(reframes[0]["role"], "reframe")
        for a in p.AREAS:
            harder = [x for x in p.FOLLOW_UPS if x["area"] == a and x["role"] == "harder"]
            self.assertEqual(len(harder), 1, a)
            self.assertIsNone(harder[0]["follows"])
        self.assertTrue(all(x["role"] == "base" and x["follows"] is None for x in p.QUESTIONS))

    def test_right_and_wrong_keys_grade_as_expected(self):
        for qid, ans in list(RIGHT.items()) + list(RIGHT_FU.items()):
            self.assertTrue(p.check_answer(q(qid), ans), qid)
            self.assertTrue(p.check_answer(q(qid), str(q(qid)["answer"])), qid)
        for qid, ans in list(WRONG.items()) + list(WRONG_FU.items()):
            self.assertFalse(p.check_answer(q(qid), ans), qid)

    # ---- base answers, computed ----
    def test_join_answer_matches_sqlite(self):
        self.assertEqual(run_on(p.JOIN_SETUP, p.JOIN_SQL), q("q01")["answer"])

    def test_python_answer_matches_running_the_snippet(self):
        self.assertEqual(run_snippet(p.PYTHON_SNIPPET), q("q09")["answer"])

    def test_sort_answer_matches_python(self):
        self.assertEqual(sorted(["9", "10", "100"]), ["10", "100", "9"])

    def test_small_eval_margin_in_q12(self):
        self.assertAlmostEqual(1.96 * math.sqrt(0.9 * 0.1 / 50), 0.08, places=2)

    # ---- follow-up answers, computed ----
    def test_fanout_sum_matches_sqlite(self):
        self.assertEqual(run_on(p.FANOUT_SETUP, p.FANOUT_SQL), q("q01b")["answer"])
        self.assertEqual(run_on(p.FANOUT_SETUP, "SELECT SUM(credit) FROM customers WHERE customer_id <= 3"), 170)

    def test_follow_up_sql_results(self):
        self.assertEqual(p.run_sql(p.MAX_SQL), p.run_sql(
            "SELECT 'North', 60 UNION ALL SELECT 'South', 60 UNION ALL SELECT 'West', 120"))
        self.assertEqual(p.run_sql(p.AVG_SQL), p.run_sql(
            "SELECT 'North', 55 UNION ALL SELECT 'South', 50 UNION ALL SELECT 'West', 120"))
        # The traps really are traps: AVG(amount) keeps East (30 over one rep).
        self.assertNotEqual(p.run_sql(WRONG_FU["h-sql"]), p.run_sql(p.AVG_SQL))
        self.assertNotEqual(p.run_sql(WRONG_FU["q02b"]), p.run_sql(p.MAX_SQL))

    def test_delivery_summaries(self):
        d = p.DELIVERY_MINUTES
        self.assertEqual(round(statistics.mean(d), 1), 26.4)
        self.assertEqual(statistics.median(d), 15)
        self.assertEqual((min(d) + max(d)) / 2, 53.5)
        self.assertEqual(round(statistics.mean(d[1:]), 1), 28.8)
        self.assertIn("26.4", q("q03b")["prompt"])
        self.assertIn("28.8", q("q03b")["prompt"])

    def test_two_proportion_z(self):
        (c1, n1), (c2, n2) = p.AB_COUNTS["control"], p.AB_COUNTS["variant"]
        pooled = (c1 + c2) / float(n1 + n2)
        se = math.sqrt(pooled * (1 - pooled) * (1.0 / n1 + 1.0 / n2))
        z = (c2 / float(n2) - c1 / float(n1)) / se
        self.assertAlmostEqual(z, q("h-statistics")["answer"], delta=0.005)
        se_u = math.sqrt((c1 / n1) * (1 - c1 / n1) / n1 + (c2 / n2) * (1 - c2 / n2) / n2)
        self.assertTrue(p.check_answer(q("h-statistics"), "%.2f" % ((c2 / n2 - c1 / n1) / se_u)))
        self.assertIn("200 of 4,000", q("h-statistics")["prompt"])

    def test_campaign_ratio_of_sums(self):
        signups = sum(s for _, s, _ in p.CAMPAIGNS)
        clicks = sum(c for _, _, c in p.CAMPAIGNS)
        self.assertAlmostEqual(100.0 * signups / clicks, q("q05b")["answer"])
        avg_rates = sum(100.0 * s / c for _, s, c in p.CAMPAIGNS) / len(p.CAMPAIGNS)
        self.assertEqual(round(avg_rates), 47)
        self.assertFalse(p.check_answer(q("q05b"), "%.1f" % avg_rates))

    def test_churn_points(self):
        self.assertEqual(10 - 8, 2)
        self.assertAlmostEqual((10 - 8) / 10.0, 0.20)

    def test_mix_effect(self):
        def overall(month):
            rows = [r for r in p.MIX_TABLE if r[0] == month]
            return 100.0 * sum(r[3] for r in rows) / sum(r[2] for r in rows)
        rate = dict(((m, seg), 100.0 * o / v) for m, seg, v, o in p.MIX_TABLE)
        for seg in ("Desktop", "Mobile"):
            self.assertGreater(rate[(2, seg)], rate[(1, seg)])
        self.assertAlmostEqual(overall(1), 6.8)
        self.assertAlmostEqual(overall(2), q("h-metrics")["answer"])
        self.assertAlmostEqual((rate[(2, "Desktop")] + rate[(2, "Mobile")]) / 2, 6.75)
        for m, seg, v, o in p.MIX_TABLE:
            self.assertIn("%d     | %-7s | %6d | %6d" % (m, seg, v, o), q("h-metrics")["prompt"])

    def test_region_share(self):
        total = sum(a for _, a in p.REGION_SALES)
        east = sum(a for r, a in p.REGION_SALES if r == "East")
        north = sum(a for r, a in p.REGION_SALES if r == "North")
        self.assertAlmostEqual(100.0 * east / total, q("q08b")["answer"])
        self.assertAlmostEqual(100.0 * north / total, q("q08")["answer"])

    def test_grain_average_matches_sqlite(self):
        self.assertAlmostEqual(run_on(p.GRAIN_SETUP, p.GRAIN_SQL), q("h-dashboards")["answer"])
        self.assertAlmostEqual(run_on(p.GRAIN_SETUP, "SELECT AVG(amount) FROM orders"), 60)

    def test_follow_up_python_snippets(self):
        self.assertEqual(run_snippet(p.PYTHON_SNIPPET_B), q("q09b")["answer"])
        self.assertEqual(run_snippet(p.PYTHON_SNIPPET_H), q("h-python")["answer"])
        self.assertEqual("7" * 2 + "3", "773")

    def test_recall_and_f1(self):
        f = p.FRAUD
        self.assertAlmostEqual(100.0 * f["flagged_and_real"] / f["real"], q("q11b")["answer"])
        self.assertAlmostEqual(100.0 * f["flagged_and_real"] / f["flagged"], 75.0)
        t = p.THRESHOLD
        prec, rec = t["flagged_and_real"] / float(t["flagged"]), t["flagged_and_real"] / float(t["real"])
        self.assertAlmostEqual(100 * 2 * prec * rec / (prec + rec), q("h-ai")["answer"], delta=0.05)
        self.assertAlmostEqual(1.96 * math.sqrt(0.9 * 0.1 / 20), 0.13, places=2)  # "about 13 points" in q12b


class TestGrade(unittest.TestCase):
    def test_all_correct(self):
        s = p.grade(RIGHT)
        self.assertEqual((s["correct"], s["total"]), (13, 13))
        for a in p.AREAS:
            self.assertEqual(s["areas"][a]["correct"], s["areas"][a]["total"])
            self.assertEqual((s["areas"][a]["level"], s["areas"][a]["confidence"]), ("strong", "high"))

    def test_all_wrong(self):
        s = p.grade(WRONG)
        self.assertEqual(s["correct"], 0)
        self.assertTrue(all(not r["correct"] for r in s["results"]))
        self.assertTrue(all(s["areas"][a]["level"] == "weak" for a in p.AREAS))

    def test_blank_and_missing_are_wrong(self):
        self.assertEqual(p.grade({})["correct"], 0)
        self.assertEqual(p.grade({})["total"], 13)
        self.assertEqual(p.grade(dict((k, "") for k in RIGHT))["correct"], 0)

    def test_mixed(self):
        mixed = dict(WRONG)
        for k in ("q01", "q02", "q11", "q12"):
            mixed[k] = RIGHT[k]
        s = p.grade(mixed)
        self.assertEqual(s["correct"], 4)
        self.assertEqual(s["areas"]["sql"]["correct"], 2)
        self.assertEqual(s["areas"]["ai"]["correct"], 2)
        self.assertEqual(s["areas"]["ai"]["total"], 3)
        self.assertEqual(s["areas"]["ai"]["level"], "mixed")  # one miss, follow-up not in the file
        self.assertEqual(s["areas"]["metrics"]["correct"], 0)

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
        z = q("h-statistics")
        for ok in ("2.43", "2.4", "2.426", "2.48"):
            self.assertTrue(p.check_answer(z, ok), ok)
        for bad in ("1.96", "2.5", "2.3"):
            self.assertFalse(p.check_answer(z, bad), bad)

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


class TestAdaptive(unittest.TestCase):
    def test_all_right_asks_only_the_base_questions(self):
        self.assertEqual(sequence(RIGHT), [x["id"] for x in p.QUESTIONS])
        self.assertIsNone(p.next_question(RIGHT))

    def test_base_questions_come_first_in_order(self):
        self.assertEqual(p.next_question({}), "q01")
        self.assertEqual(p.next_question({"q01": ""}), "q02")
        self.assertEqual(p.next_question({"q02": "x"}), "q01")

    def test_one_slip_asks_the_reframe_of_that_question(self):
        ans = with_(RIGHT, q04="a")
        self.assertEqual(p.next_question(ans), "q04b")
        self.assertIsNone(p.next_question(with_(ans, q04b="b")))
        self.assertEqual(sequence(with_(ans, **RIGHT_FU))[13:], ["q04b"])

    def test_missed_reframe_asks_the_harder_one(self):
        ans = with_(RIGHT, q04="a", q04b="a")
        self.assertEqual(p.next_question(ans), "h-statistics")
        self.assertIsNone(p.next_question(with_(ans, **{"h-statistics": "2.43"})))
        self.assertIsNone(p.next_question(with_(ans, **{"h-statistics": "9"})))

    def test_two_misses_in_an_area_ask_no_follow_up(self):
        self.assertEqual(sequence(with_(RIGHT, q01="4", q02="x")), [x["id"] for x in p.QUESTIONS])

    def test_ai_area_with_three_base_questions(self):
        ans = with_(RIGHT, q12="a")
        self.assertEqual(p.next_question(ans), "q12b")
        self.assertEqual(p.next_question(with_(ans, q12b="a")), "h-ai")
        self.assertEqual(sequence(with_(RIGHT, q11="1", q13="a")), [x["id"] for x in p.QUESTIONS])

    def test_round_one_covers_every_area_before_any_harder_question(self):
        ans = with_(RIGHT, q02="x", q03="a", q06="a", q07="a", q10="a", q11="1")
        ans.update(WRONG_FU)
        order = sequence(ans)
        self.assertEqual(order[13:19], ["q02b", "q03b", "q06b", "q07b", "q10b", "q11b"])
        self.assertEqual(order[19:], ["h-sql"])

    def test_cap_is_respected(self):
        ans = with_(RIGHT, q02="x", q03="a", q06="a", q07="a", q10="a", q11="1")
        ans.update(WRONG_FU)
        self.assertEqual(len(sequence(ans)), p.MAX_QUESTIONS)
        self.assertEqual(p.MAX_QUESTIONS, 20)
        self.assertEqual(len(sequence(ans, max_questions=15)), 15)
        self.assertEqual(sequence(ans, max_questions=15)[13:], ["q02b", "q03b"])
        self.assertEqual(len(sequence(ans, max_questions=5)), 13)  # base questions are always asked
        s = p.grade(ans)
        self.assertEqual(s["total"], 20)
        self.assertEqual(s["asked"], sequence(ans))
        # Cut by the cap: statistics had a missed reframe and no harder question.
        self.assertEqual(s["areas"]["statistics"]["asked"], ["q03", "q04", "q03b"])
        self.assertEqual(s["areas"]["statistics"]["level"], "weak")

    def test_next_question_is_pure(self):
        ans = with_(RIGHT, q04="a")
        before = dict(ans)
        self.assertEqual(p.next_question(ans), p.next_question(ans))
        self.assertEqual(ans, before)

    def test_file_replay_ignores_follow_ups_the_rule_does_not_call_for(self):
        full = with_(RIGHT, **WRONG_FU)
        s = p.grade(full)
        self.assertEqual(s["total"], 13)
        self.assertEqual(s["correct"], 13)

    def test_file_replay_skips_blank_follow_ups(self):
        ans = with_(RIGHT, q04="a")
        ans.update(dict((k, "") for k in RIGHT_FU))
        s = p.grade(ans)
        self.assertEqual(s["asked"], [x["id"] for x in p.QUESTIONS])
        self.assertEqual(s["areas"]["statistics"]["level"], "mixed")

    def test_file_without_the_reframe_uses_the_harder_one(self):
        ans = with_(RIGHT, q04="a", **{"h-statistics": "2.43"})
        self.assertEqual(p.asked_sequence(ans)[13:], ["h-statistics"])
        self.assertEqual(p.grade(ans)["areas"]["statistics"]["level"], "strong")

    def test_interactive_blank_follow_up_counts_as_wrong(self):
        ans = with_(RIGHT, q04="a", q04b="")
        asked = [x["id"] for x in p.QUESTIONS] + ["q04b"]
        s = p.grade(ans, asked)
        self.assertEqual(s["areas"]["statistics"]["total"], 3)
        self.assertEqual(s["areas"]["statistics"]["correct"], 1)


class TestLevels(unittest.TestCase):
    def items(self, *pattern):
        """pattern: strings like 'B+' (base right), 'B-', 'F+' (follow-up right), 'F-'."""
        return [{"role": "base" if x[0] == "B" else "reframe", "correct": x[1] == "+"} for x in pattern]

    def judge(self, *pattern):
        return p.judge_area(self.items(*pattern))[:2]

    def test_one_slip_is_no_longer_weak(self):
        # Old rule: 1 of 2 was below 2/3, so an analyst with one careless slip was sent back.
        self.assertEqual(self.judge("B+", "B-"), ("mixed", "low"))
        self.assertEqual(self.judge("B+", "B-", "F+"), ("strong", "medium"))
        self.assertEqual(self.judge("B-", "B+", "F+"), ("strong", "medium"))

    def test_rule_table(self):
        cases = [
            (("B+", "B+"), ("strong", "high")),
            (("B-", "B-"), ("weak", "high")),
            (("B+", "B-", "F-"), ("weak", "medium")),
            (("B+", "B-", "F-", "F+"), ("mixed", "medium")),
            (("B+", "B-", "F-", "F-"), ("weak", "high")),
            (("B+", "B+", "B+"), ("strong", "high")),
            (("B+", "B-", "B+"), ("mixed", "low")),           # one miss, no follow-up answered
            (("B+", "B-", "B+", "F+"), ("strong", "high")),
            (("B+", "B-", "B+", "F-"), ("mixed", "medium")),
            (("B+", "B-", "B+", "F-", "F+"), ("mixed", "medium")),
            (("B+", "B-", "B+", "F-", "F-"), ("weak", "low")),
            (("B+", "B-", "B-"), ("weak", "medium")),
            (("B-", "B-", "B-"), ("weak", "high")),
            ((), ("mixed", "low")),
        ]
        for pattern, expected in cases:
            self.assertEqual(self.judge(*pattern), expected, pattern)

    def test_why_names_the_counts_and_confidence(self):
        why = p.judge_area(self.items("B+", "B-", "F+"))[2]
        self.assertIn("2 of 3 right", why)
        self.assertIn("slip", why)
        self.assertIn("Confidence medium", why)

    def test_beginner_boundary_uses_base_questions(self):
        self.assertFalse(p.is_beginner({"correct": 4, "total": 10}))  # exactly 40% is not beginner
        self.assertTrue(p.is_beginner({"correct": 3, "total": 10}))
        self.assertTrue(p.is_beginner({"correct": 5, "total": 13}))   # 38%
        self.assertFalse(p.is_beginner({"correct": 6, "total": 13}))  # 46%
        # Missed follow-ups do not push you below the line.
        self.assertFalse(p.is_beginner({"correct": 6, "total": 19, "base_correct": 6, "base_total": 13}))


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
            self.assertEqual(rec["skim"], [])
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
            self.assertEqual(rec["skim"], [])
            self.assertEqual(len(rec["do_not_skip_yet"]), len(p.FAST_TRACK[track]["skip"]))

    def test_one_slip_skims_instead_of_redoing(self):
        # Data analyst, one careless slip in statistics, follow-up not answered: mixed, skim 02-01.
        rec = p.recommend(p.grade(with_(RIGHT, q03="a")), "data-analyst", LESSONS)
        self.assertEqual(rec["levels"]["statistics"], "mixed")
        self.assertEqual([k["id"] for k in rec["skim"]], ["02-01"])
        self.assertEqual(rec["skim"][0]["why"], p.SKIM_WHY)
        self.assertNotIn("02-01", [k["id"] for k in rec["skip"]])
        self.assertEqual(rec["do_not_skip_yet"], [])
        self.assertEqual(rec["start"]["id"], "02-03")  # mixed counts as not strong
        # The same slip with the follow-up right: strong, 02-01 is safe to skip.
        rec = p.recommend(p.grade(with_(RIGHT, q03="a", q03b="b")), "data-analyst", LESSONS)
        self.assertEqual(rec["levels"]["statistics"], "strong")
        self.assertIn("02-01", [k["id"] for k in rec["skip"]])
        self.assertEqual(rec["start"]["id"], "10-01")

    def test_start_is_first_gap_and_depends_on_track(self):
        # Strong in SQL and dashboards, mixed in statistics and metrics, weak in Python and AI.
        s = scores_from({"sql": (2, 2), "dashboards": (2, 2), "statistics": (1, 2), "metrics": (1, 2),
                         "python": (0, 2), "ai": (0, 3)})
        expect = {"data-analyst": "02-03", "bi-analyst": "03-05", "business-analyst": "03-05",
                  "interview-prep": "07-02"}
        for track, start in expect.items():
            rec = p.recommend(s, track, LESSONS)
            self.assertEqual(rec["start"]["id"], start, track)
            self.assertEqual(rec["strong_areas"], ["sql", "dashboards"])
            self.assertEqual(rec["mixed_areas"], ["statistics", "metrics"])
            self.assertEqual(rec["weak_areas"], ["python", "ai"])
            for k in rec["skip"]:
                self.assertIn(k["area"], ("sql", "dashboards"))
            for k in rec["skim"]:
                self.assertIn(k["area"], ("statistics", "metrics"))
            for k in rec["do_not_skip_yet"]:
                self.assertIn(k["area"], ("python", "ai"))
        bi = p.recommend(s, "bi-analyst", LESSONS)
        self.assertIn("04-04", [k["id"] for k in bi["skip"]])
        da = p.recommend(s, "data-analyst", LESSONS)
        self.assertIn("02-01", [k["id"] for k in da["skim"]])
        self.assertIn("05-01", [k["id"] for k in da["do_not_skip_yet"]])

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
        for x in p.FOLLOW_UPS:
            for lid in x["lessons"]:
                self.assertIn(lid, p.referenced_ids())
        for lid in p.referenced_ids():
            self.assertIn(lid, LESSONS)
            self.assertEqual(LESSONS[lid]["status"], "live")
            self.assertTrue(os.path.isdir(os.path.join(ROOT, LESSONS[lid]["path"])))

    def test_validate_fails_loudly(self):
        broken = dict(LESSONS)
        del broken["01-03"]
        planned = dict(LESSONS)
        planned["04-02"] = dict(planned["04-02"], status="planned")
        followup_only = dict(LESSONS)
        del followup_only["03-09"]  # only h-metrics and FAST_TRACK use it
        for lessons, word in ((broken, "01-03 is not in curriculum.json"), (planned, "04-02 is planned"),
                              (followup_only, "03-09 is not in curriculum.json")):
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

    def test_json_shape(self):
        path = self.write_answers({"track": "data-analyst", "answers": with_(RIGHT, q04="a", q04b="b")})
        out = json.loads(self.run_cli(["--answers", path, "--json"]).stdout)
        sc, rec = out["scores"], out["recommendation"]
        self.assertEqual(set(sc), {"areas", "correct", "total", "base_correct", "base_total", "asked",
                                   "max_questions", "level_rule", "results"})
        self.assertEqual(set(sc["areas"]), set(p.AREAS))
        for a in p.AREAS:
            self.assertEqual(set(sc["areas"][a]), {"correct", "total", "level", "confidence", "why", "asked"})
            self.assertIn(sc["areas"][a]["level"], p.LEVELS)
            self.assertIn(sc["areas"][a]["confidence"], ("high", "medium", "low"))
        self.assertEqual(sc["areas"]["statistics"]["asked"], ["q03", "q04", "q04b"])
        self.assertEqual((sc["total"], sc["base_total"], sc["max_questions"]), (14, 13, 20))
        self.assertEqual(sc["results"][-1]["role"], "reframe")
        self.assertEqual(sc["results"][-1]["follows"], "q04")
        self.assertEqual(set(rec), {"track", "track_title", "beginner", "levels", "strong_areas", "mixed_areas",
                                    "weak_areas", "start", "path", "skip", "skim", "do_not_skip_yet"})
        self.assertIn(rec["path"][0]["level"], p.LEVELS)

    def test_track_flag_overrides_file_and_text_report(self):
        path = self.write_answers({"track": "bi-analyst", "answers": WRONG})
        proc = self.run_cli(["--answers", path, "--track", "interview-prep"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Interview prep", proc.stdout)
        self.assertIn("Start here: 00-01", proc.stdout)
        self.assertIn("why this level: 0 of 2 right", proc.stdout)

    def test_interactive_reveals_nothing_until_the_end(self):
        stdin = "2\n" + "\n".join(RIGHT[x["id"]] for x in p.QUESTIONS) + "\n"
        proc = self.run_cli([], stdin=stdin)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        before, _, after = proc.stdout.partition("Placement result")
        self.assertNotIn("answer: ", before)
        self.assertNotIn("Level per area", before)
        for x in p.ALL_QUESTIONS:
            self.assertNotIn(x["explanation"], before)
        self.assertIn("13 / 13", after)
        self.assertIn("BI analyst", after)

    def test_interactive_slip_then_follow_up(self):
        # q04 missed, then the follow-up q04b (the 14th question) answered right.
        answers = [RIGHT[x["id"]] for x in p.QUESTIONS]
        answers[3] = "a"
        stdin = "1\n" + "\n".join(answers + ["b"]) + "\n"
        proc = self.run_cli([], stdin=stdin)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        before, _, after = proc.stdout.partition("Placement result")
        self.assertIn("[14] Statistics", before)
        self.assertIn(q("q04b")["prompt"].splitlines()[0], before)
        self.assertNotIn("[15]", before)
        self.assertNotIn("answer: ", before)
        self.assertNotIn(q("q04")["explanation"], before)
        self.assertIn("Statistics       2 / 3  strong  confidence medium", after)
        self.assertIn("(follow-up)", after)

    def test_template_and_markdown(self):
        proc = self.run_cli(["--template"])
        data = json.loads(proc.stdout)
        self.assertEqual(set(data["answers"]), set(RIGHT) | set(RIGHT_FU))
        self.assertIn("note", data)
        proc = self.run_cli(["--markdown"])
        self.assertIn("## Fast track", proc.stdout)


if __name__ == "__main__":
    unittest.main()
