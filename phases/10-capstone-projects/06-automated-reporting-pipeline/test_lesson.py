"""Checker for capstone 10-06: the Parcelwick weekly business review pipeline.
Run: python3 test_lesson.py           (checks exercise.py, your submission)
     CHECK_SOLUTION=1 python3 test_lesson.py   (checks solution/solution.py)

It checks the parts with one right answer: the numbers, the checks that block
or warn, and the pipeline's behaviour (sends once, skips a repeat, blocks a bad
load and alerts instead, writes the same bytes every time). Every expected
number is rebuilt here in plain Python from the raw drop files, never read from
the solution. The checks run on the committed data, on a second dataset built
from another seed in a temporary folder, and on tiny hand-made drops. Nothing
here touches the network: "sending" writes .eml files to a temporary outbox.
"""
import csv
import datetime as dt
import email
import email.policy
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 13
LATEST = "2026-10-19"
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("submission", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402

with open(os.path.join(HERE, "report_config.json")) as f:
    CONFIG = json.load(f)
FIELDS = CONFIG["required_columns"]
CODES = {"D": "delivered", "F": "failed", "R": "returned"}


# ---- an independent rebuild -----------------------------------------------------------

def plus(day, n):
    return (dt.date.fromisoformat(day) + dt.timedelta(days=n)).isoformat()


def raw_rows(data_dir, up_to):
    out = []
    folder = os.path.join(data_dir, "drops")
    for name in sorted(os.listdir(folder)):
        drop = name[8:18]
        if name.startswith("parcels_") and drop <= up_to:
            with open(os.path.join(folder, name), newline="") as f:
                out += [(drop, r) for r in csv.DictReader(f)]
    return out


def latest(rows):
    best = {}
    for drop, r in sorted(rows, key=lambda x: (x[1]["outcome_date"], x[0])):
        o = r["outcome"].strip()
        o = CODES.get(o, o.lower())
        if o in ("delivered", "failed", "returned"):
            best[r["parcel_id"]] = (r, o)
    return best


def expected(data_dir, week, as_of_drop=None):
    best = latest(raw_rows(data_dir, as_of_drop or plus(week, 7)))
    end = plus(week, 6)
    mine = [(r, o) for r, o in best.values() if week <= r["outcome_date"] <= end]
    on_time = sum(1 for r, o in mine if o == "delivered" and r["outcome_date"] <= r["promised_date"])
    return {"parcels": len(mine), "delivered": sum(1 for _, o in mine if o == "delivered"),
            "on_time_pct": round(100.0 * on_time / len(mine), 2) if mine else None,
            "failed": sum(1 for _, o in mine if o == "failed"), "returned": sum(1 for _, o in mine if o == "returned"),
            "revenue_gbp": round(sum(float(r["fee_gbp"]) for r, o in mine if o == "delivered"), 2),
            "sites": sorted({r["site_id"] for r, _ in mine})}


def summary_block(body):
    out = {}
    for line in body.splitlines():
        if ": " in line and line.split(": ")[0] in ("parcels", "delivered", "on_time_pct", "failed", "returned", "revenue_gbp"):
            out.setdefault(line.split(": ")[0], line.split(": ", 1)[1].strip())
    return out


def read_eml(path):
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)
    body = msg.get_body(preferencelist=("plain",)).get_content()
    return msg, body


# ---- hand-made cases ---------------------------------------------------------------------

def write_drop(folder, name, rows, fields=FIELDS):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def row(pid, site, promised, outcome, when, fee="2.99", drop="2026-01-12", file="f.csv"):
    return {"parcel_id": pid, "site_id": site, "promised_date": promised, "outcome": outcome,
            "outcome_date": when, "fee_gbp": fee, "drop": drop, "file": file}


SITES = [{"site_id": "S1", "site_name": "One", "lockers": "10"}, {"site_id": "S2", "site_name": "Two", "lockers": "10"}]


class TestHandMade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_normalise(self):
        self.assertEqual([m.normalise_outcome(x) for x in ("D", "F", "R", " Delivered ", "returned", "x", "", None)],
                         ["delivered", "failed", "returned", "delivered", "returned", None, None, None])

    def test_read_drops(self):
        d = os.path.join(self.tmp, "drops")
        write_drop(d, "parcels_2026-01-05.csv", [row("A", "S1", "2026-01-02", "D", "2026-01-02")])
        write_drop(d, "parcels_2026-01-12.csv", [row("B", "S1", "2026-01-08", "D", "2026-01-08")])
        write_drop(d, "parcels_2026-01-12_resend.csv", [row("B", "S1", "2026-01-08", "D", "2026-01-08")])
        got = m.read_drops(d, "2026-01-05")
        self.assertEqual([(r["parcel_id"], r["drop"]) for r in got], [("A", "2026-01-05")],
                         "only drops on or before up_to; each row carries its drop date")
        self.assertEqual(len(m.read_drops(d, "2026-01-12")), 3, "a re-sent file is read too: cleaning handles it")

    def test_clean_parcels(self):
        rows = [row("A", "S1", "2026-01-06", "F", "2026-01-06", "0.00", drop="2026-01-12"),
                row("A", "S1", "2026-01-06", "delivered", "2026-01-08", drop="2026-01-12"),
                row("B", "S1", "2026-01-06", "D", "2026-01-06", drop="2026-01-12"),
                row("B", "S1", "2026-01-06", "D", "2026-01-06", "3.99", drop="2026-01-19"),
                row("C", "S1", "2026-01-06", "lost", "2026-01-07")]
        got = m.clean_parcels(rows)
        self.assertEqual(sorted(got), ["A", "B"], "a row with an unknown outcome is skipped")
        self.assertEqual((got["A"]["outcome"], got["A"]["outcome_date"]), ("delivered", "2026-01-08"),
                         "the latest outcome wins, across the old and new codes")
        self.assertEqual(got["B"]["fee_gbp"], 3.99, "same outcome date: the later drop wins")

    def test_weekly_kpis(self):
        parcels = {
            "A": {"site_id": "S1", "promised_date": "2026-01-06", "outcome": "delivered", "outcome_date": "2026-01-06", "fee_gbp": 2.0},
            "B": {"site_id": "S1", "promised_date": "2026-01-02", "outcome": "delivered", "outcome_date": "2026-01-05", "fee_gbp": 3.0},
            "C": {"site_id": "S2", "promised_date": "2026-01-10", "outcome": "failed", "outcome_date": "2026-01-11", "fee_gbp": 0.0},
            "D": {"site_id": "S2", "promised_date": "2026-01-09", "outcome": "returned", "outcome_date": "2026-01-12", "fee_gbp": 0.0},
        }
        k = m.weekly_kpis(parcels, "2026-01-05")
        self.assertEqual((k["parcels"], k["delivered"], k["on_time"], k["failed"], k["returned"]), (3, 2, 1, 1, 0),
                         "a parcel counts in the week of its latest outcome (D is resolved on Monday 12th, next week)")
        self.assertAlmostEqual(k["on_time_pct"], 33.33, msg="B was delivered late; on time is over all parcels")
        self.assertAlmostEqual(k["revenue_gbp"], 5.0)
        self.assertEqual(k["sites"]["S2"]["on_time_pct"], 0.0)
        self.assertIsNone(m.weekly_kpis({}, "2026-01-05")["on_time_pct"], "no parcels: None, not 0")

    def history(self, week, per_week=4, sites=("S1", "S2")):
        rows = []
        for i in range(1, 5):
            w = plus(week, -7 * i)
            for s in sites:
                rows += [row("%s%s%d" % (s, w, j), s, w, "D", w) for j in range(per_week)]
        return rows

    def test_validate(self):
        week = "2026-02-02"
        base = self.history(week)
        ok = base + [row("N%s%d" % (s, j), s, week, "D", week) for j in range(4) for s in ("S1", "S2")]
        self.assertEqual(m.validate(ok, SITES, week, CONFIG), [], "a normal week has no issues")
        silent = base + [row("N%d" % j, "S1", week, "D", week) for j in range(8)]
        got = m.validate(silent, SITES, week, CONFIG)
        self.assertEqual([(i["level"], i["check"]) for i in got], [("warn", "site_silent")],
                         "S2 sent nothing this week but did in each of the 4 before: a warning, not an error")
        self.assertIn("S2", got[0]["detail"])
        low = base + [row("N1", "S1", week, "D", week), row("N2", "S2", week, "D", week)]
        self.assertEqual([i["check"] for i in m.validate(low, SITES, week, CONFIG) if i["level"] == "error"], ["volume"],
                         "2 parcels against a 4-week mean of 8 is under half: block")
        self.assertEqual([i["check"] for i in m.validate(base, SITES, week, CONFIG) if i["level"] == "error"], ["empty"])
        bad = ok + [row("X", "S1", week, "lost", week), row("Y", "S9", week, "D", week)]
        got = {(i["level"], i["check"]) for i in m.validate(bad, SITES, week, CONFIG)}
        self.assertEqual(got, {("error", "outcome"), ("warn", "unknown_site")})
        no_fee = [{k: v for k, v in r.items() if k != "fee_gbp"} for r in ok]
        got = m.validate(no_fee, SITES, week, CONFIG)
        self.assertEqual([(i["level"], i["check"]) for i in got], [("error", "schema")],
                         "a missing column is one error per file and column, and nothing else is checked")
        self.assertIn("fee_gbp", got[0]["detail"])

    def test_render_report(self):
        k = {"week": "2026-01-12", "parcels": 10, "delivered": 9, "on_time": 8, "on_time_pct": 80.0, "failed": 1,
             "returned": 0, "revenue_gbp": 26.91, "sites": {"S1": {"parcels": 10, "on_time_pct": 80.0, "revenue_gbp": 26.91}}}
        prev = dict(k, week="2026-01-05", parcels=12, on_time_pct=75.0)
        body = m.render_report(k, prev, dict(prev, parcels=11), [{"level": "warn", "check": "site_silent", "detail": "S2 quiet"}])
        lines = body.splitlines()
        start = lines.index("parcels: 10")
        self.assertEqual(lines[start:start + 6], ["parcels: 10", "delivered: 9", "on_time_pct: 80.00", "failed: 1",
                                                  "returned: 0", "revenue_gbp: 26.91"], "the summary block, exactly")
        self.assertIn("Restated", body, "last week changed since it was sent: say so")
        self.assertIn("S2 quiet", body, "every warning appears in the report")
        self.assertIn("synthetic", body.lower())
        same = m.render_report(k, prev, prev, [])
        self.assertNotIn("Restated", same, "no restatement note when nothing changed")


# ---- the real data, through the whole pipeline -------------------------------------------

class OnDataMixin:
    data_dir = DATA

    def test_weekly_numbers(self):
        for week in ("2026-08-03", "2026-09-07", "2026-09-14", "2026-10-05", LATEST):
            rows = m.read_drops(os.path.join(self.data_dir, "drops"), plus(week, 7))
            k = m.weekly_kpis(m.clean_parcels(rows), week)
            e = expected(self.data_dir, week)
            for key in ("parcels", "delivered", "failed", "returned"):
                self.assertEqual(k[key], e[key], "week %s %s" % (week, key))
            self.assertAlmostEqual(k["on_time_pct"], e["on_time_pct"], delta=0.005, msg="week %s on_time_pct" % week)
            self.assertAlmostEqual(k["revenue_gbp"], e["revenue_gbp"], delta=0.005, msg="week %s revenue" % week)
            self.assertEqual(sorted(k["sites"]), e["sites"])

    def test_validate_latest(self):
        rows = m.read_drops(os.path.join(self.data_dir, "drops"), plus(LATEST, 7))
        with open(os.path.join(self.data_dir, "sites.csv"), newline="") as f:
            sites = list(csv.DictReader(f))
        got = m.validate(rows, sites, LATEST, CONFIG)
        self.assertEqual([(i["level"], i["check"]) for i in got], [("warn", "site_silent")],
                         "the latest week: no errors, one silent site")
        self.assertIn("PW05", got[0]["detail"])

    def test_pipeline(self):
        outbox = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outbox, True)
        first = m.run(self.data_dir, "2026-10-12", outbox, CONFIG)
        self.assertEqual(first["status"], "sent")
        second = m.run(self.data_dir, LATEST, outbox, CONFIG)
        self.assertEqual(second["status"], "sent")
        again = m.run(self.data_dir, LATEST, outbox, CONFIG)
        self.assertEqual(again["status"], "skipped", "running the same week twice must not send twice")
        emls = sorted(f for f in os.listdir(outbox) if f.endswith(".eml"))
        self.assertEqual(emls, ["2026-10-12_wbr.eml", "2026-10-19_wbr.eml"], "one email per week in the outbox")
        msg, body = read_eml(os.path.join(outbox, "2026-10-19_wbr.eml"))
        e = expected(self.data_dir, LATEST)
        self.assertEqual(msg["To"], ", ".join(CONFIG["to"]))
        self.assertEqual(msg["Subject"], "Parcelwick WBR, week of %s: on time %.1f%%" % (LATEST, e["on_time_pct"]))
        s = summary_block(body)
        self.assertEqual((int(s["parcels"]), float(s["on_time_pct"]), float(s["revenue_gbp"])),
                         (e["parcels"], e["on_time_pct"], e["revenue_gbp"]), "the summary block in the email")
        sent_then = expected(self.data_dir, "2026-10-12")
        now = expected(self.data_dir, "2026-10-12", as_of_drop=plus(LATEST, 7))
        if (sent_then["parcels"], sent_then["on_time_pct"]) != (now["parcels"], now["on_time_pct"]):
            self.assertIn("Restated", body, "last week moved after it was sent: the email must say so")
        with open(os.path.join(outbox, "state.json")) as f:
            self.assertEqual(sorted(json.load(f)["sent"]), ["2026-10-12", LATEST])
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other, True)
        m.run(self.data_dir, "2026-10-12", other, CONFIG)
        m.run(self.data_dir, LATEST, other, CONFIG)
        with open(os.path.join(outbox, "2026-10-19_wbr.eml"), "rb") as a, open(os.path.join(other, "2026-10-19_wbr.eml"), "rb") as b:
            self.assertEqual(a.read(), b.read(), "the same inputs must write the same email, byte for byte")


class TestOnData(OnDataMixin, unittest.TestCase):
    def test_blocked(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        data = os.path.join(tmp, "data")
        shutil.copytree(DATA, data)
        latest_file = os.path.join(data, "drops", "parcels_2026-10-26.csv")
        with open(latest_file, newline="") as f:
            rows = list(csv.DictReader(f))
        write_drop(os.path.dirname(latest_file), "parcels_2026-10-26.csv", rows, [f for f in FIELDS if f != "outcome"])
        outbox = os.path.join(tmp, "outbox")
        r = m.run(data, LATEST, outbox, CONFIG)
        self.assertEqual(r["status"], "blocked", "a drop without the outcome column must block the report")
        self.assertFalse(any(f.endswith("_wbr.eml") for f in os.listdir(outbox)), "a blocked run sends no report")
        alert = os.path.join(outbox, "alerts", "%s_blocked.eml" % LATEST)
        self.assertTrue(os.path.exists(alert), "a blocked run writes an alert to the analysts")
        msg, body = read_eml(alert)
        self.assertEqual(msg["To"], ", ".join(CONFIG["alert_to"]))
        self.assertIn("outcome", body)
        state = os.path.join(outbox, "state.json")
        if os.path.exists(state):
            with open(state) as f:
                self.assertNotIn(LATEST, json.load(f)["sent"],
                                 "a blocked week is not recorded as sent, so the next run tries again")


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so typed-in numbers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.data_dir = os.path.join(cls.tmp, "data")
        make_data.write_all(make_data.build(seed=OTHER_SEED), cls.data_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
