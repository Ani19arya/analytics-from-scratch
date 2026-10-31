"""Checker for capstone 04: Shiftwren subscription and churn. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 it checks solution/solution.py instead of exercise.py.

Every expected number is rebuilt here in plain Python with a different method
(per-account timelines and binary search), never read from the solution. The
checks run on the committed data, on a second dataset built in memory with
another seed, and on tiny hand-made event logs. The forecast is also checked
against a seeded simulation of the same book.
"""
import bisect
import importlib.util
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 9
BASE = "2026-09"
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("capstone", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402

TEXT = lambda rows: [{k: str(v) for k, v in r.items()} for r in rows]  # noqa: E731


# ---- an independent rebuild ----------------------------------------------------

def mnum(month):
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def mtext(i):
    return "%04d-%02d" % (i // 12, i % 12 + 1)


def mend(month):
    days = [31, 29 if int(month[:4]) % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return "%s-%02d" % (month, days[int(month[5:7]) - 1])


class Book:
    """Per-account timelines of (effective_on, mrr, plan, type)."""

    def __init__(self, raw, loaded_by=None, fix=True):
        billing = {}
        for a in raw["accounts"]:
            billing.setdefault(a["account_id"].strip().upper(), a["billing"])
        keep = {}
        for r in sorted(raw["subscription_events"], key=lambda r: r["loaded_on"]):
            if loaded_by is None or r["loaded_on"] <= loaded_by:
                keep[r["event_id"]] = r
        self.billing = billing
        self.events = {}
        for eid, r in sorted(keep.items(), key=lambda kv: (kv[1]["effective_on"], kv[0])):
            aid = r["account_id"].strip().upper()
            amt = float(r["amount"])
            if fix and billing[aid] == "annual" and r["requested_on"] < "2026-04-01":
                amt /= 12
            self.events.setdefault(aid, []).append((r["effective_on"], amt, r["plan"], r["event_type"]))
        self.dates = {a: [e[0] for e in evs] for a, evs in self.events.items()}

    def at(self, aid, month):
        i = bisect.bisect_right(self.dates[aid], mend(month))
        return self.events[aid][i - 1] if i else None

    def mrr(self, aid, month):
        e = self.at(aid, month)
        return e[1] if e else 0.0

    def paying(self, month):
        return {a: self.mrr(a, month) for a in self.events if self.mrr(a, month) > 0}

    def total(self, month):
        return sum(self.paying(month).values())

    def term_start(self, aid, month):
        starts = [e[0] for e in self.events[aid] if e[3] in ("start", "reactivate") and e[0] <= mend(month)]
        return starts[-1]


def exp_bridge(b, month):
    prev_m = mtext(mnum(month) - 1)
    out = dict(new=0.0, reactivation=0.0, expansion=0.0, contraction=0.0, churn=0.0)
    first = min(e[0][:7] for evs in b.events.values() for e in evs)
    churned = 0
    for a in b.events:
        p, c = b.mrr(a, prev_m), b.mrr(a, month)
        if p == 0 and c > 0:
            before = any(b.mrr(a, mtext(k)) > 0 for k in range(mnum(first), mnum(month)))
            out["reactivation" if before else "new"] += c
        elif p > 0 and c == 0:
            out["churn"] += p
            churned += 1
        elif c > p:
            out["expansion"] += c - p
        else:
            out["contraction"] += p - c
    out["start_mrr"], out["end_mrr"] = b.total(prev_m), b.total(month)
    out["start_accounts"], out["churned_accounts"] = len(b.paying(prev_m)), churned
    return out


def exp_hazards(b, base, window=6):
    out = {}
    for k in range(window):
        mo = mtext(mnum(base) - k)
        pm = mtext(mnum(mo) - 1)
        for a in b.events:
            if b.billing[a] == "monthly" and b.mrr(a, pm) > 0:
                plan = b.at(a, pm)[2]
                for key in (plan, "pooled"):
                    r = out.setdefault(key, [0, 0])
                    r[0] += 1
                    r[1] += b.mrr(a, mo) == 0
    return out


def anniversary(start, month):
    k = mnum(month) - mnum(start[:7])
    return k > 0 and k % 12 == 0


def exp_renewal(b, base, window=12):
    due = ren = 0
    for k in range(window):
        mo = mtext(mnum(base) - k)
        pm = mtext(mnum(mo) - 1)
        for a in b.events:
            if b.billing[a] == "annual" and b.mrr(a, pm) > 0 and anniversary(b.term_start(a, pm), mo):
                due += 1
                ren += b.mrr(a, mo) > 0
    return due, ren


def exp_expansion(b, base, window=6):
    base_mrr = change = 0.0
    for k in range(window):
        mo = mtext(mnum(base) - k)
        pm = mtext(mnum(mo) - 1)
        for a in b.events:
            p, c = b.mrr(a, pm), b.mrr(a, mo)
            if p > 0 and c > 0:
                base_mrr += p
                change += c - p
    return change / base_mrr if base_mrr else 0.0


def exp_forecast(b, base, horizon=6, expansion=True):
    hz = exp_hazards(b, base)
    pooled = hz["pooled"][1] / hz["pooled"][0]
    due, ren = exp_renewal(b, base)
    rate = ren / due
    g = exp_expansion(b, base) if expansion else 0.0
    out = []
    for k in range(1, horizon + 1):
        tot = 0.0
        for a, v in b.paying(base).items():
            if b.billing[a] == "monthly":
                plan = b.at(a, base)[2]
                h = hz[plan][1] / hz[plan][0] if plan in hz and hz[plan][0] else pooled
                tot += v * (1 - h) ** k
            else:
                s = b.term_start(a, base)
                tot += v * (rate if any(anniversary(s, mtext(mnum(base) + j)) for j in range(1, k + 1)) else 1)
        out.append((mtext(mnum(base) + k), tot * (1 + g) ** k))
    return out


# ---- hand-made cases ------------------------------------------------------------

def ev(eid, aid, etype, plan, amount, eff, loaded=None, req=None):
    return {"event_id": eid, "account_id": aid, "event_type": etype, "plan": plan, "locations": "1",
            "amount": str(amount), "requested_on": req or eff, "effective_on": eff, "loaded_on": loaded or eff}


def acc(aid, billing):
    return {"account_id": aid, "company_name": "x", "segment": "clinic", "country": "IE",
            "billing": billing, "signup_date": "2025-01-01"}


TINY_ACCOUNTS = [acc("A", "monthly"), acc("B", "monthly"), acc("C", "annual"), acc("D", "annual"),
                 acc("E", "annual"), acc("F", "monthly")]
TINY_EVENTS = [
    ev("1", "A", "start", "starter", 100, "2026-02-10"),
    ev("2", "B", "start", "starter", 100, "2026-02-12"),
    ev("3", "A", "cancel", "starter", 0, "2026-06-01", req="2026-05-20"),
    ev("4", "C", "start", "pro", 1440, "2025-11-10"),          # annual, old definition: 120 a month
    ev("5", "D", "start", "pro", 1200, "2025-07-05"),          # 100 a month
    ev("6", "D", "cancel", "pro", 0, "2026-07-05"),            # did not renew
    ev("7", "E", "start", "pro", 1200, "2025-08-02"),          # renewed in August 2026
]


def tiny(events=None, accounts=None):
    acc_ = m.clean_accounts(accounts or TINY_ACCOUNTS)
    return m.clean_events(events or TINY_EVENTS, acc_)


class TestHandMade(unittest.TestCase):
    def test_clean(self):
        rows = [ev("1", " a ", "start", "pro", 1200, "2026-01-05", loaded="2026-01-05"),
                ev("1", "A", "start", "pro", 2400, "2026-01-05", loaded="2026-02-20"),
                ev("2", "a", "change", "business", 300, "2026-05-01")]
        got = m.clean_events(rows, m.clean_accounts([acc("A", "annual"), acc("a ", "annual")]))
        self.assertEqual([e["event_id"] for e in got], ["1", "2"], "one row per event_id, sorted by effective_on")
        self.assertEqual({e["account_id"] for e in got}, {"A"}, "ids are trimmed and upper-cased")
        self.assertAlmostEqual(got[0]["mrr"], 200, msg="keep the row loaded last; annual amounts before 2026-04-01 are / 12")
        self.assertAlmostEqual(got[1]["mrr"], 300, msg="from 2026-04-01 annual amounts are already monthly")
        early = m.clean_events(rows, m.clean_accounts([acc("A", "annual")]), loaded_by="2026-01-31")
        self.assertEqual([(e["event_id"], e["mrr"]) for e in early], [("1", 100)],
                         "loaded_by keeps only rows loaded on or before that date")

    def test_bridge(self):
        events = tiny()
        b = m.mrr_bridge(events, "2026-06")
        self.assertEqual((b["start_mrr"], b["churn"], b["end_mrr"], b["churned_accounts"], b["start_accounts"]),
                         (520, 100, 420, 1, 5), "June: A's cancel effective 1 June removes 100")
        jul = m.mrr_bridge(events, "2026-07")
        self.assertEqual((jul["churn"], jul["end_mrr"]), (100, 320), "July: D lapses at its anniversary")
        events2 = tiny(TINY_EVENTS + [ev("8", "A", "reactivate", "pro", 150, "2026-08-03"),
                                      ev("9", "B", "change", "starter", 60, "2026-08-20"),
                                      ev("10", "F", "start", "starter", 39, "2026-08-21"),
                                      ev("11", "E", "change", "business", 200, "2026-08-25")])
        aug = m.mrr_bridge(events2, "2026-08")
        self.assertEqual({k: aug[k] for k in ("new", "reactivation", "expansion", "contraction", "churn")},
                         {"new": 39, "reactivation": 150, "expansion": 100, "contraction": 40, "churn": 0},
                         "a returning account is reactivation, not new; E's change after the switch is monthly")
        self.assertIsNone(m.mrr_bridge(events, "2024-01")["logo_churn_pct"], "nobody paying: no churn rate")

    def test_retention(self):
        r = m.retention_12m(tiny(), "2026-08")
        self.assertEqual((r["base_mrr"], r["grr_pct"], r["nrr_pct"]), (200, 50.0, 50.0),
                         "base is D and E paying at the end of 2025-08; D left")
        self.assertIsNone(m.retention_12m(tiny(), "2025-12")["nrr_pct"], "an empty base gives None")

    def test_hazards_and_renewals(self):
        events = tiny()
        hz = m.monthly_hazards(events, "2026-09")
        self.assertEqual((hz["starter"]["at_risk"], hz["starter"]["churned"]), (9, 1),
                         "A is at risk April to June, B April to September; annual accounts are left out")
        self.assertNotIn("pro", hz, "no monthly pro accounts: no pro row")
        rr = m.renewal_rate(events, "2026-09")
        self.assertEqual((rr["due"], rr["renewed"]), (2, 1), "D (July) and E (August) were due; E renewed")
        self.assertIsNone(m.renewal_rate(events, "2026-04", window=2)["rate"], "nothing due: rate None")
        self.assertAlmostEqual(m.expansion_rate(events, "2026-09")["rate"], 0.0)

    def test_forecast(self):
        events = tiny()
        events = [e for e in events if e["account_id"] not in ("D", "E")]
        got = m.forecast(events, "2026-09", horizon=1)
        self.assertEqual(got[0][0], "2026-10")
        self.assertAlmostEqual(got[0][1], 100 * 8 / 9 + 120, places=2,
                               msg="B keeps (1 - 1/9) of its MRR; C pays in full until its November anniversary")
        with self.assertRaises(ValueError, msg="C renews in November, and no renewal was ever observed"):
            m.forecast(events, "2026-09", horizon=2)


# ---- the real data ----------------------------------------------------------------

class OnDataMixin:
    @classmethod
    def setUpClass(cls):
        cls.raw = m.load_raw(DATA)
        cls.setup_common()

    @classmethod
    def setup_common(cls):
        cls.accounts = m.clean_accounts(cls.raw["accounts"])
        cls.events = m.clean_events(cls.raw["subscription_events"], cls.accounts)
        cls.book = Book(cls.raw)

    def test_clean(self):
        ids = {r["event_id"] for r in self.raw["subscription_events"]}
        self.assertEqual(len(self.events), len(ids), "one event per event_id after de-duplication")
        self.assertEqual(len(self.accounts), len({r["account_id"].strip().upper() for r in self.raw["accounts"]}))

    def test_mrr_series(self):
        for k in range(mnum("2025-01"), mnum(BASE) + 1):
            mo = mtext(k)
            self.assertAlmostEqual(sum(m.mrr_by_account(self.events, mo).values()), self.book.total(mo), places=4,
                                   msg="restated MRR at the end of %s" % mo)

    def test_bridge(self):
        for k in range(12):
            mo = mtext(mnum(BASE) - k)
            got, exp = m.mrr_bridge(self.events, mo), exp_bridge(self.book, mo)
            for key, v in exp.items():
                self.assertAlmostEqual(got[key], v, places=2, msg="bridge %s, %s" % (mo, key))
            self.assertAlmostEqual(got["start_mrr"] + got["new"] + got["reactivation"] + got["expansion"]
                                   - got["contraction"] - got["churn"], got["end_mrr"], places=2,
                                   msg="the bridge must add up for %s" % mo)

    def test_retention(self):
        b = self.book
        then, now = b.paying(mtext(mnum(BASE) - 12)), b.paying(BASE)
        base = sum(then.values())
        r = m.retention_12m(self.events, BASE)
        self.assertAlmostEqual(r["nrr_pct"], round(100 * sum(now.get(a, 0) for a in then) / base, 2), places=2)
        self.assertAlmostEqual(r["grr_pct"], round(100 * sum(min(now.get(a, 0), v) for a, v in then.items()) / base, 2),
                               places=2, msg="GRR caps each account at its old MRR")

    def test_model_inputs(self):
        hz, exp = m.monthly_hazards(self.events, BASE), exp_hazards(self.book, BASE)
        self.assertEqual({k: (v["at_risk"], v["churned"]) for k, v in hz.items()}, {k: tuple(v) for k, v in exp.items()},
                         "hazards: at risk and churned by plan, monthly billing only, six months to September")
        rr = m.renewal_rate(self.events, BASE)
        self.assertEqual((rr["due"], rr["renewed"]), exp_renewal(self.book, BASE), "annual renewals due and renewed")
        self.assertAlmostEqual(m.expansion_rate(self.events, BASE)["rate"], exp_expansion(self.book, BASE), places=9)

    def test_forecast_and_backtest(self):
        for expansion in (True, False):
            got = m.forecast(self.events, BASE, expansion=expansion)
            for (gm, gv), (em, evv) in zip(got, exp_forecast(self.book, BASE, expansion=expansion)):
                self.assertEqual(gm, em)
                self.assertAlmostEqual(gv, evv, delta=0.011, msg="forecast %s (expansion=%s)" % (gm, expansion))
        bt = m.backtest(self.events, "2026-03")
        book = set(self.book.paying("2026-03"))
        for row, (em, evv) in zip(bt, exp_forecast(self.book, "2026-03")):
            actual = sum(v for a, v in self.book.paying(em).items() if a in book)
            self.assertAlmostEqual(row["actual"], actual, places=2, msg="backtest actual for %s" % em)
            self.assertAlmostEqual(row["error_pct"], 100 * (evv - actual) / actual, delta=0.01)

    def test_reconcile(self):
        r = m.reconcile(self.raw, BASE)
        reported = int(next(x["reported_mrr"] for x in self.raw["finance_close"] if x["month"] == BASE))
        self.assertEqual(r["reported"], reported)
        self.assertAlmostEqual(r["as_at_close"], reported, places=2,
                               msg="rows loaded by 2026-10-03, no definition fix, must rebuild finance's number")
        self.assertAlmostEqual(r["as_at_close"] + r["definition_fix"] + r["late_rows"], r["restated"], places=2)
        self.assertAlmostEqual(r["restated"], self.book.total(BASE), places=2)
        fixed_at_close = Book(self.raw, loaded_by="2026-10-03").total(BASE)
        self.assertAlmostEqual(r["late_rows"], self.book.total(BASE) - fixed_at_close, places=2)

    def test_story(self):
        hz = m.monthly_hazards(self.events, BASE)
        reported = float(next(x["reported_logo_churn_pct"] for x in self.raw["finance_close"] if x["month"] == BASE))
        self.assertGreater(100 * hz["starter"]["hazard"], 1.5 * reported,
                           "starter monthly churn is far above the blended rate finance reports")
        fc = m.forecast(self.events, BASE)
        self.assertGreater(fc[2][1] - fc[3][1], fc[1][1] - fc[2][1],
                           "the January 2027 renewals of the promotion cohort make the biggest monthly drop")


class TestOnData(OnDataMixin, unittest.TestCase):
    def test_forecast_matches_simulation(self):
        """The closed-form expected MRR against 400 seeded simulations of the same book."""
        b = self.book
        hz = exp_hazards(b, BASE)
        due, ren = exp_renewal(b, BASE)
        rng = random.Random(1)
        book = b.paying(BASE)
        sims = 400
        total = 0.0
        for _ in range(sims):
            for a, v in book.items():
                if b.billing[a] == "monthly":
                    h = hz[b.at(a, BASE)[2]]
                    h = h[1] / h[0]
                    alive = all(rng.random() >= h for _ in range(6))
                else:
                    s = b.term_start(a, BASE)
                    renews = any(anniversary(s, mtext(mnum(BASE) + j)) for j in range(1, 7))
                    alive = (rng.random() < ren / due) if renews else True
                total += v if alive else 0.0
        simulated = total / sims
        got = m.forecast(self.events, BASE, expansion=False)[-1][1]
        self.assertAlmostEqual(got / simulated, 1.0, delta=0.01,
                               msg="the churn-only month-6 forecast should match a simulation within 1%")


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so typed-in numbers fail."""

    @classmethod
    def setUpClass(cls):
        t = make_data.build(seed=OTHER_SEED)
        cls.raw = {k: TEXT(v) for k, v in t.items()}
        cls.setup_common()


if __name__ == "__main__":
    unittest.main()
