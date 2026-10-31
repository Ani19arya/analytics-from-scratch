"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Kappa is checked a second way: for two labels, kappa = 2(ad - bc) / ((a+b)(b+d) + (a+c)(c+d)),
from the four cells of the 2 by 2 table. The bias counts are recomputed here in plain loops.
"""
import csv
import importlib.util
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 1609


def committed(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if "words" in r:
            r["words"] = int(r["words"])
    return rows


def ref_kappa_2x2(x, y, pos="pass"):
    a = sum(1 for p, q in zip(x, y) if p == pos and q == pos)
    b = sum(1 for p, q in zip(x, y) if p == pos and q != pos)
    c = sum(1 for p, q in zip(x, y) if p != pos and q == pos)
    d = sum(1 for p, q in zip(x, y) if p != pos and q != pos)
    return 2 * (a * d - b * c) / ((a + b) * (b + d) + (a + c) * (c + d))


def ref_false_pass(rows, long_words=120):
    out = {}
    for key, keep in [("short", lambda w: w < long_words), ("long", lambda w: w >= long_words)]:
        both_fail = [r for r in rows if r["rater_a"] == "fail" and r["rater_b"] == "fail" and keep(r["words"])]
        out[key] = (len([r for r in both_fail if r["judge"] == "pass"]), len(both_fail))
    return out


def ref_position(pairs):
    first = 0
    consistent = 0
    for p in pairs:
        if p["judge_x_first"] == "x":
            first += 1
        if p["judge_y_first"] == "y":
            first += 1
        if p["judge_x_first"] == p["judge_y_first"]:
            consistent += 1
    return {"pairs": len(pairs), "consistent": consistent, "first_wins": first}


class TestKappa(unittest.TestCase):
    def test_hand_made(self):
        a = ["pass", "pass", "fail", "fail"]
        po, pe, k = lesson.cohen_kappa(a, ["pass", "fail", "fail", "fail"])
        self.assertAlmostEqual(po, 0.75)
        self.assertAlmostEqual(pe, 0.5 * 0.25 + 0.5 * 0.75)
        self.assertAlmostEqual(k, 0.5)
        self.assertAlmostEqual(lesson.cohen_kappa(a, a)[2], 1.0, msg="identical lists have kappa 1")
        self.assertAlmostEqual(lesson.cohen_kappa(a, ["fail", "fail", "pass", "pass"])[2], -1.0,
                               msg="perfect disagreement on a balanced list has kappa -1")

    def test_always_pass_judge_has_kappa_zero(self):
        people = ["pass"] * 6 + ["fail"] * 4
        po, pe, k = lesson.cohen_kappa(["pass"] * 10, people)
        self.assertAlmostEqual(po, 0.6)
        self.assertAlmostEqual(k, 0.0, msg="a judge that always says pass agrees 60% of the time here, but its kappa is 0")

    def test_undefined_and_bad_input(self):
        self.assertIsNone(lesson.cohen_kappa(["pass"] * 3, ["pass"] * 3)[2],
                          "when both raters only ever use one label, chance agreement is 1 and kappa is undefined: return None")
        with self.assertRaises(ValueError):
            lesson.cohen_kappa([], [])
        with self.assertRaises(ValueError):
            lesson.cohen_kappa(["pass"], ["pass", "fail"])

    def test_three_labels(self):
        a = ["good", "ok", "bad", "good", "ok", "bad"]
        b = ["good", "ok", "ok", "good", "bad", "bad"]
        po, pe, k = lesson.cohen_kappa(a, b)
        self.assertAlmostEqual(po, 4 / 6)
        self.assertAlmostEqual(pe, 3 * (2 / 6) * (2 / 6))
        self.assertAlmostEqual(k, (4 / 6 - 1 / 3) / (1 - 1 / 3))

    def check_kappas(self, rows, label):
        got = lesson.kappas(rows)
        a = [r["rater_a"] for r in rows]
        b = [r["rater_b"] for r in rows]
        j = [r["judge"] for r in rows]
        self.assertAlmostEqual(got["a_vs_b"], ref_kappa_2x2(a, b), msg="%s: kappa for rater A vs rater B" % label)
        self.assertAlmostEqual(got["judge_vs_a"], ref_kappa_2x2(j, a), msg="%s: kappa for judge vs rater A" % label)
        self.assertAlmostEqual(got["judge_vs_b"], ref_kappa_2x2(j, b), msg="%s: kappa for judge vs rater B" % label)
        return got

    def test_committed_kappas(self):
        got = self.check_kappas(committed("answers.csv"), "committed data")
        self.assertLess(got["judge_vs_a"], got["a_vs_b"], "the judge agrees with people less than people agree with each other")

    def test_second_dataset_kappas(self):
        self.check_kappas(make_data.build(seed=OTHER_SEED)["answers"], "seed %d" % OTHER_SEED)


class TestBiases(unittest.TestCase):
    def test_false_pass_small(self):
        rows = [
            {"rater_a": "fail", "rater_b": "fail", "judge": "pass", "words": 200},
            {"rater_a": "fail", "rater_b": "fail", "judge": "fail", "words": 120},
            {"rater_a": "fail", "rater_b": "fail", "judge": "fail", "words": 119},
            {"rater_a": "fail", "rater_b": "pass", "judge": "pass", "words": 50},
            {"rater_a": "pass", "rater_b": "pass", "judge": "pass", "words": 300},
        ]
        self.assertEqual(lesson.false_pass_by_length(rows), {"short": (0, 1), "long": (1, 2)},
                         "count only replies BOTH people failed; 120 words counts as long")
        self.assertEqual(lesson.false_pass_by_length([]), {"short": (0, 0), "long": (0, 0)})

    def test_position_small(self):
        pairs = [
            {"judge_x_first": "x", "judge_y_first": "y", "human": "x"},
            {"judge_x_first": "y", "judge_y_first": "y", "human": "y"},
            {"judge_x_first": "x", "judge_y_first": "x", "human": "y"},
        ]
        self.assertEqual(lesson.position_stats(pairs), {"pairs": 3, "consistent": 2, "first_wins": 4})
        self.assertEqual(lesson.swap_verdicts(pairs), ["tie", "y", "x"],
                         "a pair whose winner changes when the order is swapped is a tie")
        self.assertEqual(lesson.agreement_with_human(pairs, lesson.swap_verdicts(pairs)), (1, 2))
        self.assertEqual(lesson.position_stats([]), {"pairs": 0, "consistent": 0, "first_wins": 0})
        self.assertEqual(lesson.agreement_with_human([], []), (0, 0))

    def check_data(self, answers, pairs, label):
        self.assertEqual(lesson.false_pass_by_length(answers), ref_false_pass(answers), "%s: false passes by length" % label)
        self.assertEqual(lesson.position_stats(pairs), ref_position(pairs), "%s: position counts" % label)
        verdicts = lesson.swap_verdicts(pairs)
        agree = sum(1 for p, v in zip(pairs, verdicts) if v != "tie" and v == p["human"])
        decided = sum(1 for v in verdicts if v != "tie")
        self.assertEqual(lesson.agreement_with_human(pairs, verdicts), (agree, decided), "%s: agreement with the person" % label)

    def test_committed_biases(self):
        answers, pairs = committed("answers.csv"), committed("pairs.csv")
        self.check_data(answers, pairs, "committed data")
        fp = lesson.false_pass_by_length(answers)
        self.assertGreater(fp["long"][0] / fp["long"][1], 3 * fp["short"][0] / fp["short"][1],
                           "the judge should pass long bad replies far more often than short ones")
        self.assertGreater(lesson.position_stats(pairs)["first_wins"], 0.6 * 2 * len(pairs))

    def test_second_dataset_biases(self):
        built = make_data.build(seed=OTHER_SEED)
        self.check_data(built["answers"], built["pairs"], "seed %d" % OTHER_SEED)

    def test_fixture(self):
        with open(os.path.join(HERE, "data", "fixture.json")) as f:
            info = json.load(f)
        self.assertEqual(info["source"], "simulated")
        self.assertTrue(info["model"].startswith("none"))


if __name__ == "__main__":
    unittest.main()
