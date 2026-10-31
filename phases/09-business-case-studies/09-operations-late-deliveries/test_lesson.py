"""Tests for case 09: operations, why are deliveries late? Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (the Sunday and Monday either side of the split, delivery on the
promised day itself, the 16:00 and 20:00 band edges, a warehouse with only one
period, a parcel the what-if cannot help, no after-period shipments at all).
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
DATA = os.path.join(HERE, "data", "shipments.csv")
OTHER_SEED = 4
START = datetime.date(2026, 7, 6)
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


def ts(text):
    return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")


def week_of(row):
    return (ts(row["order_ts"]).date() - START).days // 7 + 1


def period_of(row):
    return "before" if week_of(row) <= 6 else "after"


def on_time(row):
    return row["delivered_ts"][:10] <= row["promised_date"]


def hours(a, b):
    return (ts(b) - ts(a)).total_seconds() / 3600.0


def run_sql(con, sql):
    body = "\n".join(ln for ln in (sql or "").splitlines() if not ln.strip().startswith("--"))
    if not body.strip():
        raise AssertionError("the query is still a TODO: write it in the exercise file")
    return m.query(con, sql)


def ship(sid, order, warehouse, packed, collected, delivered, promised, carrier="A", zone=1):
    return {"shipment_id": sid, "order_ts": order, "warehouse": warehouse, "carrier": carrier, "zone": str(zone),
            "packed_ts": packed, "collected_ts": collected, "delivered_ts": delivered, "promised_date": promised}


def tiny_db(rows):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE shipments (shipment_id TEXT, order_ts TEXT, warehouse TEXT, carrier TEXT,"
                " zone INTEGER, packed_ts TEXT, collected_ts TEXT, delivered_ts TEXT, promised_date TEXT)")
    for r in rows:
        con.execute("INSERT INTO shipments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [r[k] for k in make_data.FIELDS])
    return con


class TestHandMade(unittest.TestCase):
    def test_week_boundary_and_on_time_day(self):
        rows = [ship("1", "2026-08-16 23:30", "North", "2026-08-17 01:00", "2026-08-17 20:00", "2026-08-18 20:59", "2026-08-18"),
                ship("2", "2026-08-17 00:10", "North", "2026-08-17 02:00", "2026-08-17 20:00", "2026-08-20 00:30", "2026-08-19")]
        got = run_sql(tiny_db(rows), m.WEEKLY_SQL)
        self.assertEqual([(g["week"], g["shipments"], g["on_time"], g["on_time_pct"]) for g in got],
                         [(6, 1, 1, 100.0), (7, 1, 0, 0.0)],
                         "the week comes from the order date (Sunday 16 Aug is week 6); delivered on the promised day "
                         "at 20:59 is on time, the next day at 00:30 is late: compare dates, not timestamps")

    def test_stage_hours(self):
        rows = [ship("1", "2026-07-06 10:00", "South", "2026-07-06 12:00", "2026-07-06 20:00", "2026-07-07 14:00", "2026-07-08"),
                ship("2", "2026-07-07 10:00", "South", "2026-07-07 11:00", "2026-07-07 20:00", "2026-07-08 20:00", "2026-07-09")]
        got = run_sql(tiny_db(rows), m.STAGE_SQL)
        self.assertEqual(len(got), 1, "one row per warehouse and period that has shipments")
        g = got[0]
        self.assertEqual((g["warehouse"], g["period"], g["shipments"]), ("South", "before", 2))
        self.assertEqual([g["pack_h"], g["dwell_h"], g["transit_h"], g["total_h"], g["on_time_pct"]],
                         [1.5, 8.5, 21.0, 31.0, 100.0],
                         "hours between timestamps: julianday difference x 24, averaged over the shipments")

    def test_band_edges(self):
        rows = [ship("1", "2026-07-06 14:00", "North", "2026-07-06 15:59", "2026-07-06 20:00", "2026-07-07 12:00", "2026-07-08"),
                ship("2", "2026-07-06 14:00", "North", "2026-07-06 16:00", "2026-07-06 20:00", "2026-07-07 12:00", "2026-07-08"),
                ship("3", "2026-07-06 19:00", "North", "2026-07-06 20:00", "2026-07-07 20:00", "2026-07-09 12:00", "2026-07-08")]
        got = run_sql(tiny_db(rows), m.BAND_SQL)
        self.assertEqual([(g["packed_band"], g["shipments"], g["on_time_pct"]) for g in got],
                         [("00-16", 1, 100.0), ("16-20", 1, 100.0), ("20-24", 1, 0.0)],
                         "15:59 is before 16:00; 16:00 starts '16-20'; 20:00 starts '20-24'")

    def test_stage_change(self):
        rows = [
            {"warehouse": "A", "period": "after", "pack_h": 2.0, "dwell_h": 7.0, "transit_h": 30.0},
            {"warehouse": "A", "period": "before", "pack_h": 2.0, "dwell_h": 6.0, "transit_h": 31.0},
            {"warehouse": "B", "period": "after", "pack_h": 3.0, "dwell_h": 6.0, "transit_h": 30.0},
            {"warehouse": "B", "period": "before", "pack_h": 2.0, "dwell_h": 6.0, "transit_h": 30.0},
            {"warehouse": "C", "period": "after", "pack_h": 9.0, "dwell_h": 9.0, "transit_h": 99.0},
        ]
        got = m.stage_change(rows)
        self.assertEqual([(g["warehouse"], g["stage"], g["change"]) for g in got],
                         [("A", "dwell", 1.0), ("B", "pack", 1.0), ("A", "pack", 0.0), ("B", "dwell", 0.0),
                          ("B", "transit", 0.0), ("A", "transit", -1.0)],
                         "change = after - before, largest first, ties by warehouse then stage; "
                         "a warehouse with only one period (C) is left out")
        self.assertEqual(m.stage_change([]), [])

    def test_what_if(self):
        rows = [
            # week 7, South, packed 16:30, collected next day at 16:10, late
            ship("1", "2026-08-17 14:00", "South", "2026-08-17 16:30", "2026-08-18 16:10", "2026-08-20 09:00", "2026-08-19"),
            # week 7, South, packed 20:30: a 20:00 collection would not take it the same day either
            ship("2", "2026-08-17 19:00", "South", "2026-08-17 20:30", "2026-08-18 16:05", "2026-08-20 10:00", "2026-08-19"),
            # week 7, North: untouched
            ship("3", "2026-08-18 09:00", "North", "2026-08-18 10:00", "2026-08-18 20:00", "2026-08-19 15:00", "2026-08-20"),
            # week 1: not counted
            ship("4", "2026-07-06 09:00", "South", "2026-07-06 10:00", "2026-07-06 20:00", "2026-07-10 15:00", "2026-07-08"),
        ]
        self.assertAlmostEqual(m.on_time_with_collection(rows, "South", 20), 200.0 / 3,
                               msg="parcel 1 moves one day earlier and is on time; parcel 2 does not move; "
                                   "only week 7 onward counts: 2 of 3 on time")
        self.assertAlmostEqual(m.on_time_with_collection(rows, "South", 15), 100.0 / 3,
                               msg="with a 15:00 collection nothing moves earlier: 1 of 3 on time")
        self.assertIsNone(m.on_time_with_collection(rows[3:], "South", 20), "no shipments from week 7: None")

    def test_text_chart(self):
        self.assertEqual(m.text_chart([]), [])
        lines = m.text_chart([{"week": 1, "on_time_pct": 100.0}, {"week": 2, "on_time_pct": 90.0},
                              {"week": 3, "on_time_pct": 70.0}], low=80.0, width=10)
        self.assertEqual([ln.count("#") for ln in lines], [10, 5, 0],
                         "the axis starts at `low`: 90% is half way from 80 to 100; below `low` draws nothing")
        self.assertTrue(lines[0].startswith("W01 100.0%"), "lines look like 'W01 100.0% ##########'")


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
            e[1] += on_time(r)
        got = run_sql(self.con, m.WEEKLY_SQL)
        self.assertEqual([g["week"] for g in got], sorted(exp), "one row per week, 1 to 12")
        for g in got:
            n, k = exp[g["week"]]
            self.assertEqual((g["shipments"], g["on_time"]), (n, k), "week %d" % g["week"])
            self.assertAlmostEqual(g["on_time_pct"], 100.0 * k / n, delta=0.06)

    def expected_stages(self):
        exp = {}
        for r in self.rows:
            e = exp.setdefault((r["warehouse"], period_of(r)), [0, 0.0, 0.0, 0.0, 0.0, 0])
            e[0] += 1
            e[1] += hours(r["order_ts"], r["packed_ts"])
            e[2] += hours(r["packed_ts"], r["collected_ts"])
            e[3] += hours(r["collected_ts"], r["delivered_ts"])
            e[4] += hours(r["order_ts"], r["delivered_ts"])
            e[5] += on_time(r)
        return exp

    def test_stages(self):
        exp = self.expected_stages()
        got = run_sql(self.con, m.STAGE_SQL)
        self.assertEqual([(g["warehouse"], g["period"]) for g in got], sorted(exp),
                         "one row per warehouse and period, ordered by warehouse then period")
        for g in got:
            n, p, d, t, tot, k = exp[(g["warehouse"], g["period"])]
            self.assertEqual(g["shipments"], n)
            for name, v in (("pack_h", p), ("dwell_h", d), ("transit_h", t), ("total_h", tot)):
                self.assertAlmostEqual(g[name], round(v / n, 2), delta=0.011,
                                       msg="%s for %s %s" % (name, g["warehouse"], g["period"]))
            self.assertAlmostEqual(g["on_time_pct"], 100.0 * k / n, delta=0.06)

    def test_bands(self):
        exp = {}
        for r in self.rows:
            hm = r["packed_ts"][11:]
            band = "00-16" if hm < "16:00" else ("16-20" if hm < "20:00" else "20-24")
            e = exp.setdefault((r["warehouse"], period_of(r), band), [0, 0])
            e[0] += 1
            e[1] += on_time(r)
        got = run_sql(self.con, m.BAND_SQL)
        self.assertEqual([(g["warehouse"], g["period"], g["packed_band"]) for g in got], sorted(exp))
        for g in got:
            n, k = exp[(g["warehouse"], g["period"], g["packed_band"])]
            self.assertEqual(g["shipments"], n)
            self.assertAlmostEqual(g["on_time_pct"], 100.0 * k / n, delta=0.06)

    def test_insight(self):
        exp = self.expected_stages()
        changes = {}
        for wh in ("North", "South"):
            for i, st in enumerate(("pack", "dwell", "transit"), 1):
                changes[(wh, st)] = exp[(wh, "after")][i] / exp[(wh, "after")][0] - exp[(wh, "before")][i] / exp[(wh, "before")][0]
        top = max(changes, key=changes.get)
        self.assertEqual(top, ("South", "dwell"), "the planted cause is the wait for collection at South")
        got = m.stage_change(run_sql(self.con, m.STAGE_SQL))
        self.assertEqual((got[0]["warehouse"], got[0]["stage"]), top)
        self.assertAlmostEqual(got[0]["change"], changes[top], delta=0.02)
        # what-if: South collected at 20:00 again from week 7
        total = good = 0
        for r in self.rows:
            if week_of(r) < 7:
                continue
            delivered = ts(r["delivered_ts"]).date()
            if r["warehouse"] == "South":
                packed = ts(r["packed_ts"])
                new_day = packed.date() + datetime.timedelta(days=0 if packed.hour < 20 else 1)
                shift = (ts(r["collected_ts"]).date() - new_day).days
                delivered -= datetime.timedelta(days=max(0, shift))
            total += 1
            good += delivered.isoformat() <= r["promised_date"]
        what_if = m.on_time_with_collection(self.rows, "South", 20)
        self.assertAlmostEqual(what_if, 100.0 * good / total, places=6)
        after = [r for r in self.rows if week_of(r) >= 7]
        self.assertGreater(what_if, 100.0 * sum(on_time(r) for r in after) / len(after),
                           "restoring the 20:00 collection must improve on-time delivery")


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.path = os.path.join(cls.tmp, "shipments.csv")
        make_data.write_csv(make_data.build(seed=OTHER_SEED)["shipments"], cls.path)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
