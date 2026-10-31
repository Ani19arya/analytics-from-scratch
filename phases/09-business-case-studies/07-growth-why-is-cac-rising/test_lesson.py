"""Tests for case 07: growth, why is acquisition cost rising? Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python from the CSV rows, never
with SQL and never read from the solution. The checks run on the committed data,
on a second dataset built in memory with another seed, and on tiny hand-made
tables (the join fan-out, a channel with no spend, a week with no paid
subscribers, the quarter boundary, a platform missing from the base quarter, zero).
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
SPEND = os.path.join(HERE, "data", "spend.csv")
ACQ = os.path.join(HERE, "data", "acquisitions.csv")
OTHER_SEED = 12
START = datetime.date(2026, 1, 5)
PAID = ("search", "social", "video")
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


def week_of(day):
    return (datetime.date.fromisoformat(day) - START).days // 7 + 1


def quarter_of(day):
    return "Q%d" % ((week_of(day) - 1) // 13 + 1)


def run_sql(con, sql):
    body = "\n".join(ln for ln in (sql or "").splitlines() if not ln.strip().startswith("--"))
    if not body.strip():
        raise AssertionError("the query is still a TODO: write it in the exercise file")
    return m.query(con, sql)


def tiny_db(spend, acq):
    """spend: (week_start, channel, spend); acq: (week_start, channel, platform, signups, subscribers)."""
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE spend (week_start TEXT, channel TEXT, spend REAL)")
    con.execute("CREATE TABLE acquisitions (week_start TEXT, channel TEXT, platform TEXT,"
                " signups INTEGER, subscribers INTEGER)")
    con.executemany("INSERT INTO spend VALUES (?, ?, ?)", spend)
    con.executemany("INSERT INTO acquisitions VALUES (?, ?, ?, ?, ?)", acq)
    return con


def qrow(quarter, channel, spend, signups, subscribers):
    return {"quarter": quarter, "channel": channel, "spend": spend, "signups": signups, "subscribers": subscribers}


def prow(quarter, platform, subscribers, unattributed):
    return {"quarter": quarter, "platform": platform, "subscribers": subscribers, "unattributed": unattributed}


class TestHandMade(unittest.TestCase):
    def test_no_fan_out_and_no_spend_channel(self):
        con = tiny_db([("2026-01-05", "social", 300.0)],
                      [("2026-01-05", "social", "ios", 8, 2), ("2026-01-05", "social", "android", 4, 1),
                       ("2026-01-05", "social", "web", 4, 1), ("2026-01-05", "organic", "web", 12, 3)])
        got = run_sql(con, m.QUARTER_SQL)
        self.assertEqual([(g["quarter"], g["channel"], g["spend"], g["signups"], g["subscribers"]) for g in got],
                         [("Q1", "organic", 0, 12, 3), ("Q1", "social", 300.0, 16, 4)],
                         "spend is 300, not 900: aggregate each table before joining (one spend row matches three "
                         "platform rows), and organic spend is 0, not NULL")

    def test_quarter_boundary(self):
        # Monday 30 March is week 13 (Q1); Monday 6 April is week 14 (Q2).
        con = tiny_db([("2026-03-30", "search", 100.0), ("2026-04-06", "search", 50.0)],
                      [("2026-03-30", "search", "web", 4, 1), ("2026-04-06", "search", "web", 4, 1)])
        got = run_sql(con, m.QUARTER_SQL)
        self.assertEqual([(g["quarter"], g["spend"]) for g in got], [("Q1", 100.0), ("Q2", 50.0)],
                         "weeks 1 to 13 are Q1: the week of 30 March is still Q1, 6 April starts Q2")

    def test_weekly_zero_paid_subscribers(self):
        con = tiny_db([("2026-01-05", "video", 200.0), ("2026-01-12", "video", 100.0)],
                      [("2026-01-05", "video", "ios", 3, 0), ("2026-01-05", "unattributed", "ios", 4, 1),
                       ("2026-01-12", "video", "ios", 8, 2), ("2026-01-12", "organic", "android", 4, 1)])
        got = run_sql(con, m.WEEKLY_SQL)
        self.assertEqual([(g["week"], g["paid_spend"], g["paid_subscribers"], g["reported_cac"], g["ios_unattributed_pct"])
                          for g in got],
                         [(1, 200.0, 0, None, 100.0), (2, 100.0, 2, 50.0, 0.0)],
                         "no paid subscribers: reported_cac is NULL, not an error; organic and unattributed are not paid")

    def test_platform_sql(self):
        con = tiny_db([], [("2026-01-05", "unattributed", "ios", 4, 1), ("2026-01-05", "social", "ios", 8, 3),
                           ("2026-01-05", "social", "web", 4, 2)])
        got = run_sql(con, m.PLATFORM_SQL)
        self.assertEqual([(g["quarter"], g["platform"], g["subscribers"], g["unattributed"]) for g in got],
                         [("Q1", "ios", 4, 1), ("Q1", "web", 2, 0)],
                         "subscribers counts every channel; unattributed only the 'unattributed' channel, 0 not NULL")

    def test_cac_functions(self):
        rows = [qrow("Q1", "search", 100.0, 40, 10), qrow("Q1", "organic", 0.0, 40, 10),
                qrow("Q1", "video", 50.0, 0, 0)]
        self.assertAlmostEqual(m.reported_cac(rows, "Q1"), 15.0,
                               msg="reported CAC = paid spend 150 / paid subscribers 10; organic is not in it")
        self.assertIsNone(m.reported_cac(rows, "Q2"), "a quarter with no paid subscribers: None")
        cc = m.channel_cac(rows)
        self.assertEqual(set(cc), {("Q1", "search"), ("Q1", "video")}, "only paid channels")
        self.assertIsNone(cc[("Q1", "video")], "spend with no subscribers: None, not a division by zero")
        self.assertEqual(m.trial_to_paid(rows), {"Q1": 20 / 80})
        self.assertEqual(m.trial_to_paid([qrow("Q1", "search", 1.0, 0, 0)]), {"Q1": None})

    def test_excess_and_decompose(self):
        prows = [prow("Q1", "ios", 100, 2), prow("Q1", "web", 0, 0),
                 prow("Q3", "ios", 200, 44), prow("Q3", "web", 50, 1), prow("Q3", "android", 10, 1)]
        ex = m.excess_unattributed(prows)
        self.assertAlmostEqual(ex["ios"], 40.0, msg="ios: 44 - 200 x 2% = 40")
        self.assertAlmostEqual(ex["web"], 1.0, msg="a platform with 0 base subscribers has a base share of 0")
        self.assertAlmostEqual(ex["android"], 1.0, msg="a platform missing from the base quarter has a base share of 0")
        qrows = [qrow("Q1", "social", 1000.0, 0, 100), qrow("Q3", "social", 1500.0, 0, 100)]
        d = m.decompose(qrows, [prow("Q1", "ios", 100, 0), prow("Q3", "ios", 100, 25), prow("Q3", "web", 10, -5)])
        self.assertAlmostEqual(d["cac_base"], 10.0)
        self.assertAlmostEqual(d["cac_target"], 15.0)
        self.assertAlmostEqual(d["cac_corrected"], 12.0,
                               msg="corrected = 1500 / (100 + 25): only positive excess is added back")
        self.assertAlmostEqual(d["change_pct"], 50.0)
        self.assertAlmostEqual(d["tracking_pts"], 30.0)
        self.assertAlmostEqual(d["real_pts"], 20.0)
        self.assertAlmostEqual(d["tracking_pts"] + d["real_pts"], d["change_pct"],
                               msg="the two parts add up exactly to the reported change")

    def test_marginal(self):
        self.assertAlmostEqual(m.marginal_cac(1000, 100, 3000, 140), 50.0, msg="2000 more spend / 40 more subscribers")
        self.assertIsNone(m.marginal_cac(1000, 100, 3000, 100), "no extra subscribers: None")
        self.assertIsNone(m.marginal_cac(1000, 100, 3000, 90), "fewer subscribers: None")

    def test_text_chart(self):
        self.assertEqual(m.text_chart([]), [])
        lines = m.text_chart([("Q1", 40.0), ("Q3", 80.0), ("Q9", None)], width=10)
        self.assertEqual([ln.count("#") for ln in lines], [5, 10, 0], "largest value gets `width`; None counts as 0")
        self.assertTrue(lines[1].startswith("Q3 "), "each line starts with the label")
        self.assertEqual(m.text_chart([("a", 0.0)], width=10)[0].count("#"), 0, "all values 0: no bars")


class OnDataMixin:
    spend_path = SPEND
    acq_path = ACQ

    @classmethod
    def setUpClass(cls):
        cls.spend = read_rows(cls.spend_path)
        cls.acq = read_rows(cls.acq_path)
        cls.con = m.load_db(cls.spend_path, cls.acq_path)

    def expected_quarters(self):
        out = {}
        for r in self.acq:
            e = out.setdefault((quarter_of(r["week_start"]), r["channel"]), [0.0, 0, 0])
            e[1] += int(r["signups"])
            e[2] += int(r["subscribers"])
        for r in self.spend:
            out[(quarter_of(r["week_start"]), r["channel"])][0] += float(r["spend"])
        return out

    def expected_platforms(self):
        out = {}
        for r in self.acq:
            e = out.setdefault((quarter_of(r["week_start"]), r["platform"]), [0, 0])
            e[0] += int(r["subscribers"])
            e[1] += int(r["subscribers"]) if r["channel"] == "unattributed" else 0
        return out

    def test_quarter_sql(self):
        exp = self.expected_quarters()
        got = run_sql(self.con, m.QUARTER_SQL)
        self.assertEqual([(g["quarter"], g["channel"]) for g in got], sorted(exp),
                         "one row per quarter and channel, in order")
        for g in got:
            s, n, k = exp[(g["quarter"], g["channel"])]
            self.assertAlmostEqual(g["spend"], s, delta=0.006,
                                   msg="spend for %s %s: did a join multiply it?" % (g["quarter"], g["channel"]))
            self.assertEqual((g["signups"], g["subscribers"]), (n, k))

    def test_platform_and_weekly_sql(self):
        exp = self.expected_platforms()
        got = run_sql(self.con, m.PLATFORM_SQL)
        self.assertEqual({(g["quarter"], g["platform"]): [g["subscribers"], g["unattributed"]] for g in got},
                         {k: v for k, v in exp.items()})
        weekly = {}
        for r in self.acq:
            w = weekly.setdefault(week_of(r["week_start"]), [0.0, 0, 0, 0])
            if r["channel"] in PAID:
                w[1] += int(r["subscribers"])
            if r["platform"] == "ios":
                w[3] += int(r["subscribers"])
                w[2] += int(r["subscribers"]) if r["channel"] == "unattributed" else 0
        for r in self.spend:
            weekly[week_of(r["week_start"])][0] += float(r["spend"])
        got = run_sql(self.con, m.WEEKLY_SQL)
        self.assertEqual([g["week"] for g in got], sorted(weekly), "one row per week, 1 to 39")
        for g in got:
            s, n, u, ios = weekly[g["week"]]
            self.assertAlmostEqual(g["paid_spend"], s, delta=0.006)
            self.assertEqual(g["paid_subscribers"], n)
            self.assertAlmostEqual(g["reported_cac"], s / n, delta=0.006, msg="week %d reported_cac" % g["week"])
            self.assertAlmostEqual(g["ios_unattributed_pct"], 100.0 * u / ios, delta=0.06)

    def test_insight(self):
        q = self.expected_quarters()
        p = self.expected_platforms()

        def cac(quarter):
            return (sum(q[(quarter, c)][0] for c in PAID) / sum(q[(quarter, c)][2] for c in PAID))
        c1, c3 = cac("Q1"), cac("Q3")
        extra = 0.0
        for plat in ("android", "ios", "web"):
            subs1, un1 = p[("Q1", plat)]
            subs3, un3 = p[("Q3", plat)]
            extra += max(0.0, un3 - subs3 * un1 / subs1)
        corrected = sum(q[("Q3", c)][0] for c in PAID) / (sum(q[("Q3", c)][2] for c in PAID) + extra)
        qrows = run_sql(self.con, m.QUARTER_SQL)
        prows = run_sql(self.con, m.PLATFORM_SQL)
        d = m.decompose(qrows, prows)
        self.assertAlmostEqual(d["change_pct"], 100 * (c3 / c1 - 1), places=4, msg="reported CAC change Q1 to Q3")
        self.assertAlmostEqual(d["cac_corrected"], corrected, places=4,
                               msg="corrected CAC adds the excess unattributed subscribers back to paid")
        self.assertGreater(d["tracking_pts"], d["real_pts"], "in this data most of the reported rise is tracking")
        self.assertGreater(d["real_pts"], 0, "but a real rise is left after the correction")
        ttp = m.trial_to_paid(qrows)
        for quarter in ("Q1", "Q2", "Q3"):
            subs = sum(v[2] for k, v in q.items() if k[0] == quarter)
            sign = sum(v[1] for k, v in q.items() if k[0] == quarter)
            self.assertAlmostEqual(ttp[quarter], subs / sign, places=9)


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        data = make_data.build(seed=OTHER_SEED)
        cls.spend_path = os.path.join(cls.tmp, "spend.csv")
        cls.acq_path = os.path.join(cls.tmp, "acquisitions.csv")
        make_data.write_csv(data["spend"], make_data.SPEND_FIELDS, cls.spend_path)
        make_data.write_csv(data["acquisitions"], make_data.ACQ_FIELDS, cls.acq_path)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
