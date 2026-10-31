"""Tests for lesson 06: explain findings to leadership.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The test has its own checker, written separately below. It checks your check_summary on
hand-made summaries with known problems, your SUMMARY on the committed results, and your
draft_summary on the committed results and on results built in memory from other seeds.
"""
import csv
import importlib.util
import math
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

UP = {"rose", "rise", "risen", "up", "increased", "increase", "improved", "higher", "gained"}
DOWN = {"fell", "fall", "fallen", "down", "decreased", "decrease", "dropped", "drop", "worsened", "lower", "declined"}
FLAT = {"unchanged", "flat"}
DECIDE = {"approve", "decide", "decision", "choose", "agree"}


def committed_results():
    with open(os.path.join(HERE, "data", "results.csv"), newline="") as f:
        return {r["name"]: r["value"] for r in csv.DictReader(f)}


def committed_orders():
    with open(os.path.join(HERE, "data", "orders.csv"), newline="") as f:
        return list(csv.DictReader(f))


def numbers(text):
    """Numbers as written, commas removed. Scans character by character, not with one regex."""
    out, i = [], 0
    while i < len(text):
        ch = text[i]
        starts = ch.isdigit() or (ch == "-" and i + 1 < len(text) and text[i + 1].isdigit())
        prev = text[i - 1] if i else " "
        if starts and not (prev.isalnum() or prev in "_.,"):
            j = i + 1
            while j < len(text) and (text[j].isdigit() or (text[j] in ",." and j + 1 < len(text) and text[j + 1].isdigit())):
                j += 1
            if j < len(text) and (text[j].isalnum() or text[j] == "_"):
                i = j
                continue
            out.append(text[i:j].replace(",", ""))
            i = j
        else:
            i += 1
    return out


def ref_check(text, results):
    if not text.strip():
        return ["empty"]
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    top = " ".join(lines[:2])
    words = set(re.findall(r"[a-z]+", top.lower()))
    size = results["change_pts"].lstrip("-")
    c = float(results["change_pts"])
    right = UP if c > 0 else DOWN if c < 0 else FLAT
    wrong = (UP | DOWN | FLAT) - right
    allowed = {size}
    for v in results.values():
        allowed.update(numbers(v))
    found = []
    if size not in numbers(top):
        found.append("headline")
    if not words & right or words & wrong:
        found.append("direction")
    if not words & DECIDE:
        found.append("decision")
    after = text.replace(" ", "")
    if any(after[m.end():].startswith(("%", "percent")) and (m.start() == 0 or not (after[m.start() - 1].isdigit() or after[m.start() - 1] in ".,"))
           for m in re.finditer(re.escape(size), after)):
        found.append("units")
    if any(n not in allowed for n in numbers(text)):
        found.append("untraceable")
    if not any(x.lower().startswith("caveat:") for x in lines):
        found.append("caveat")
    if len(text.split()) > 100:
        found.append("too_long")
    return sorted(found)


# A small results file written by hand for the edge cases.
R = {"metric": "on-time delivery rate", "control_rate_pct": "80.5", "pilot_rate_pct": "84.5",
     "change_pts": "4.0", "ci_low_pts": "0.4", "ci_high_pts": "7.5", "pilot_orders": "1240",
     "control_orders": "868", "weeks": "4", "decide_by": "13 November", "interval": "95% interval"}
GOOD = ("On-time deliveries rose 4.0 points, from 80.5% to 84.5%.\n"
        "Please approve the new rule for all cities by 13 November.\n"
        "Caveat: one city, 4 weeks.\n")


class TestChecker(unittest.TestCase):
    def check(self, text, results, want, why):
        self.assertEqual(lesson.check_summary(text, results), want, why)

    def test_good_summary(self):
        self.check(GOOD, R, [], "number, direction and decision in the first two lines, every number from the results, a caveat")

    def test_buried_answer(self):
        text = ("We analysed 1,240 orders on the new rule and 868 on the current one over 4 weeks.\n"
                "Orders were assigned at random and on time means delivered by the promised minute.\n"
                "On-time deliveries rose 4.0 points. Please approve the new rule by 13 November.\n"
                "Caveat: one city.\n")
        self.check(text, R, ["decision", "direction", "headline"],
                   "the answer is on line 3, so the first two lines have no headline, direction or decision")

    def test_wrong_direction(self):
        self.check(GOOD.replace("rose", "fell"), R, ["direction"], "the change is +4.0 points, so 'fell' is the wrong direction")
        self.check(GOOD.replace("rose", "moved"), R, ["direction"], "'moved' does not say which way")

    def test_rounding_changes_the_claim(self):
        text = GOOD.replace("4.0 points", "4 points").replace("by 13 November.", "by 13 November. The range is 0 to 8 points.")
        self.check(text, R, ["headline", "untraceable"], "4, 0 and 8 are rounded: 4.0 is not on the first two lines and 0 and 8 are not in the results")
        self.assertEqual(lesson.untraceable_numbers(text + " Not 0 again.", R), ["0", "8"],
                         "list the numbers that are not in the results, in order, each once (4 is allowed: it is the number of weeks)")

    def test_percent_not_points(self):
        self.check(GOOD.replace("4.0 points", "4.0%"), R, ["units"], "the change is 4.0 points; 4.0% is a different claim")

    def test_missing_caveat_and_too_long(self):
        self.check(GOOD.replace("Caveat: one city, 4 weeks.\n", ""), R, ["caveat"], "a summary needs a line that starts with 'Caveat:'")
        long_text = GOOD + "More detail follows here. " * 20
        self.check(long_text, R, ["too_long"], "over 100 words is too long for the VP")

    def test_empty(self):
        self.check("", R, ["empty"], "an empty summary returns ['empty'] and nothing else")
        self.check("   \n\n", R, ["empty"], "blank lines are still empty")

    def test_thousands_and_tricky_tokens(self):
        text = GOOD.replace("from 80.5% to 84.5%", "from 80.5% to 84.5% on 1,240 orders, tracked in GA4 for Q3")
        self.check(text, R, [], "1,240 is 1240 in the results; the 4 in GA4 and the 3 in Q3 are part of a name, not numbers")
        self.assertEqual(lesson.untraceable_numbers(text, R), [])

    def test_negative_change(self):
        r = dict(R, change_pts="-2.1", ci_low_pts="-4.0", ci_high_pts="-0.2", control_rate_pct="82.0", pilot_rate_pct="79.9")
        text = ("On-time deliveries fell 2.1 points, from 82.0% to 79.9%.\n"
                "Please decide by 13 November; I recommend we keep the current rule.\n"
                "The 95% interval is -4.0 to -0.2 points.\nCaveat: one city.\n")
        self.check(text, r, [], "a fall is written as its size, 2.1, with a direction word")
        self.check(text.replace("-0.2", "0.2"), r, ["untraceable"], "dropping the minus sign on -0.2 changes the claim")

    def test_zero_change(self):
        r = dict(R, change_pts="0.0", control_rate_pct="80.1", pilot_rate_pct="80.1")
        text = "On-time deliveries were unchanged at 80.1%, a change of 0.0 points.\nPlease decide by 13 November.\nCaveat: one city.\n"
        self.check(text, r, [], "a change of 0.0 is 'unchanged'")
        self.check(text.replace("unchanged at", "up at"), r, ["direction"], "a change of 0.0 is neither up nor down")


class TestYourSummary(unittest.TestCase):
    def test_results_file_matches_orders(self):
        n, ok = {"current": 0, "new": 0}, {"current": 0, "new": 0}
        for row in committed_orders():
            n[row["rule"]] += 1
            ok[row["rule"]] += int(row["actual_min"]) <= int(row["promised_min"])
        p_new, p_cur = ok["new"] / n["new"], ok["current"] / n["current"]
        se = math.sqrt(p_new * (1 - p_new) / n["new"] + p_cur * (1 - p_cur) / n["current"])
        r = committed_results()
        self.assertEqual(r["pilot_rate_pct"], "%.1f" % (100 * p_new), "data/results.csv is out of date: run python3 make_data.py")
        self.assertEqual(r["change_pts"], "%.1f" % (100 * (p_new - p_cur)))
        self.assertEqual(r["ci_low_pts"], "%.1f" % (100 * (p_new - p_cur - 1.96 * se)))

    def test_your_summary(self):
        text = lesson.SUMMARY
        self.assertTrue(text.strip(), "write your summary for the committed results in SUMMARY")
        problems = ref_check(text, committed_results())
        self.assertEqual(problems, [], "your SUMMARY has these problems: %s" % ", ".join(problems))


class TestDraft(unittest.TestCase):
    def check_draft(self, results, where):
        text = lesson.draft_summary(results)
        problems = ref_check(text, results)
        self.assertEqual(problems, [], "%s: the drafted summary has these problems: %s" % (where, ", ".join(problems)))
        lines = [x for x in text.splitlines() if x.strip()]
        self.assertIn(results["recommendation"], " ".join(lines[:2]), "%s: give the recommendation in the first two lines" % where)

    def test_committed(self):
        self.check_draft(committed_results(), "committed results")

    def test_other_seeds(self):
        verdicts = set()
        for seed in (77, 45, 2024, 13):
            results = make_data.build(seed=seed)["results"]
            verdicts.add(results["verdict"])
            self.check_draft(results, "seed %d (change %s points)" % (seed, results["change_pts"]))
        self.assertEqual(verdicts, {"better", "worse", "unclear"}, "the seeds should cover all three verdicts")

    def test_hand_made_fall(self):
        r = dict(committed_results(), change_pts="-2.1", ci_low_pts="-4.0", ci_high_pts="-0.2",
                 control_rate_pct="82.0", pilot_rate_pct="79.9", verdict="worse", recommendation="keep the current rule")
        self.check_draft(r, "a fall of 2.1 points")


if __name__ == "__main__":
    unittest.main()
