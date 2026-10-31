"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are worked out here a second way: red flags come from the generator's own
labels (not from a regex), fit and freshness are recomputed with plain arithmetic, and the
best plan is checked by trying every subset on small cases and by a separate dictionary-based
search on the full data. Everything runs on the committed postings and on a second set built
in memory from another seed. One check uses the real entry-level search result from
data/real_snapshot_2026-10-31.json.
"""
import csv
import datetime
import importlib.util
import itertools
import json
import os
import random
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

OTHER_SEED = 4242
PROFILE = {"as_of": "2026-10-31", "skills": ["SQL", "Excel", "Tableau", "Python", "statistics"],
           "weekly_hours": 10, "entry_salary_ceiling_usd": 110000}


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def posting(**kw):
    base = {"posting_id": "X", "company": "Testco", "title": "Data Analyst", "seniority_label": "Mid Level",
            "source": "careers_page", "first_seen": "2026-10-31", "salary_min_usd": "", "salary_max_usd": "",
            "must_have": "SQL", "nice_to_have": "", "notes": "", "est_hours": "1.0"}
    base.update(kw)
    return base


def ref_value(p, profile, planted):
    """Value from first principles, with the generator's planted flag as the truth."""
    have = [s.lower() for s in profile["skills"]]
    must = [s.strip().lower() for s in p["must_have"].split(";") if s.strip()]
    nice = [s.strip().lower() for s in p["nice_to_have"].split(";") if s.strip()]
    missing = [s for s in must if s not in have]
    if planted in ("fee_to_apply", "unpaid_work", "seniority_mismatch") or len(missing) > 1:
        return 0.0
    must_share = 1.0 if not must else (len(must) - len(missing)) / len(must)
    nice_share = 1.0 if not nice else sum(1 for s in nice if s in have) / len(nice)
    if p["first_seen"]:
        age = (datetime.date(2026, 10, 31) - datetime.date(*map(int, p["first_seen"].split("-")))).days
        fresh = min(1.0, max(0.0, (30 - age) / 30))
    else:
        fresh = 0.0
    v = 100 * (0.75 * must_share + 0.25 * nice_share) * (0.5 + 0.5 * fresh)
    return v / 2 if planted == "repost" else v


def brute_best(items, budget):
    best = 0.0
    for r in range(len(items) + 1):
        for combo in itertools.combinations(items, r):
            if sum(h for _, _, h in combo) <= budget + 1e-9:
                best = max(best, sum(max(v, 0) for _, v, _ in combo if v > 0))
    return best


def dict_best(items, budget):
    """Best value per total hours, built item by item in a dictionary."""
    reach = {0.0: 0.0}
    for _, v, h in items:
        if v <= 0:
            continue
        for hours, val in list(reach.items()):
            nh = hours + h
            if nh <= budget + 1e-9 and reach.get(nh, -1) < val + v:
                reach[nh] = val + v
    return max(reach.values())


class TestScoring(unittest.TestCase):
    def test_freshness(self):
        self.assertAlmostEqual(lesson.freshness("2026-10-31", "2026-10-31"), 1.0)
        self.assertAlmostEqual(lesson.freshness("2026-10-16", "2026-10-31"), 0.5, msg="15 of 30 days old is halfway")
        self.assertAlmostEqual(lesson.freshness("2026-10-01", "2026-10-31"), 0.0, msg="30 days old is stale")
        self.assertAlmostEqual(lesson.freshness("2026-08-01", "2026-10-31"), 0.0, msg="never below 0")
        self.assertAlmostEqual(lesson.freshness("", "2026-10-31"), 0.0, msg="a blank date is unknown, so treat it as stale")
        self.assertAlmostEqual(lesson.freshness("2026-11-02", "2026-10-31"), 1.0, msg="a future date counts as today")

    def test_fit(self):
        score, missing = lesson.fit(posting(must_have="sql; Excel ;R", nice_to_have="python;dbt"), PROFILE["skills"])
        self.assertAlmostEqual(score, 0.75 * 2 / 3 + 0.25 * 1 / 2, msg="compare skills without case and strip spaces")
        self.assertEqual(missing, ["r"])
        score, missing = lesson.fit(posting(must_have="", nice_to_have=""), PROFILE["skills"])
        self.assertAlmostEqual(score, 1.0, msg="an empty list counts as a share of 1, not a division by zero")
        self.assertEqual(missing, [])
        self.assertEqual(lesson.fit(posting(must_have="R;dbt;Looker"), [])[1], ["dbt", "looker", "r"],
                         "missing must-haves come back sorted and in lower case")

    def test_red_flags_by_hand(self):
        rf = lambda **kw: lesson.red_flags(posting(**kw), PROFILE)
        self.assertEqual(rf(notes="A 30 USD processing fee is due with your application."), ["fee_to_apply"])
        self.assertEqual(rf(notes="We never charge an application fee."), [], "a sentence that says never is not a fee")
        self.assertEqual(rf(notes="Hybrid. There is no application fee."), [])
        self.assertEqual(rf(notes="Final stage is an unpaid trial week."), ["unpaid_work"])
        self.assertEqual(rf(notes="Short take-home task, paid at our contractor rate."), [], "paid work is not a flag")
        self.assertEqual(rf(seniority_label="Entry Level", title="Senior Data Analyst"), ["seniority_mismatch"])
        self.assertEqual(rf(seniority_label="Entry Level", title="Data Analyst", salary_min_usd="110000"),
                         ["seniority_mismatch"], "a salary at the ceiling is too high for an entry label")
        self.assertEqual(rf(seniority_label="Entry Level", title="Data Analyst", salary_min_usd="109999"), [])
        self.assertEqual(rf(seniority_label="Mid Level", title="Senior Data Analyst"), [],
                         "a senior title is only a mismatch when the label says Entry Level")
        self.assertEqual(rf(seniority_label="Entry Level", title="Management Trainee"), [],
                         "match whole words: Management is not manager")
        self.assertEqual(rf(source="repost", notes="Unpaid pilot project first."), ["repost", "unpaid_work"])

    def test_real_entry_level_result(self):
        with open(os.path.join(HERE, "data", "real_snapshot_2026-10-31.json")) as f:
            real = json.load(f)["entry_level_search"]["first_result"]
        p = posting(title=real["title"], seniority_label="Entry Level", salary_min_usd=str(real["salary_min_usd"]))
        self.assertIn("seniority_mismatch", lesson.red_flags(p, PROFILE),
                      "the real entry-level result titled %r should be flagged" % real["title"])
        self.assertIn("seniority_mismatch", lesson.red_flags(dict(p, title="Advanced Analytics"), PROFILE),
                      "its salary alone is above the entry ceiling")

    def test_value_rules(self):
        self.assertEqual(lesson.value(posting(must_have="R;dbt"), PROFILE), 0.0, "two missing must-haves: do not apply")
        self.assertAlmostEqual(lesson.value(posting(must_have="R;SQL"), PROFILE), 100 * 0.75 * 0.5 + 25,
                               msg="one missing must-have is allowed")
        self.assertEqual(lesson.value(posting(notes="Pay to apply."), PROFILE), 0.0, msg="a hard flag means 0")
        self.assertAlmostEqual(lesson.value(posting(source="repost"), PROFILE), 50.0, msg="a repost is worth half")
        self.assertAlmostEqual(lesson.value(posting(first_seen=""), PROFILE), 50.0, msg="unknown age gets the stale half")


class TestChoose(unittest.TestCase):
    def check(self, items, budget, label):
        ids, total, hours = lesson.choose(items, budget)
        by_id = {i: (v, h) for i, v, h in items}
        self.assertEqual(ids, sorted(ids), "%s: return the chosen ids sorted" % label)
        self.assertEqual(len(set(ids)), len(ids), "%s: each posting at most once" % label)
        self.assertTrue(all(by_id[i][0] > 0 for i in ids), "%s: never choose a posting worth 0" % label)
        self.assertLessEqual(sum(by_id[i][1] for i in ids), budget + 1e-9, "%s: over the time budget" % label)
        self.assertAlmostEqual(total, sum(by_id[i][0] for i in ids), msg="%s: total must match the chosen ids" % label)
        self.assertAlmostEqual(hours, sum(by_id[i][1] for i in ids), msg="%s: hours must match the chosen ids" % label)
        return total

    def test_edges(self):
        self.assertEqual(lesson.choose([], 10), ([], 0, 0), "nothing to choose from")
        self.assertEqual(lesson.choose([("a", 50.0, 3.0)], 0)[0], [], "a budget of 0 fits nothing")
        self.assertEqual(lesson.choose([("a", 0.0, 0.5), ("b", -1.0, 0.5)], 10)[0], [], "zero-value postings are skipped")
        self.assertEqual(lesson.choose([("a", 90.0, 12.0)], 10)[0], [], "a posting longer than the budget never fits")

    def test_greedy_trap(self):
        items = [("a", 60.0, 5.0), ("b", 60.0, 5.0), ("c", 70.0, 5.5)]
        self.assertEqual(lesson.choose(items, 10)[0], ["a", "b"],
                         "c has the best value per hour, but a and b together are worth more in 10 hours")

    def test_brute_force_small_cases(self):
        rng = random.Random(7)
        for case in range(60):
            n = rng.randint(1, 10)
            items = [("i%d" % k, rng.choice([0.0, rng.uniform(5, 100)]), rng.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0]))
                     for k in range(n)]
            budget = rng.choice([0, 1.5, 3, 5, 7.5, 10])
            total = self.check(items, budget, "random case %d" % case)
            self.assertAlmostEqual(total, brute_best(items, budget),
                                   msg="random case %d: a better set exists (tried every subset)" % case)


class TestOnData(unittest.TestCase):
    def check_dataset(self, d, label):
        planted = {r["posting_id"]: r["planted_flag"] for r in d["labels"]}
        profile = d["profile"]
        for p in d["postings"]:
            flags = lesson.red_flags(p, profile)
            want = planted[p["posting_id"]]
            self.assertEqual(flags, [want] if want else [],
                             "%s: %s %r should have flags %r" % (label, p["posting_id"], p["title"], [want] if want else []))
            self.assertAlmostEqual(lesson.value(p, profile), ref_value(p, profile, want),
                                   msg="%s: value of %s" % (label, p["posting_id"]))
        items = [(p["posting_id"], ref_value(p, profile, planted[p["posting_id"]]), float(p["est_hours"])) for p in d["postings"]]
        ids, total, hours = lesson.plan(d["postings"], profile)
        self.assertLessEqual(hours, profile["weekly_hours"], "%s: the plan is over budget" % label)
        self.assertAlmostEqual(total, dict_best(items, profile["weekly_hours"]),
                               msg="%s: the plan is not the best set inside the budget" % label)
        self.assertFalse(any(planted[i] in ("fee_to_apply", "unpaid_work", "seniority_mismatch") for i in ids),
                         "%s: the plan includes a posting with a hard red flag" % label)
        return ids

    def test_committed_data(self):
        with open(os.path.join(HERE, "data", "profile.json")) as f:
            profile = json.load(f)
        d = {"postings": read(os.path.join(HERE, "data", "postings.csv")),
             "labels": read(os.path.join(HERE, "data", "labels.csv")), "profile": profile}
        self.check_dataset(d, "committed postings")

    def test_second_dataset(self):
        self.check_dataset(make_data.build(seed=OTHER_SEED), "seed %d" % OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
