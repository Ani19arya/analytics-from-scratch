"""Tests for lesson 08-03: incremental models and backfills.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected tables are computed here in plain Python, never with SQL: the
latest version of each order as of a date, the daily totals, and a nightly
incremental run simulated as a dictionary whose window of days is replaced
each night. Your functions run on three kinds of data:
1. the committed data/raw_orders.csv,
2. a second feed built in memory with make_data.build(seed=2027), with other
   volumes and a different longest delay, so typing out answers cannot pass,
3. tiny hand-made feeds: an empty feed, an order that lands exactly
   lookback_days late (caught) and one day later (missed), a day with only a
   cancelled order (revenue 0, not NULL), a refund that lands after the
   window, and the same run repeated (no duplicate rows).
"""
import datetime
import importlib.util
import os
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

SECOND_SEED = 2027
TEAM_LOOKBACK = 3
START, END = "2026-09-01", "2026-10-31"


# Reference answers, in plain Python.

def day_add(day, n):
    y, m, d = (int(x) for x in day.split("-"))
    return (datetime.date(y, m, d) + datetime.timedelta(days=n)).isoformat()


def days_between(a, b):
    out = []
    while a <= b:
        out.append(a)
        a = day_add(a, 1)
    return out


def ref_days(rows, lo, hi, as_of):
    latest = {}
    for r in rows:
        if r["load_date"] > as_of:
            continue
        k = int(r["order_id"])
        if k not in latest or r["load_date"] > latest[k]["load_date"]:
            latest[k] = r
    out = {}
    for r in latest.values():
        if not (lo <= r["order_date"] <= hi):
            continue
        g = out.setdefault(r["order_date"], [0, 0, 0.0])
        g[0] += 1
        if r["status"] == "delivered":
            g[1] += 1
            g[2] += float(r["amount"])
    return {d: (g[0], g[1], round(g[2], 2)) for d, g in out.items()}


def ref_incremental(rows, start, end, lookback):
    table = ref_days(rows, "0000-01-01", "9999-12-31", start)
    for run in days_between(day_add(start, 1), end):
        lo = day_add(run, -lookback)
        table = {d: v for d, v in table.items() if not (lo <= d <= run)}
        table.update(ref_days(rows, lo, run, run))
    return table


def ref_lookback(rows):
    best = 0
    for r in rows:
        y1, m1, d1 = (int(x) for x in r["load_date"].split("-"))
        y2, m2, d2 = (int(x) for x in r["order_date"].split("-"))
        best = max(best, (datetime.date(y1, m1, d1) - datetime.date(y2, m2, d2)).days)
    return best


def ref_stale(a, b):
    return sorted(d for d in set(a) | set(b) if d not in a or d not in b or a[d][:2] != b[d][:2] or abs(a[d][2] - b[d][2]) > 0.005)


def committed():
    return lesson.read_raw()


class IncrementalTest(unittest.TestCase):
    def call(self, fn, *args):
        try:
            return getattr(lesson, fn)(*args)
        except NotImplementedError:
            self.fail("%s is not written yet: fill it in in exercise.py" % fn)

    def fresh(self, rows):
        return lesson.load_raw(sqlite3.connect(":memory:"), rows)

    def table(self, con):
        rows = lesson.table_rows(con)
        return {d: (o, dl, rev) for d, (o, dl, rev) in rows.items()}

    def assertTableEqual(self, con, want, label):
        got = self.table(con)
        self.assertEqual(sorted(got), sorted(want), "%s: daily_revenue should have one row for each of these %d days, it has %d rows" % (label, len(want), len(got)))
        for d, (o, dl, rev) in want.items():
            g = got[d]
            self.assertEqual((g[0], g[1]), (o, dl), "%s: %s should have orders=%d and delivered_orders=%d (latest version of each order), not %r" % (label, d, o, dl, g[:2]))
            self.assertIsNotNone(g[2], "%s: %s revenue is NULL; it must be 0 when nothing was delivered" % (label, d))
            self.assertAlmostEqual(g[2], rev, 2, "%s: %s revenue should be %.2f" % (label, d, rev))

    def simulate(self, rows, start, end, lookback):
        con = self.fresh(rows)
        self.call("full_rebuild", con, start)
        for run in days_between(day_add(start, 1), end):
            self.call("incremental_run", con, run, lookback)
        return con

    def check_feed(self, rows, label, start=START, end=END):
        full = self.fresh(rows)
        self.call("full_rebuild", full, end)
        want_full = ref_days(rows, "0000-01-01", "9999-12-31", end)
        self.assertTableEqual(full, want_full, "%s, full rebuild" % label)
        need = ref_lookback(rows)
        self.assertEqual(self.call("required_lookback", full), need, "%s: required_lookback should be %d, the longest load_date - order_date in days" % (label, need))

        short = self.simulate(rows, start, end, TEAM_LOOKBACK)
        want_short = ref_incremental(rows, start, end, TEAM_LOOKBACK)
        self.assertTableEqual(short, want_short, "%s, nightly runs with lookback %d" % (label, TEAM_LOOKBACK))
        stale = ref_stale(want_short, want_full)
        self.assertEqual(self.call("stale_days", short, full), stale, "%s: stale_days should list the %d days where the incremental table and the full rebuild differ" % (label, len(stale)))
        self.assertEqual(self.call("stale_days", full, full), [], "%s: a table compared with itself has no stale days" % label)

        if stale:
            self.call("backfill", short, stale[0], stale[-1], end)
            self.assertTableEqual(short, want_full, "%s, after backfilling %s to %s" % (label, stale[0], stale[-1]))
            self.assertEqual(self.call("stale_days", short, full), [], "%s: after the backfill the incremental table must equal the full rebuild" % label)

        enough = self.simulate(rows, start, end, need)
        self.assertTableEqual(enough, want_full, "%s, nightly runs with lookback %d (the required lookback)" % (label, need))
        return stale, need

    def test_committed_feed(self):
        stale, need = self.check_feed(committed(), "committed data")
        self.assertGreater(len(stale), 0, "committed data: a 3-day lookback should miss some late refunds")
        self.assertGreater(need, TEAM_LOOKBACK, "committed data: some rows land more than 3 days late")

    def test_second_feed(self):
        self.check_feed(make_data.build(SECOND_SEED)["raw_orders"], "seed %d" % SECOND_SEED)

    def test_empty_feed(self):
        con = self.fresh([])
        self.call("full_rebuild", con, END)
        self.assertEqual(self.table(con), {}, "an empty raw table gives an empty daily_revenue")
        self.assertEqual(self.call("required_lookback", con), 0, "required_lookback of an empty raw table is 0")
        self.call("incremental_run", con, END, TEAM_LOOKBACK)
        self.assertEqual(self.table(con), {}, "an incremental run over an empty raw table writes nothing")

    def test_window_edges_and_reruns(self):
        def row(load, oid, day, status, amount):
            return {"load_date": load, "order_id": oid, "order_date": day, "status": status, "amount": amount}
        rows = [
            row("2026-09-01", 1, "2026-09-01", "delivered", "100.00"),
            row("2026-09-02", 2, "2026-09-02", "cancelled", "40.00"),     # only a cancelled order
            row("2026-09-03", 3, "2026-09-01", "delivered", "10.50"),     # 2 days late
            row("2026-09-04", 4, "2026-09-01", "delivered", "7.25"),      # 3 days late
            row("2026-09-06", 1, "2026-09-01", "refunded", "100.00"),     # refund 5 days later
        ]
        con = self.simulate(rows, "2026-09-01", "2026-09-06", 2)
        self.assertTableEqual(con, ref_incremental(rows, "2026-09-01", "2026-09-06", 2), "hand-made, lookback 2")
        got = self.table(con)
        self.assertEqual(got["2026-09-01"][:2], (2, 2), "lookback 2: the run on 3 Sep covers 1 Sep (both ends included), so order 3 is in; order 4 (3 days late) and the refund are missed")
        self.assertAlmostEqual(got["2026-09-01"][2], 110.5, 2, "lookback 2: 1 Sep revenue should be 100.00 + 10.50")
        self.assertEqual(got["2026-09-02"], (1, 0, 0), "2 Sep has only a cancelled order: orders 1, delivered 0, revenue 0, not NULL")

        con3 = self.simulate(rows, "2026-09-01", "2026-09-06", 3)
        self.assertEqual(self.table(con3)["2026-09-01"][:2], (3, 3), "lookback 3 catches order 4 on 4 Sep, but the refund on 6 Sep is 5 days after its order date")
        self.call("incremental_run", con3, "2026-09-06", 3)
        self.call("incremental_run", con3, "2026-09-06", 3)
        n = con3.execute("SELECT COUNT(*), COUNT(DISTINCT order_date) FROM daily_revenue").fetchone()
        self.assertEqual(n[0], n[1], "running the same night twice must not duplicate rows: delete the window before inserting")

        full = self.fresh(rows)
        self.call("full_rebuild", full, "2026-09-06")
        self.assertEqual(self.call("stale_days", con3, full), ["2026-09-01"], "only 1 Sep differs: its refund landed outside every window")
        self.call("backfill", con3, "2026-09-01", "2026-09-01", "2026-09-06")
        self.assertEqual(self.table(con3)["2026-09-01"][:2], (3, 2), "after the backfill order 1 is refunded: 3 orders, 2 delivered")
        self.assertAlmostEqual(self.table(con3)["2026-09-01"][2], 17.75, 2, "after the backfill 1 Sep revenue is 10.50 + 7.25")
        self.assertEqual(self.call("stale_days", con3, full), [], "after the backfill nothing is stale")
        self.assertEqual(self.call("required_lookback", full), 5, "the refund of order 1 landed 5 days after its order date")

        before = self.table(con3)
        self.call("backfill", con3, "2026-09-02", "2026-09-02", "2026-09-06")
        self.assertEqual(self.table(con3), before, "a backfill of one day must leave the other days untouched")
        empty = self.fresh([])
        self.assertEqual(self.call("stale_days", con3, empty), sorted(before), "a day missing from one table counts as stale")


if __name__ == "__main__":
    unittest.main(verbosity=2)
