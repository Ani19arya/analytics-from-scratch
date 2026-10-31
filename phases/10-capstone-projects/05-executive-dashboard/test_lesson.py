"""Checker for capstone 10-05: the Kettlemoor executive dashboard. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 it checks solution/solution.py instead of exercise.py.

The dashboard's look is scored with RUBRIC.md. This file checks the part with
one right answer: the model and the KPI numbers. Every expected value is
rebuilt here in plain Python from the raw CSV rows (no SQL), never read from
the solution. The checks run on the committed data, on a second dataset built
in memory with another seed, and on tiny hand-made tables.

Optional export check: if you rebuilt the dashboard in a BI tool, export its
card values to exports/kpis_from_tool.csv (columns kpi,value for September
2026: net_revenue, orders, gross_margin_pct, lfl_growth_pct) and this test
compares them with the model. It is skipped when the file is absent.
"""
import csv
import datetime as dt
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
EXPORT = os.path.join(HERE, "exports", "kpis_from_tool.csv")
OTHER_SEED = 11
MONTH = "2026-09"
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("capstone", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402


# ---- an independent rebuild in plain Python ------------------------------------------

def shift(month, n):
    i = int(month[:4]) * 12 + int(month[5:7]) - 1 + n
    return "%04d-%02d" % (i // 12, i % 12 + 1)


class Expected:
    def __init__(self, raw):
        best = {}
        for r in sorted(raw["daily_sales"], key=lambda r: r["loaded_at"]):
            best[(r["sales_date"], r["store_id"])] = r
        self.sales = {}
        for k, r in best.items():
            net = float(r["gross_sales"]) - (float(r["discounts"]) if k[0] < "2026-07-01" else 0.0)
            self.sales[k] = (int(r["orders"]), net, float(r["cogs"]))
        self.stores = {s["store_id"]: s for s in raw["stores"]}
        self.closures = raw["store_closures"]
        self.targets = {}
        for t in raw["targets"]:
            self.targets[(t["month"], t["store_id"])] = float(t["revenue_target"])
        dates = sorted(d for d, _ in self.sales)
        self.first, self.last = (dates[0], dates[-1]) if dates else (None, None)

    def closed(self, sid, day):
        return any(c["store_id"] == sid and c["closed_from"] <= day <= c["closed_to"] for c in self.closures)

    def month_dates(self, month):
        d = dt.date.fromisoformat(self.first)
        while d.isoformat() <= self.last:
            if d.isoformat()[:7] == month:
                yield d.isoformat()
            d += dt.timedelta(days=1)

    def totals(self, month, stores=None):
        o = r = c = 0.0
        for (d, s), v in self.sales.items():
            if d[:7] == month and (stores is None or s in stores):
                o += v[0]
                r += v[1]
                c += v[2]
        return o, r, c

    def lfl(self, month):
        ly = shift(month, -12)
        out = []
        for sid, s in sorted(self.stores.items()):
            if s["opened_on"] > ly + "-01":
                continue
            if any(c["store_id"] == sid and (c["closed_from"][:7] <= mo <= c["closed_to"][:7])
                   for c in self.closures for mo in (month, ly)):
                continue
            out.append(sid)
        return out

    def missing(self, month):
        return sorted((sid, d) for sid, s in self.stores.items() for d in self.month_dates(month)
                      if d >= s["opened_on"] and not self.closed(sid, d) and (d, sid) not in self.sales)

    def kpis(self, month):
        o, r, c = self.totals(month)
        _, rly, _ = self.totals(shift(month, -12))
        target = sum(v for (mo, _), v in self.targets.items() if mo == month)
        stores = self.lfl(month)
        now, then = self.totals(month, stores)[1], self.totals(shift(month, -12), stores)[1]
        return {"net_revenue": r, "orders": o, "aov": r / o if o else None,
                "gross_margin_pct": 100 * (r - c) / r if r else None,
                "target": target or None, "vs_target_pct": 100 * r / target if target else None,
                "net_revenue_ly": rly, "yoy_pct": 100 * (r / rly - 1) if rly else None,
                "lfl_stores": stores, "lfl_growth_pct": 100 * (now / then - 1) if stores and then else None,
                "missing_days": len(self.missing(month))}


def exp_status(p):
    return None if p is None else ("green" if p >= 100 else "amber" if p >= 95 else "red")


# ---- hand-made cases ---------------------------------------------------------------------

def sale(day, store, orders, gross, disc, cogs, loaded):
    return {"sales_date": day, "store_id": store, "orders": str(orders), "gross_sales": str(gross),
            "discounts": str(disc), "cogs": str(cogs), "loaded_at": loaded}


def tiny_raw(sales, targets=(), closures=()):
    return {"daily_sales": list(sales),
            "stores": [{"store_id": "A", "store_name": "A", "city": "x", "opened_on": "2025-01-01"},
                       {"store_id": "B", "store_name": "B", "city": "y", "opened_on": "2026-06-15"}],
            "store_closures": list(closures),
            "targets": [{"month": mo, "store_id": s, "revenue_target": str(v)} for mo, s, v in targets]}


class TestHandMade(unittest.TestCase):
    def model(self, raw):
        con = m.build_model(raw)
        self.addCleanup(con.close)
        return con

    def test_clean_sales(self):
        rows = [sale("2026-06-30", "A", 10, 110, 10, 30, "2026-07-01 02:00:00"),
                sale("2026-07-01", "A", 10, 100, 10, 30, "2026-07-02 02:00:00"),
                sale("2026-07-01", "A", 20, 200, 20, 60, "2026-07-05 09:00:00"),
                sale("2026-07-01", "A", 15, 150, 15, 45, "2026-07-03 02:00:00")]
        got = m.clean_sales(rows)
        self.assertEqual([(r["sales_date"], r["orders"]) for r in got], [("2026-06-30", 10), ("2026-07-01", 20)],
                         "one row per day and store: the load with the latest loaded_at")
        self.assertAlmostEqual(got[0]["net_revenue"], 100, msg="before 1 July net revenue = gross - discounts")
        self.assertAlmostEqual(got[1]["net_revenue"], 200, msg="from 1 July gross_sales is already net: do not subtract again")
        self.assertEqual(m.clean_sales([]), [])

    def test_model_and_checks(self):
        raw = tiny_raw([sale("2026-06-30", "A", 10, 110, 10, 30, "x"), sale("2026-07-02", "A", 5, 50, 0, 20, "x")],
                       closures=[{"store_id": "A", "closed_from": "2026-07-01", "closed_to": "2026-07-01", "reason": "r"}])
        con = self.model(raw)
        dates = [r[0] for r in con.execute("SELECT date_key FROM dim_date ORDER BY date_key")]
        self.assertEqual(dates, ["2026-06-30", "2026-07-01", "2026-07-02"], "dim_date has every day, even with no sales")
        self.assertEqual(con.execute("SELECT day_of_week, is_weekend FROM dim_date WHERE date_key = '2026-07-02'").fetchone(),
                         (3, 0), "2 July 2026 is a Thursday: day_of_week 3 (Monday is 0), not a weekend")
        self.assertEqual(m.check_model(con), [], "a sound model has no problems")
        con.execute("INSERT INTO fact_sales VALUES ('2026-07-01', 'A', 1, 5.0, 1.0)")
        self.assertEqual(len(m.check_model(con)), 1, "a sale on a closed day is a problem")
        con.execute("INSERT INTO fact_sales VALUES ('2026-07-02', 'Z', 1, 5.0, 1.0)")
        con.execute("INSERT INTO fact_sales VALUES ('2026-06-30', 'A', 1, 5.0, 1.0)")
        self.assertEqual(len(m.check_model(con)), 3, "an unknown store and a duplicate day are problems too")

    def test_missing_and_lfl(self):
        raw = tiny_raw([sale("2026-06-14", "A", 1, 1, 0, 0, "x"), sale("2026-06-16", "A", 1, 1, 0, 0, "x"),
                        sale("2026-06-16", "B", 1, 1, 0, 0, "x")],
                       closures=[{"store_id": "A", "closed_from": "2026-06-15", "closed_to": "2026-06-15", "reason": "r"}])
        con = self.model(raw)
        self.assertEqual(m.missing_days(con, "2026-06"), [("B", "2026-06-15")],
                         "A was closed on the 15th; B was open from the 15th and sent nothing")
        self.assertEqual(m.lfl_stores(con, "2026-06"), [], "A had a closure this month; B opened this year")
        self.assertEqual(m.lfl_stores(con, "2026-07"), ["A"], "A traded all of July 2025 and July 2026")

    def test_kpis_edges(self):
        raw = tiny_raw([sale("2026-06-30", "A", 0, 0, 0, 0, "x")], targets=[("2026-07", "A", 1000)])
        k = m.monthly_kpis(self.model(raw), "2026-06")
        self.assertIsNone(k["aov"], "no orders: AOV is None, not 0")
        self.assertIsNone(k["gross_margin_pct"], "no revenue: margin is None")
        self.assertIsNone(k["vs_target_pct"], "no target this month")
        self.assertIsNone(k["status"])
        self.assertIsNone(k["yoy_pct"], "no sales a year earlier")
        self.assertIsNone(k["lfl_growth_pct"])
        self.assertEqual([m.status(x) for x in (100.0, 99.99, 95.0, 94.99, None)],
                         ["green", "amber", "amber", "red", None], "green 100+, amber 95 to 100, red below 95")


# ---- the real data ---------------------------------------------------------------------

class OnDataMixin:
    @classmethod
    def setUpClass(cls):
        cls.raw = m.load(DATA)
        cls.setup_common()

    @classmethod
    def setup_common(cls):
        cls.exp = Expected(cls.raw)
        cls.con = m.build_model(cls.raw)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def test_model(self):
        n = lambda sql: self.con.execute(sql).fetchone()[0]  # noqa: E731
        days = (dt.date.fromisoformat(self.exp.last) - dt.date.fromisoformat(self.exp.first)).days + 1
        self.assertEqual(n("SELECT COUNT(*) FROM dim_date"), days, "dim_date: one row per day, first to last sale")
        self.assertEqual(n("SELECT COUNT(*) FROM fact_sales"), len(self.exp.sales),
                         "fact_sales: one row per day and store after de-duplication")
        self.assertAlmostEqual(n("SELECT SUM(net_revenue) FROM fact_sales"),
                               sum(v[1] for v in self.exp.sales.values()), places=2,
                               msg="fact_sales must reconcile to the cleaned rows")
        self.assertEqual(m.check_model(self.con), [], "the clean model passes its own checks")

    def test_kpis(self):
        for month in (MONTH, "2026-07", "2026-06", "2026-03", "2025-12"):
            got, exp = m.monthly_kpis(self.con, month), self.exp.kpis(month)
            for key, v in exp.items():
                if isinstance(v, float):
                    self.assertAlmostEqual(got[key], v, delta=0.011, msg="%s %s" % (month, key))
                else:
                    self.assertEqual(got[key], v, "%s %s" % (month, key))
            self.assertEqual(got["status"], exp_status(got["vs_target_pct"]))

    def test_missing_days(self):
        self.assertEqual(m.missing_days(self.con, MONTH), self.exp.missing(MONTH))

    def test_store_table(self):
        got = m.store_table(self.con, MONTH)
        self.assertEqual([r["store_id"] for r in got], sorted(self.exp.stores))
        for r in got:
            _, rev, cogs = self.exp.totals(MONTH, [r["store_id"]])
            t = self.exp.targets.get((MONTH, r["store_id"]))
            self.assertAlmostEqual(r["net_revenue"], rev, delta=0.011, msg="store %s revenue" % r["store_id"])
            self.assertAlmostEqual(r["vs_target_pct"], 100 * rev / t, delta=0.011)
            self.assertAlmostEqual(r["gross_margin_pct"], 100 * (rev - cogs) / rev, delta=0.011)

    def test_trend(self):
        got = m.trend(self.con, MONTH)
        self.assertEqual([mo for mo, _ in got], [shift(MONTH, -k) for k in range(12, -1, -1)], "13 months, oldest first")
        for mo, v in got:
            self.assertAlmostEqual(v, self.exp.totals(mo)[1], delta=0.011, msg="trend %s" % mo)

    def test_story(self):
        k = m.monthly_kpis(self.con, MONTH)
        self.assertGreater(k["yoy_pct"] - k["lfl_growth_pct"], 10,
                           "the headline growth is mostly the new shop and last year's refit, not like-for-like")
        self.assertNotIn("KM03", k["lfl_stores"], "Leeds was shut for a refit in September 2025")


class TestOnData(OnDataMixin, unittest.TestCase):
    @unittest.skipUnless(os.path.exists(EXPORT), "no exports/kpis_from_tool.csv: the BI-tool check is optional")
    def test_tool_export(self):
        with open(EXPORT, newline="") as f:
            tool = {r["kpi"]: float(r["value"]) for r in csv.DictReader(f)}
        k = self.exp.kpis(MONTH)
        for key in ("net_revenue", "orders", "gross_margin_pct", "lfl_growth_pct"):
            if key in tool:
                self.assertAlmostEqual(tool[key], k[key], delta=0.05 if key.endswith("pct") else 1.0,
                                       msg="your BI tool's %s disagrees with the model" % key)


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so typed-in numbers fail."""

    @classmethod
    def setUpClass(cls):
        cls.raw = make_data.build(seed=OTHER_SEED)
        cls.setup_common()


if __name__ == "__main__":
    unittest.main()
