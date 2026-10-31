"""Checker for capstone 10-01: the Pottlemere quarterly business review.
Run: python3 test_lesson.py           (checks exercise.py, your submission)
     CHECK_SOLUTION=1 python3 test_lesson.py   (checks solution/solution.py)

It checks the numbers that have one right answer. Every expected value is
computed here in plain Python from the raw rows, never read from the solution.
The checks run on the committed data, on a second dataset built in memory with
another seed (so typed-in answers fail), and on tiny hand-made tables. The
interval is also checked against a seeded bootstrap, an independent route to
the same standard error. Judgement (the recommendation, the write-up) is
scored with RUBRIC.md, not here.
"""
import csv
import importlib.util
import math
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 7
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("submission", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def read_rows(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def qtr(d):
    return "%s-Q%d" % (d[:4], (int(d[5:7]) - 1) // 3 + 1)


def o_row(oid, cid, date, amount, status="completed", platform="v2", loaded="2026-01-01"):
    return {"order_id": oid, "customer_id": cid, "order_date": date, "status": status, "platform": platform,
            "amount": amount, "loaded_at": loaded}


def r_row(rid, oid, date, amount, loaded):
    return {"refund_id": rid, "order_id": oid, "refund_date": date, "refund_amount": amount, "loaded_at": loaded}


# ---- an independent reference, written differently from the solution -----

def ref_orders(raw, as_of=None):
    rows = sorted((r for r in raw if as_of is None or r["loaded_at"] <= as_of),
                  key=lambda r: (r["order_id"], r["loaded_at"]))
    last = {}
    for r in rows:
        last[r["order_id"]] = r  # sorted by load date, so the last one seen is the latest
    out = {}
    for oid, r in last.items():
        if r["status"] == "completed":
            amt = float(r["amount"])
            out[oid] = (r["customer_id"], r["order_date"], amt * 100 / 112 if r["platform"] == "legacy" else amt)
    return out


def ref_refunds(raw, as_of=None):
    out = {}
    for r in raw:
        if as_of is None or r["loaded_at"] <= as_of:
            if r["refund_id"] not in out or r["loaded_at"] >= out[r["refund_id"]][2]:
                out[r["refund_id"]] = (r["refund_date"], float(r["refund_amount"]), r["loaded_at"])
    return out


def ref_summary(orders, refunds, q):
    first = {}
    for cid, d, _ in orders.values():
        first[cid] = min(first.get(cid, "9999"), d)
    in_q = [v for v in orders.values() if qtr(v[1]) == q]
    buyers = {v[0] for v in in_q}
    new = sum(1 for c in buyers if qtr(first[c]) == q)
    sales = sum(v[2] for v in in_q)
    ref = sum(v[1] for v in refunds.values() if qtr(v[0]) == q)
    return {"orders": len(in_q), "customers": len(buyers), "new_customers": new,
            "returning_customers": len(buyers) - new, "net_sales": sales, "refunds": ref,
            "net_revenue": sales - ref}


class TestHandMade(unittest.TestCase):
    def test_clean_orders_latest_load_wins(self):
        raw = [o_row("A", "c1", "2026-06-30", "1120.00", platform="legacy", loaded="2026-07-01"),
               o_row("A", "c1", "2026-06-30", "1120.00", platform="legacy", loaded="2026-07-01"),
               o_row("B", "c2", "2026-06-29", "500.00", platform="legacy", loaded="2026-06-30"),
               o_row("B", "c2", "2026-06-29", "500.00", status="cancelled", platform="legacy", loaded="2026-07-09"),
               o_row("C", "c3", "2026-08-02", "700.00", platform="v2", loaded="2026-08-03")]
        got = {o["order_id"]: o for o in m.clean_orders(raw)}
        self.assertEqual(sorted(got), ["A", "C"], "a double-loaded order counts once, and B's latest load says cancelled")
        self.assertAlmostEqual(got["A"]["net_amount"], 1000.0, places=6,
                               msg="legacy amounts include 12% tax: 1,120.00 is 1,000.00 excluding tax")
        self.assertAlmostEqual(got["C"]["net_amount"], 700.0, places=6, msg="v2 amounts already exclude tax")
        early = {o["order_id"] for o in m.clean_orders(raw, as_of="2026-07-03")}
        self.assertEqual(early, {"A", "B"}, "on 3 July B was still completed and C did not exist yet")
        self.assertEqual(m.clean_orders([]), [], "no rows: an empty list")

    def test_clean_refunds(self):
        raw = [r_row("R1", "A", "2026-07-05", "200.00", "2026-07-06"),
               r_row("R1", "A", "2026-07-05", "200.00", "2026-07-06"),
               r_row("R2", "B", "2026-06-20", "50.00", "2026-07-20")]
        got = m.clean_refunds(raw)
        self.assertEqual(sorted(r["refund_id"] for r in got), ["R1", "R2"], "a repeated refund_id counts once")
        self.assertEqual([r["refund_id"] for r in m.clean_refunds(raw, as_of="2026-07-10")], ["R1"],
                         "R2 was loaded on 20 July, after the as_of date")

    def test_quarter_summary_new_returning_and_refund_dates(self):
        orders = [{"order_id": "1", "customer_id": "x", "order_date": "2026-03-31", "net_amount": 100.0},
                  {"order_id": "2", "customer_id": "x", "order_date": "2026-04-01", "net_amount": 300.0},
                  {"order_id": "3", "customer_id": "y", "order_date": "2026-06-30", "net_amount": 200.0},
                  {"order_id": "4", "customer_id": "y", "order_date": "2026-06-30", "net_amount": 100.0}]
        refunds = [{"refund_id": "r", "order_id": "1", "refund_date": "2026-04-02", "refund_amount": 100.0},
                   {"refund_id": "s", "order_id": "3", "refund_date": "2026-07-01", "refund_amount": 50.0}]
        s = m.quarter_summary(orders, refunds, "2026-Q2")
        self.assertEqual((s["orders"], s["customers"], s["new_customers"], s["returning_customers"]), (3, 2, 1, 1),
                         "x first bought on 31 March (Q1), so x is returning in Q2; y is new")
        self.assertAlmostEqual(s["net_sales"], 600.0)
        self.assertAlmostEqual(s["refunds"], 100.0, msg="refunds count in the quarter of the refund date, not the order date")
        self.assertAlmostEqual(s["net_revenue"], 500.0)
        self.assertAlmostEqual(s["aov"], 200.0)
        empty = m.quarter_summary(orders, refunds, "2026-Q4")
        self.assertEqual((empty["orders"], empty["customers"], empty["aov"]), (0, 0, None),
                         "a quarter with no orders: zeros, and aov None (no division by zero)")

    def test_restate(self):
        raw_o = [o_row("A", "c1", "2026-06-10", "1000.00", loaded="2026-06-11"),
                 o_row("B", "c2", "2026-06-29", "400.00", loaded="2026-07-20"),
                 o_row("A", "c1", "2026-06-10", "1000.00", status="cancelled", loaded="2026-07-15")]
        raw_r = [r_row("R", "B", "2026-06-30", "100.00", "2026-07-21")]
        got = m.restate(raw_o, raw_r, "2026-Q2", "2026-07-03")
        self.assertAlmostEqual(got["reported"], 1000.0, msg="on 3 July only A was known, still completed")
        self.assertAlmostEqual(got["restated"], 300.0, msg="now A is cancelled and B (late) has a refund of 100")
        self.assertAlmostEqual(got["change"], -700.0, msg="change is restated minus reported")

    def test_new_customers_by_channel(self):
        orders = [{"order_id": "1", "customer_id": "a", "order_date": "2026-07-02", "net_amount": 1.0},
                  {"order_id": "2", "customer_id": "a", "order_date": "2026-07-09", "net_amount": 1.0},
                  {"order_id": "3", "customer_id": "b", "order_date": "2026-08-01", "net_amount": 1.0},
                  {"order_id": "4", "customer_id": "z", "order_date": "2026-09-30", "net_amount": 1.0},
                  {"order_id": "5", "customer_id": "old", "order_date": "2026-05-01", "net_amount": 1.0},
                  {"order_id": "6", "customer_id": "old", "order_date": "2026-07-01", "net_amount": 1.0}]
        customers = [{"customer_id": "a", "acquisition_channel": "social"},
                     {"customer_id": "a", "acquisition_channel": "social"},
                     {"customer_id": "b", "acquisition_channel": "search"},
                     {"customer_id": "old", "acquisition_channel": "search"}]
        self.assertEqual(m.new_customers_by_channel(orders, customers, "2026-Q3"),
                         {"search": 1, "social": 1, "unknown": 1},
                         "a repeated customer row must not count twice; z is missing so 'unknown'; 'old' is not new")
        self.assertEqual(m.new_customers_by_channel([], customers, "2026-Q3"), {})

    def test_mean_diff_ci(self):
        self.assertIsNone(m.mean_diff_ci([5.0], [1.0, 2.0]), "fewer than 2 values: no variance, so None")
        same = m.mean_diff_ci([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(same["diff"], 0.0)
        a, b = [10.0, 12.0, 14.0], [20.0, 20.0, 26.0, 30.0]
        se = math.sqrt(4.0 / 3 + 24.0 / 4)
        got = m.mean_diff_ci(a, b)
        self.assertAlmostEqual(got["diff"], 12.0, msg="diff is mean(b) - mean(a)")
        self.assertAlmostEqual(got["se"], se, places=9, msg="Welch SE: sqrt(var_a/n_a + var_b/n_b) with n-1 variances")
        self.assertAlmostEqual(got["low"], 12.0 - 1.96 * se, places=9)
        self.assertAlmostEqual(got["high"], 12.0 + 1.96 * se, places=9)

    def test_monthly_net_sales(self):
        orders = [{"order_id": "1", "customer_id": "a", "order_date": "2026-08-31", "net_amount": 5.0},
                  {"order_id": "2", "customer_id": "a", "order_date": "2026-07-01", "net_amount": 2.0},
                  {"order_id": "3", "customer_id": "b", "order_date": "2026-08-01", "net_amount": 1.5}]
        self.assertEqual(m.monthly_net_sales(orders), {"2026-07": 2.0, "2026-08": 6.5})
        self.assertEqual(list(m.monthly_net_sales(orders)), ["2026-07", "2026-08"], "months in order")
        self.assertEqual(m.monthly_net_sales([]), {})


class OnDataMixin:
    @classmethod
    def setUpClass(cls):
        cls.raw = cls.get_raw()
        cls.orders = m.clean_orders(cls.raw["orders"])
        cls.refunds = m.clean_refunds(cls.raw["refunds"])
        cls.exp_orders = ref_orders(cls.raw["orders"])
        cls.exp_refunds = ref_refunds(cls.raw["refunds"])

    def test_clean_counts(self):
        self.assertEqual(sorted(o["order_id"] for o in self.orders), sorted(self.exp_orders),
                         "clean orders: one per order_id, latest load, completed only")
        self.assertEqual(len(self.refunds), len(self.exp_refunds), "clean refunds: one per refund_id")
        total = sum(o["net_amount"] for o in self.orders)
        self.assertAlmostEqual(total, sum(v[2] for v in self.exp_orders.values()), delta=0.01,
                               msg="total net sales excluding tax: check the legacy tax conversion and do not round per row")

    def test_quarter_summaries(self):
        for q in ("2026-Q2", "2026-Q3"):
            exp = ref_summary(self.exp_orders, self.exp_refunds, q)
            got = m.quarter_summary(self.orders, self.refunds, q)
            for k in ("orders", "customers", "new_customers", "returning_customers"):
                self.assertEqual(got[k], exp[k], "%s %s" % (q, k))
            for k in ("net_sales", "refunds", "net_revenue"):
                self.assertAlmostEqual(got[k], exp[k], delta=0.01, msg="%s %s" % (q, k))
            self.assertAlmostEqual(got["aov"], exp["net_sales"] / exp["orders"], delta=0.001, msg=q + " aov")

    def test_restatement_of_q2(self):
        exp_rep = ref_summary(ref_orders(self.raw["orders"], "2026-07-03"),
                              ref_refunds(self.raw["refunds"], "2026-07-03"), "2026-Q2")["net_revenue"]
        exp_now = ref_summary(self.exp_orders, self.exp_refunds, "2026-Q2")["net_revenue"]
        got = m.restate(self.raw["orders"], self.raw["refunds"], "2026-Q2", "2026-07-03")
        self.assertAlmostEqual(got["reported"], exp_rep, delta=0.01, msg="Q2 net revenue as the 3 July report saw it")
        self.assertAlmostEqual(got["restated"], exp_now, delta=0.01, msg="Q2 net revenue with every row known today")
        self.assertNotAlmostEqual(got["change"], 0.0, places=0, msg="late rows and later cancellations move Q2")

    def test_new_customers_by_channel_and_story(self):
        channel = {c["customer_id"]: c["acquisition_channel"] for c in self.raw["customers"]}
        first = {}
        for cid, d, _ in self.exp_orders.values():
            first[cid] = min(first.get(cid, "9999"), d)
        for q in ("2026-Q2", "2026-Q3"):
            exp = {}
            for cid, d in first.items():
                if qtr(d) == q:
                    exp[channel.get(cid, "unknown")] = exp.get(channel.get(cid, "unknown"), 0) + 1
            got = m.new_customers_by_channel(self.orders, self.raw["customers"], q)
            self.assertEqual(got, exp, q + ": new customers per acquisition channel")
        q2 = m.new_customers_by_channel(self.orders, self.raw["customers"], "2026-Q2")
        q3 = m.new_customers_by_channel(self.orders, self.raw["customers"], "2026-Q3")
        self.assertLess(q3["social"], q2["social"] / 2, "the planted story: paid social was paused in Q3")

    def test_aov_interval_against_bootstrap(self):
        a = [v[2] for v in self.exp_orders.values() if qtr(v[1]) == "2026-Q2"]
        b = [v[2] for v in self.exp_orders.values() if qtr(v[1]) == "2026-Q3"]
        got = m.mean_diff_ci(sorted(a), sorted(b))
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        self.assertAlmostEqual(got["diff"], mb - ma, delta=1e-6)
        rng = random.Random(2026)
        diffs = []
        for _ in range(1500):
            ra = rng.choices(a, k=len(a))
            rb = rng.choices(b, k=len(b))
            diffs.append(sum(rb) / len(rb) - sum(ra) / len(ra))
        mean = sum(diffs) / len(diffs)
        boot_se = math.sqrt(sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1))
        self.assertLess(abs(got["se"] - boot_se) / boot_se, 0.1,
                        "the Welch SE should be within 10%% of a bootstrap SE (%.1f); got %.1f" % (boot_se, got["se"]))

    def test_definition_change_is_handled(self):
        months = m.monthly_net_sales(self.orders)
        naive = {}
        for r in ref_latest_completed(self.raw["orders"]):
            naive[r["order_date"][:7]] = naive.get(r["order_date"][:7], 0.0) + float(r["amount"])
        self.assertAlmostEqual(months["2026-07"] * 1.12, naive["2026-07"], delta=0.05,
                               msg="July is all legacy, so July excluding tax is the raw July amount / 1.12")
        self.assertAlmostEqual(months["2026-08"], naive["2026-08"], delta=0.01, msg="August is all v2: no conversion")


def ref_latest_completed(raw):
    last = {}
    for r in sorted(raw, key=lambda r: r["loaded_at"]):
        last[r["order_id"]] = r
    return [r for r in last.values() if r["status"] == "completed"]


class TestOnData(OnDataMixin, unittest.TestCase):
    @staticmethod
    def get_raw():
        return {"orders": read_rows("orders.csv"), "refunds": read_rows("refunds.csv"),
                "customers": read_rows("customers.csv")}


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @staticmethod
    def get_raw():
        return make_data.build(seed=OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
