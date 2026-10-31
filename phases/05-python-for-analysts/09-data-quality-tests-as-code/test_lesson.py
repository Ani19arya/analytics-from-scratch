"""Tests for lesson 09: data quality tests as code.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Every check is tested on small hand-made rows: blank and missing cells, the value "0", ties,
a non-number, both ends of a range and both ends of the tolerance band. The replay of two weeks
of loads is compared with a reference written here in plain Python, on the committed files and
on a second dataset from make_data.build(seed=2039) whose broken night is a different date.
"""
import csv
import importlib.util
import os
import statistics
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" \
    else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
OTHER_SEED = 2039
NAMES = ["order_id not null", "order_id unique", "currency not null", "status accepted values",
         "amount between 0 and 5000", "customer_id in customers", "row count near recent median",
         "revenue near recent median"]


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def is_blank(v):
    return v is None or str(v).strip() == ""


def ref_replay(rows, customers):
    """{load_date: {check name: status}} computed by hand, without the lesson's functions."""
    ids = {c["customer_id"] for c in customers}
    days = sorted({r["load_date"] for r in rows})
    hist_rows, hist_rev, out = [], [], {}
    for day in days:
        load_rows = [r for r in rows if r["load_date"] == day]
        ids_seen = [r["order_id"] for r in load_rows if not is_blank(r["order_id"])]
        amounts = []
        for r in load_rows:
            try:
                amounts.append(float(r["amount"]))
            except ValueError:
                pass
        rev = round(sum(amounts), 2)
        bad_amount = any(not (0 <= float(r["amount"]) <= 5000) for r in load_rows if not is_blank(r["amount"]))

        def near(value, history):
            recent = history[-7:]
            if len(recent) < 3:
                return True
            m = statistics.median(recent)
            return round(m * 0.5, 2) <= value <= round(m * 1.5, 2)

        broke = {
            "order_id not null": any(is_blank(r["order_id"]) for r in load_rows),
            "order_id unique": len(ids_seen) != len(set(ids_seen)),
            "currency not null": any(is_blank(r["currency"]) for r in load_rows),
            "status accepted values": any(r["status"] not in ("paid", "refunded", "cancelled")
                                          for r in load_rows if not is_blank(r["status"])),
            "amount between 0 and 5000": bad_amount,
            "customer_id in customers": any(r["customer_id"] not in ids for r in load_rows
                                            if not is_blank(r["customer_id"])),
            "row count near recent median": not near(len(load_rows), hist_rows),
            "revenue near recent median": not near(rev, hist_rev),
        }
        status = {}
        for name in NAMES:
            if not broke[name]:
                status[name] = "pass"
            else:
                status[name] = "warn" if name == "customer_id in customers" else "fail"
        out[day] = status
        if "fail" not in status.values():
            hist_rows.append(len(load_rows))
            hist_rev.append(rev)
    return out


def order(i, load_date="2026-10-01", **kw):
    row = {"load_date": load_date, "order_id": "KO-%05d" % i, "order_date": "2026-09-30",
           "customer_id": "C0001", "status": "paid", "currency": "USD", "amount": "10.00"}
    row.update(kw)
    return row


class TestChecks(unittest.TestCase):
    def test_not_null(self):
        rows = [{"a": ""}, {"a": " "}, {"a": None}, {"a": "0"}, {}, {"a": "x"}]
        self.assertEqual(list(lesson.check_not_null(rows, "a")), [0, 1, 2, 4],
                         "blank, spaces, None and a missing column are null; the text 0 is a value")
        self.assertEqual(list(lesson.check_not_null([], "a")), [])

    def test_unique(self):
        rows = [{"k": v} for v in ["x", "y", "x", "", "", "y", "z", "x"]]
        self.assertEqual(list(lesson.check_unique(rows, "k")), ["x", "y"],
                         "each repeated value once, sorted; repeated blanks are not_null's job, not unique's")
        self.assertEqual(list(lesson.check_unique([], "k")), [])

    def test_accepted_values(self):
        rows = [{"s": v} for v in ["paid", "PAID", "", "refunded", "paid "]]
        self.assertEqual(list(lesson.check_accepted_values(rows, "s", {"paid", "refunded"})), [1, 4],
                         "PAID and 'paid ' are not paid: the check must not quietly clean values")

    def test_range(self):
        rows = [{"n": v} for v in ["0", "5000", "5000.01", "-1", "", "abc", "12.5"]]
        self.assertEqual(list(lesson.check_range(rows, "n", 0, 5000)), [2, 3, 5],
                         "both ends are allowed, a blank is skipped, a non-number fails")

    def test_relationships(self):
        rows = [{"c": "C1"}, {"c": "C9"}, {"c": ""}, {"c": None}, {"c": "C1"}]
        self.assertEqual(list(lesson.check_relationships(rows, "c", ["C1", "C2"])), [1])

    def test_vs_history(self):
        h = [10, 10, 10]
        self.assertEqual(list(lesson.check_vs_history(15, h, 0.5)), [], "the top of the band is allowed")
        self.assertEqual(list(lesson.check_vs_history(5, h, 0.5)), [], "the bottom of the band is allowed")
        self.assertEqual(list(lesson.check_vs_history(15.01, h, 0.5)), [(15.01, 5.0, 15.0)])
        self.assertEqual(list(lesson.check_vs_history(4.99, h, 0.5)), [(4.99, 5.0, 15.0)])
        self.assertEqual(list(lesson.check_vs_history(999, [10, 10], 0.5)), [],
                         "with fewer than 3 earlier loads there is nothing to compare with yet")
        self.assertEqual(list(lesson.check_vs_history(10, [1000] + [10] * 7, 0.5)), [],
                         "only the last 7 values count, and the median ignores one odd value")
        self.assertEqual(list(lesson.check_vs_history(0, [0, 0, 0], 0.5)), [])
        self.assertEqual(len(lesson.check_vs_history(1, [0, 0, 0], 0.5)), 1, "anything above a zero median is a change")


class TestSuiteAndGate(unittest.TestCase):
    SUITE = [("always ok", "error", lambda rows: []),
             ("soft", "warn", lambda rows: [7, 8, 9, 10]),
             ("hard", "error", lambda rows: ["a"])]

    def test_run_suite(self):
        got = lesson.run_suite([{"x": 1}], self.SUITE)
        self.assertEqual([r["name"] for r in got], ["always ok", "soft", "hard"], "one result per check, in order")
        self.assertEqual([r["status"] for r in got], ["pass", "warn", "fail"],
                         "a failing warn check is a warn, a failing error check is a fail")
        self.assertEqual([r["failures"] for r in got], [0, 4, 1])
        self.assertEqual(list(got[1]["sample"]), [7, 8, 9], "sample is the first 3 failures")
        self.assertEqual(lesson.run_suite([], []), [])

    def test_gate(self):
        results = lesson.run_suite([], self.SUITE)
        with self.assertRaises(lesson.LoadRejected) as ctx:
            lesson.gate(results)
        self.assertIn("hard", str(ctx.exception), "the error should name the failed check")
        self.assertNotIn("soft", str(ctx.exception), "warnings are not a reason to reject")
        lesson.gate(lesson.run_suite([], self.SUITE[:2]))
        lesson.gate([])

    def test_rejected_loads_never_become_the_baseline(self):
        customers = [{"customer_id": "C0001"}]
        rows, n = [], 0
        for day, size in [("2026-10-01", 10), ("2026-10-02", 10), ("2026-10-03", 10)] + \
                         [("2026-10-%02d" % d, 40) for d in range(4, 9)]:
            for _ in range(size):
                n += 1
                rows.append(order(n, load_date=day))
        got = lesson.replay(rows, customers)
        rejected = [d for d, res in got.items() if any(r["status"] == "fail" for r in res)]
        self.assertEqual(rejected, ["2026-10-0%d" % d for d in range(4, 9)],
                         "a source that stays broken must stay rejected: only loads that passed go into the history")


class DataChecks:
    rows = customers = broken = None

    def test_replay_matches_reference(self):
        want = ref_replay(self.rows, self.customers)
        got = lesson.replay(self.rows, self.customers)
        self.assertEqual(sorted(got), sorted(want), "one entry per load_date")
        for day in want:
            statuses = {r["name"]: r["status"] for r in got[day]}
            self.assertEqual(statuses, want[day], "check results for the load of %s" % day)

    def test_only_the_broken_night_is_rejected(self):
        got = lesson.replay(self.rows, self.customers)
        rejected = [d for d, res in got.items() if any(r["status"] == "fail" for r in res)]
        self.assertEqual(rejected, [self.broken], "the suite should reject the broken load and nothing else")

    def test_failure_counts_on_the_broken_night(self):
        load_rows = [r for r in self.rows if r["load_date"] == self.broken]
        res = {r["name"]: r for r in lesson.replay(self.rows, self.customers)[self.broken]}
        ids = [r["order_id"] for r in load_rows]
        self.assertEqual(res["order_id unique"]["failures"], len(set(i for i in ids if ids.count(i) > 1)))
        self.assertEqual(res["currency not null"]["failures"], sum(1 for r in load_rows if is_blank(r["currency"])))
        self.assertEqual(res["amount between 0 and 5000"]["failures"],
                         sum(1 for r in load_rows if not 0 <= float(r["amount"]) <= 5000))


class TestCommittedFiles(DataChecks, unittest.TestCase):
    rows, customers = read("orders.csv"), read("customers.csv")
    broken = make_data.build()["broken_load_date"]


class TestSecondFiles(DataChecks, unittest.TestCase):
    _data = make_data.build(OTHER_SEED)
    rows, customers, broken = _data["orders"], _data["customers"], _data["broken_load_date"]


if __name__ == "__main__":
    unittest.main()
