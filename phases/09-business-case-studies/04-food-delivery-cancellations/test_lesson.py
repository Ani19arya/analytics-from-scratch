"""Tests for case 04: food delivery cancellations. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (no cancellations at all, a tie, a city with no before orders, a zero).
"""
import csv
import datetime
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "orders.csv")
OTHER_SEED = 7
START = datetime.date(2026, 8, 3)
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def read_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def week_of(row):
    return (datetime.date.fromisoformat(row["order_date"]) - START).days // 7 + 1


def period_of(row):
    return "before" if week_of(row) <= 6 else "after"


def run_sql(con, sql):
    body = "\n".join(ln for ln in (sql or "").splitlines() if not ln.strip().startswith("--"))
    if not body.strip():
        raise AssertionError("the query is still a TODO: write it in the exercise file")
    return m.query(con, sql)


def tiny_db(rows):
    """rows: (order_date, city, app_version, cancel_reason or None)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE orders (order_id TEXT, order_date TEXT, city TEXT, restaurant_id TEXT,"
                " app_version TEXT, status TEXT, cancel_reason TEXT)")
    for i, (d, city, ver, reason) in enumerate(rows):
        con.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("X%d" % i, d, city, "R01", ver, "cancelled" if reason else "delivered", reason))
    return con


class TestHandMade(unittest.TestCase):
    def test_no_cancellations(self):
        con = tiny_db([("2026-08-03", "Pune", "7.3.2", None), ("2026-09-20", "Pune", "7.3.2", None)])
        weekly = run_sql(con, m.WEEKLY_SQL)
        self.assertEqual([(w["week"], w["orders"], w["cancelled"], w["cancel_rate_pct"]) for w in weekly],
                         [(1, 1, 0, 0.0), (7, 1, 0, 0.0)],
                         "a week with orders but no cancellations must show cancelled 0 and rate 0.0, not NULL")
        self.assertEqual(run_sql(con, m.REASON_SQL), [], "delivered orders have a NULL reason and must not appear as a reason row")

    def test_reason_denominator_is_all_orders(self):
        con = tiny_db([("2026-08-04", "Pune", "7.3.2", "rider")] + [("2026-08-05", "Pune", "7.3.2", None)] * 3)
        r = run_sql(con, m.REASON_SQL)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["per_100_orders"], 25.0,
                         "per_100_orders divides by all orders in the period (4), not by cancellations (1)")

    def test_week_boundary(self):
        # Sunday 13 Sep is still week 6 (before); Monday 14 Sep is week 7 (after).
        con = tiny_db([("2026-09-13", "Pune", "7.3.2", None), ("2026-09-14", "Pune", "7.3.2", "customer")])
        weeks = [w["week"] for w in run_sql(con, m.WEEKLY_SQL)]
        self.assertEqual(weeks, [6, 7], "weeks start on Monday 3 August 2026: 13 Sep is week 6, 14 Sep is week 7")
        periods = sorted((s["period"], s["cancelled"]) for s in run_sql(con, m.SEGMENT_SQL))
        self.assertEqual(periods, [("after", 1), ("before", 0)])

    def test_excess_simple_and_tie(self):
        seg = [
            {"city": "A", "app_version": "1", "period": "before", "orders": 100, "cancelled": 5},
            {"city": "A", "app_version": "1", "period": "after", "orders": 100, "cancelled": 10},
            {"city": "B", "app_version": "1", "period": "before", "orders": 100, "cancelled": 10},
            {"city": "B", "app_version": "1", "period": "after", "orders": 50, "cancelled": 10},
        ]
        ex = m.excess_by_segment(seg)
        self.assertEqual([(r["city"], round(r["excess"], 6)) for r in ex], [("A", 5.0), ("B", 5.0)],
                         "excess = cancelled - after orders x the city's before rate; a tie is ordered by city")
        self.assertAlmostEqual(m.top_segment_share(ex), 0.5)

    def test_new_version_uses_city_rate_and_new_city_uses_overall(self):
        seg = [
            {"city": "A", "app_version": "1", "period": "before", "orders": 200, "cancelled": 10},
            {"city": "A", "app_version": "2", "period": "after", "orders": 100, "cancelled": 30},
            {"city": "C", "app_version": "1", "period": "after", "orders": 100, "cancelled": 5},
        ]
        ex = {(r["city"], r["app_version"]): r for r in m.excess_by_segment(seg)}
        self.assertAlmostEqual(ex[("A", "2")]["expected"], 5.0,
                               msg="a version that did not exist before is compared with its city's before rate (5%)")
        self.assertAlmostEqual(ex[("C", "1")]["expected"], 5.0,
                               msg="a city with no before orders uses the overall before rate")

    def test_share_none_and_empty(self):
        self.assertIsNone(m.top_segment_share([]), "no rows: return None")
        self.assertIsNone(m.top_segment_share([{"excess": -2.0}, {"excess": 1.0}]),
                          "when cancellations did not rise (total excess <= 0) there is nothing to explain: None")

    def test_rate_without(self):
        seg = [{"city": "A", "app_version": "1", "period": "after", "orders": 10, "cancelled": 5},
               {"city": "B", "app_version": "1", "period": "after", "orders": 90, "cancelled": 9},
               {"city": "B", "app_version": "1", "period": "before", "orders": 90, "cancelled": 90}]
        self.assertAlmostEqual(m.rate_without(seg, "A", "1"), 10.0, msg="only after-period rows count")
        self.assertIsNone(m.rate_without(seg[:1], "A", "1"), "no orders left: None")

    def test_text_chart(self):
        self.assertEqual(m.text_chart([]), [])
        lines = m.text_chart([{"week": 1, "cancel_rate_pct": 5.0}, {"week": 2, "cancel_rate_pct": 10.0},
                              {"week": 3, "cancel_rate_pct": 0.0}], width=10)
        self.assertEqual([ln.count("#") for ln in lines], [5, 10, 0], "bars scale so the highest rate gets `width` characters")
        self.assertTrue(lines[0].startswith("W01"), "each line starts with the week label, W01")
        flat = m.text_chart([{"week": 1, "cancel_rate_pct": 0.0}], width=10)
        self.assertEqual(flat[0].count("#"), 0, "all rates 0: no bars and no division by zero")


class OnDataMixin:
    path = DATA

    @classmethod
    def setUpClass(cls):
        cls.rows = read_rows(cls.path)
        cls.con = m.load_db(cls.path)

    def test_weekly(self):
        exp = {}
        for r in self.rows:
            e = exp.setdefault(week_of(r), [0, 0])
            e[0] += 1
            e[1] += r["status"] == "cancelled"
        got = run_sql(self.con, m.WEEKLY_SQL)
        self.assertEqual([w["week"] for w in got], sorted(exp), "one row per week, 1 to 12, in order")
        for w in got:
            o, c = exp[w["week"]]
            self.assertEqual((w["orders"], w["cancelled"]), (o, c), "week %d: expected %d orders, %d cancelled" % (w["week"], o, c))
            self.assertAlmostEqual(w["cancel_rate_pct"], round(100.0 * c / o, 1), places=6)

    def test_reasons(self):
        orders = {"before": 0, "after": 0}
        cancels = {}
        for r in self.rows:
            orders[period_of(r)] += 1
            if r["cancel_reason"]:
                k = (period_of(r), r["cancel_reason"])
                cancels[k] = cancels.get(k, 0) + 1
        got = run_sql(self.con, m.REASON_SQL)
        self.assertEqual([(g["period"], g["cancel_reason"]) for g in got], sorted(cancels),
                         "one row per period and reason, ordered by period then reason")
        for g in got:
            n = cancels[(g["period"], g["cancel_reason"])]
            self.assertEqual(g["cancelled"], n)
            self.assertAlmostEqual(g["per_100_orders"], round(100.0 * n / orders[g["period"]], 2), places=6,
                                   msg="per_100_orders for %s %s" % (g["period"], g["cancel_reason"]))

    def expected_segments(self):
        seg = {}
        for r in self.rows:
            s = seg.setdefault((r["city"], r["app_version"], period_of(r)), [0, 0])
            s[0] += 1
            s[1] += r["status"] == "cancelled"
        return seg

    def test_segments(self):
        seg = self.expected_segments()
        got = run_sql(self.con, m.SEGMENT_SQL)
        self.assertEqual([(g["city"], g["app_version"], g["period"]) for g in got], sorted(seg),
                         "one row per city, app_version and period, in that order")
        for g in got:
            self.assertEqual([g["orders"], g["cancelled"]], seg[(g["city"], g["app_version"], g["period"])])

    def test_insight(self):
        seg = self.expected_segments()
        before = {}
        for (city, _, period), (o, c) in seg.items():
            if period == "before":
                b = before.setdefault(city, [0, 0])
                b[0] += o
                b[1] += c
        excess = {(city, ver): c - o * before[city][1] / before[city][0]
                  for (city, ver, period), (o, c) in seg.items() if period == "after"}
        top = max(excess, key=excess.get)
        self.assertEqual(top, ("Nagpur", "7.4.0"), "the planted cause is Nagpur on app 7.4.0")
        ex = m.excess_by_segment(run_sql(self.con, m.SEGMENT_SQL))
        self.assertEqual((ex[0]["city"], ex[0]["app_version"]), top)
        self.assertAlmostEqual(ex[0]["excess"], excess[top], places=6)
        self.assertAlmostEqual(m.top_segment_share(ex), excess[top] / sum(excess.values()), places=6)
        o = sum(v[0] for k, v in seg.items() if k[2] == "after" and k[:2] != top)
        c = sum(v[1] for k, v in seg.items() if k[2] == "after" and k[:2] != top)
        self.assertAlmostEqual(m.rate_without(run_sql(self.con, m.SEGMENT_SQL), *top), 100.0 * c / o, places=6)


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "orders.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["orders"], cls.path)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
