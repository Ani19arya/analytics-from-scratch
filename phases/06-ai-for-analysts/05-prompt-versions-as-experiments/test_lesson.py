"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

The expected p-values are worked out here a second way: a row of Pascal's triangle built
by addition, and the two-sided p-value as the total chance of every outcome no more likely
than the one observed. The functions also run on a second dataset built from another seed.
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

OTHER_SEED = 1610


def committed(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def pascal_row(n):
    row = [1]
    for _ in range(n):
        row = [1] + [row[i] + row[i + 1] for i in range(len(row) - 1)] + [1]
    return row


def ref_p(k, n):
    """Sum the chance of every outcome that is no more likely than k (exact, in integers)."""
    if n == 0:
        return 1.0
    row = pascal_row(n)
    return min(1.0, sum(c for c in row if c <= row[k]) / 2 ** n)


def ref_compare(gold, run_a, run_b, alpha=0.05):
    g = {r["ticket_id"]: r["gold_label"] for r in gold}
    a = {r["ticket_id"]: r["label"] for r in run_a}
    b = {r["ticket_id"]: r["label"] for r in run_b}
    a_only = sum(1 for t in g if a[t] == g[t] and b[t] != g[t])
    b_only = sum(1 for t in g if a[t] != g[t] and b[t] == g[t])
    p = ref_p(b_only, a_only + b_only)
    verdict = "no clear difference"
    if p < alpha:
        verdict = "v2 better" if b_only > a_only else "v1 better"
    return {"acc_a": sum(a[t] == g[t] for t in g) / len(g), "acc_b": sum(b[t] == g[t] for t in g) / len(g),
            "a_only": a_only, "b_only": b_only, "p_value": p, "verdict": verdict}


def make_pairs(cells):
    """cells = (both right, only a, only b, both wrong) -> pairs with gold 'x' and wrong label 'y'."""
    both, a_only, b_only, neither = cells
    pairs = []
    for count, a, b in ((both, "x", "x"), (a_only, "x", "y"), (b_only, "y", "x"), (neither, "y", "y")):
        for _ in range(count):
            pairs.append({"ticket_id": "t%04d" % len(pairs), "gold": "x", "a": a, "b": b})
    return pairs


class TestPairing(unittest.TestCase):
    GOLD = [{"ticket_id": "t1", "gold_label": "bug"}, {"ticket_id": "t2", "gold_label": "refund"}]

    def test_pairs_by_id_not_by_row_order(self):
        a = [{"ticket_id": "t2", "label": "refund"}, {"ticket_id": "t1", "label": "other"}]
        b = [{"ticket_id": "t1", "label": "bug"}, {"ticket_id": "t2", "label": "billing"}]
        pairs = lesson.pair_runs(self.GOLD, a, b)
        self.assertEqual(pairs, [{"ticket_id": "t1", "gold": "bug", "a": "other", "b": "bug"},
                                 {"ticket_id": "t2", "gold": "refund", "a": "refund", "b": "billing"}],
                         "join on ticket_id: the runs can be saved in a different row order")

    def test_refuses_different_tickets(self):
        a = [{"ticket_id": "t1", "label": "bug"}, {"ticket_id": "t2", "label": "refund"}]
        b = [{"ticket_id": "t1", "label": "bug"}, {"ticket_id": "t3", "label": "refund"}]
        with self.assertRaises(ValueError, msg="run b is on ticket t3, not t2: this must be refused"):
            lesson.pair_runs(self.GOLD, a, b)
        with self.assertRaises(ValueError, msg="a run on fewer tickets must be refused too"):
            lesson.pair_runs(self.GOLD, a[:1], a)

    def test_refuses_repeated_ids(self):
        a = [{"ticket_id": "t1", "label": "bug"}, {"ticket_id": "t1", "label": "bug"}, {"ticket_id": "t2", "label": "x"}]
        b = [{"ticket_id": "t1", "label": "bug"}, {"ticket_id": "t2", "label": "refund"}]
        with self.assertRaises(ValueError, msg="a ticket that appears twice would be counted twice"):
            lesson.pair_runs(self.GOLD, a, b)

    def test_other_week_cannot_be_paired(self):
        with self.assertRaises(ValueError, msg="v2 on another week's tickets is not a paired comparison"):
            lesson.pair_runs(committed("tickets.csv"), committed("run_v1.csv"), committed("other_week_v2.csv"))

    def test_empty(self):
        self.assertEqual(lesson.pair_runs([], [], []), [])
        self.assertEqual(lesson.accuracy([], "a"), 0.0, "accuracy of no tickets should be 0.0, not a crash")
        self.assertEqual(lesson.compare([])["verdict"], "no clear difference")


class TestExactTest(unittest.TestCase):
    def test_against_independent_computation(self):
        for k, n in [(0, 0), (0, 1), (0, 5), (0, 6), (1, 6), (3, 6), (6, 6), (3, 18), (15, 18), (10, 32), (40, 90)]:
            self.assertAlmostEqual(lesson.exact_two_sided_p(k, n), ref_p(k, n), places=12,
                                   msg="p for %d of %d: sum comb(n, i) up to min(k, n - k), double, cap at 1" % (k, n))

    def test_edges(self):
        self.assertEqual(lesson.exact_two_sided_p(0, 0), 1.0, "no discordant tickets means no evidence: p = 1")
        self.assertEqual(lesson.exact_two_sided_p(3, 6), 1.0, "an even split must give p = 1.0, capped")
        self.assertAlmostEqual(lesson.exact_two_sided_p(0, 6), 2 / 64)
        self.assertAlmostEqual(lesson.exact_two_sided_p(6, 6), 2 / 64, msg="the test is two-sided: 6 of 6 and 0 of 6 match")

    def test_verdicts(self):
        self.assertEqual(lesson.compare(make_pairs((150, 1, 12, 37)))["verdict"], "v2 better")
        self.assertEqual(lesson.compare(make_pairs((150, 12, 1, 37)))["verdict"], "v1 better")
        self.assertEqual(lesson.compare(make_pairs((150, 4, 4, 42)))["verdict"], "no clear difference",
                         "a tie in the discordant tickets is no evidence either way")
        self.assertEqual(lesson.compare(make_pairs((0, 0, 5, 0)))["verdict"], "no clear difference",
                         "5 of 5 gives p = 0.0625, which is not below 0.05")
        self.assertEqual(lesson.compare(make_pairs((0, 0, 6, 0)))["verdict"], "v2 better")

    def test_agreements_do_not_change_the_p_value(self):
        few = lesson.compare(make_pairs((10, 2, 11, 5)))
        many = lesson.compare(make_pairs((900, 2, 11, 500)))
        self.assertAlmostEqual(few["p_value"], many["p_value"],
                               msg="tickets where both versions agree carry no evidence about which is better")


class TestOnData(unittest.TestCase):
    def check(self, gold, run_a, run_b, label):
        got = lesson.compare(lesson.pair_runs(gold, run_a, run_b))
        exp = ref_compare(gold, run_a, run_b)
        for key in ("a_only", "b_only", "verdict"):
            self.assertEqual(got[key], exp[key], "%s: %s differs from an independent count" % (label, key))
        for key in ("acc_a", "acc_b", "p_value"):
            self.assertAlmostEqual(got[key], exp[key], places=12, msg="%s: %s differs" % (label, key))
        return got

    def test_committed(self):
        got = self.check(committed("tickets.csv"), committed("run_v1.csv"), committed("run_v2.csv"), "committed data")
        self.assertEqual(got["n"], 200)
        self.assertEqual(got["verdict"], "v2 better")

    def test_second_dataset(self):
        d = make_data.build(seed=OTHER_SEED)
        self.check(d["tickets"], d["run_v1"], d["run_v2"], "seed %d" % OTHER_SEED)

    def test_runs_saved_in_another_order(self):
        d = make_data.build(seed=OTHER_SEED)
        flipped = list(reversed(d["run_v2"]))
        a = lesson.compare(lesson.pair_runs(d["tickets"], d["run_v1"], d["run_v2"]))
        b = lesson.compare(lesson.pair_runs(d["tickets"], d["run_v1"], flipped))
        self.assertEqual(a, b, "the result must not depend on the row order of a saved run")

    def test_fixture_is_labelled(self):
        with open(os.path.join(HERE, "data", "fixture.json")) as f:
            info = json.load(f)
        self.assertEqual(info["label_source"], "simulated")
        self.assertTrue(info["model"].startswith("none"))
        texts = {}
        for r, v1, v2 in zip(committed("tickets.csv"), committed("run_v1.csv"), committed("run_v2.csv")):
            pair = (v1["label"], v2["label"])
            self.assertEqual(texts.setdefault(r["text"], pair), pair, "the same text got two labels: %r" % r["text"])


if __name__ == "__main__":
    unittest.main()
