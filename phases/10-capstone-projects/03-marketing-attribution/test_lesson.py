"""Checker for capstone 10-03: Brambletoe attribution and budget.
Run: python3 test_lesson.py           (checks exercise.py, your submission)
     CHECK_SOLUTION=1 python3 test_lesson.py   (checks solution/solution.py)

It checks the numbers that have one right answer. Every expected value is
computed here in plain Python from the raw rows, never read from the solution.
The checks run on the committed data, on a second dataset built in memory with
another seed (so typed-in answers fail), and on tiny hand-made tables. Two
results are checked by an independent route: the holdout interval against a
seeded bootstrap, and the budget split against a brute-force grid search.
Judgement is scored with RUBRIC.md, not here.
"""
import csv
import datetime
import importlib.util
import math
import os
import random
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 21
PAID = ("paid_search", "paid_social", "display")
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


def order(oid, uid, t, revenue=1000):
    return {"order_id": oid, "user_id": uid, "order_time": t, "revenue": revenue}


def touch(uid, t, ch):
    return {"user_id": uid, "touch_time": t, "channel": ch}


# ---- an independent reference ---------------------------------------------

def ref_spend(raw):
    rows = {(r["week_start"], r["channel"]): float(r["spend"]) for r in raw}
    return {k: v * (1.15 if k[1] == "display" and k[0] < "2026-08-17" else 1.0) for k, v in rows.items()}


def ref_orders(raw):
    first = {}
    for r in sorted(raw, key=lambda r: r["loaded_at"]):
        if "2026-06-29" <= r["order_time"][:10] <= "2026-09-27":
            first.setdefault(r["order_id"], r)
    return [{"order_id": k, "user_id": v["user_id"], "order_time": v["order_time"], "revenue": int(v["revenue"])}
            for k, v in sorted(first.items())]


def ref_credit(orders, touches, model, by_week=False):
    stamp = {}
    for t in touches:
        stamp.setdefault(t["user_id"], []).append(t)
    out = {}
    for o in orders:
        ot = datetime.datetime.strptime(o["order_time"], "%Y-%m-%d %H:%M")
        path = []
        for t in stamp.get(o["user_id"], []):
            tt = datetime.datetime.strptime(t["touch_time"], "%Y-%m-%d %H:%M")
            if datetime.timedelta(0) <= ot - tt <= datetime.timedelta(days=30):
                path.append((tt, t["channel"]))
        path = [c for _, c in sorted(path)]
        n = len(path)
        if n == 0:
            share = [("(none)", 1.0)]
        elif model == "first":
            share = [(path[0], 1.0)]
        elif model == "last":
            share = [(path[-1], 1.0)]
        elif model == "linear":
            share = [(c, 1.0 / n) for c in path]
        elif n <= 2:
            share = [(c, 1.0 / n) for c in path]
        else:
            share = [(path[0], 0.4), (path[-1], 0.4)] + [(c, 0.2 / (n - 2)) for c in path[1:-1]]
        d = datetime.date.fromisoformat(o["order_time"][:10])
        week = (d - datetime.timedelta(days=d.weekday())).isoformat()
        for c, s in share:
            key = (week, c) if by_week else c
            out[key] = out.get(key, 0.0) + s
    return out


def ref_test_counts(test_users, orders):
    buyers = {o["user_id"] for o in orders if "2026-08-03" <= o["order_time"][:10] <= "2026-08-30"}
    groups = {"exposed": [], "holdout": []}
    for u in test_users:
        groups[u["grp"]].append(1 if u["user_id"] in buyers else 0)
    return groups


class TestHandMade(unittest.TestCase):
    def test_clean_spend(self):
        raw = [{"week_start": "2026-08-10", "channel": "display", "spend": "1000.00"},
               {"week_start": "2026-08-10", "channel": "display", "spend": "1000.00"},
               {"week_start": "2026-08-17", "channel": "display", "spend": "1000.00"},
               {"week_start": "2026-08-10", "channel": "paid_search", "spend": "500.00"}]
        got = m.clean_spend(raw)
        self.assertEqual(len(got), 3, "one value per week and channel: the repeated row counts once")
        self.assertAlmostEqual(got[("2026-08-10", "display")], 1150.0,
                               msg="display before the week of 17 August excludes the 15% fee: add it")
        self.assertAlmostEqual(got[("2026-08-17", "display")], 1000.0, msg="from 17 August display already includes the fee")
        self.assertAlmostEqual(got[("2026-08-10", "paid_search")], 500.0)

    def test_clean_orders(self):
        raw = [{"order_id": "A", "user_id": "u", "order_time": "2026-06-29 00:00", "revenue": "100", "loaded_at": "2026-06-29 01:00"},
               {"order_id": "A", "user_id": "u", "order_time": "2026-06-29 00:00", "revenue": "100", "loaded_at": "2026-06-29 01:30"},
               {"order_id": "B", "user_id": "v", "order_time": "2026-09-27 23:59", "revenue": "200", "loaded_at": "2026-10-10 00:00"},
               {"order_id": "C", "user_id": "w", "order_time": "2026-09-28 00:00", "revenue": "300", "loaded_at": "2026-09-28 01:00"},
               {"order_id": "D", "user_id": "x", "order_time": "2026-06-28 23:59", "revenue": "300", "loaded_at": "2026-06-29 01:00"}]
        got = m.clean_orders(raw)
        self.assertEqual([o["order_id"] for o in got], ["A", "B"],
                         "one row per order_id; Q3 runs from 29 June to 27 September by order time, however late the row loaded")
        self.assertEqual(got[1]["revenue"], 200, "revenue as an int")

    def test_attribute_window_and_models(self):
        orders = [order("1", "u", "2026-08-31 12:00"), order("2", "v", "2026-08-31 12:00"),
                  order("3", "w", "2026-08-31 12:00")]
        touches = [touch("u", "2026-08-01 12:00", "paid_social"),   # exactly 30 days before: in
                   touch("u", "2026-08-01 11:59", "display"),       # 30 days and a minute: out
                   touch("u", "2026-08-20 09:00", "email"),
                   touch("u", "2026-08-31 12:00", "paid_search"),   # same minute as the order: in
                   touch("u", "2026-08-31 12:05", "email"),         # after the order: out
                   touch("u", "2026-08-25 10:00", "display"),
                   touch("v", "2026-08-30 10:00", "display")]
        last = m.attribute(orders, touches, "last")
        self.assertEqual(last, {"(none)": 1.0, "display": 1.0, "paid_search": 1.0},
                         "a touch after the order never gets credit; w has no touch, so '(none)'")
        first = m.attribute(orders, touches, "first")
        self.assertAlmostEqual(first["paid_social"], 1.0, msg="the touch exactly 30 days before is inside the window")
        self.assertAlmostEqual(first.get("display", 0.0), 1.0, msg="the display touch 30 days and 1 minute before is outside")
        lin = m.attribute(orders, touches, "linear")
        self.assertAlmostEqual(lin["email"], 0.25, msg="u's path has 4 touches: social, email, display, search")
        self.assertAlmostEqual(sum(lin.values()), 3.0, msg="credits add up to the number of orders")
        pos = m.attribute(orders, touches, "position")
        self.assertAlmostEqual(pos["paid_social"], 0.4)
        self.assertAlmostEqual(pos["email"], 0.1, msg="position: 40% first, 40% last, 20% split over the middle")
        self.assertAlmostEqual(pos["display"], 0.1 + 1.0)
        two = m.attribute([order("9", "z", "2026-08-31 12:00")],
                          [touch("z", "2026-08-30 12:00", "email"), touch("z", "2026-08-30 13:00", "display")], "position")
        self.assertEqual(two, {"display": 0.5, "email": 0.5}, "position with two touches: half each")
        week = m.attribute(orders, touches, "last", by_week=True)
        self.assertEqual(week[("2026-08-31", "paid_search")], 1.0, "by_week keys are (Monday of the order week, channel)")
        self.assertEqual(m.attribute([], touches, "linear"), {})
        with self.assertRaises(ValueError):
            m.attribute(orders, touches, "magic")

    def test_holdout_lift(self):
        users = [{"user_id": "a", "grp": "exposed"}, {"user_id": "b", "grp": "exposed"},
                 {"user_id": "c", "grp": "holdout"}, {"user_id": "d", "grp": "holdout"},
                 {"user_id": "e", "grp": "holdout"}, {"user_id": "f", "grp": "holdout"}]
        orders = [order("1", "a", "2026-08-03 00:00"), order("2", "a", "2026-08-10 10:00"),
                  order("3", "c", "2026-08-30 23:59"), order("4", "d", "2026-08-31 00:00")]
        got = m.holdout_lift(users, orders)
        self.assertEqual((got["n_exposed"], got["n_holdout"]), (2, 4))
        self.assertAlmostEqual(got["conv_exposed"], 0.5, msg="a user with two orders converts once")
        self.assertAlmostEqual(got["conv_holdout"], 0.25, msg="d's order on 31 August is after the test")
        se = math.sqrt(0.25 / 2 + 0.1875 / 4)
        self.assertAlmostEqual(got["se"], se, msg="unpooled SE: sqrt(pe(1-pe)/ne + ph(1-ph)/nh)")
        self.assertAlmostEqual(got["incremental"], 0.25 * 2, msg="incremental = lift x exposed users")
        self.assertAlmostEqual(got["low"], 0.25 - 1.96 * se)
        self.assertIsNone(m.holdout_lift(users[:2], orders), "no holdout users: None")

    def test_calibration_factor(self):
        users = [{"user_id": "a", "grp": "exposed"}, {"user_id": "b", "grp": "exposed"},
                 {"user_id": "c", "grp": "holdout"}, {"user_id": "d", "grp": "holdout"}]
        orders = [order("1", "a", "2026-08-05 10:00"), order("2", "b", "2026-08-06 10:00"),
                  order("3", "c", "2026-08-06 10:00")]
        touches = [touch("a", "2026-08-05 09:00", "display"), touch("b", "2026-08-06 08:00", "email"),
                   touch("b", "2026-08-06 09:00", "display"), touch("c", "2026-08-06 09:00", "email")]
        self.assertAlmostEqual(m.calibration_factor(users, orders, touches), (1.0 - 0.5) * 2 / 1.5,
                               msg="incremental (0.5 x 2 = 1 order) / linear display credit on exposed orders (1 + 0.5)")
        self.assertIsNone(m.calibration_factor(users, orders, []), "no display credit: None")

    def test_fit_sqrt_response(self):
        pts = [(100.0, 20.0), (400.0, 40.0), (900.0, 60.0)]
        self.assertAlmostEqual(m.fit_sqrt_response(pts), 2.0, msg="y = 2 sqrt(x) exactly, so a = 2")
        noisy = [(100.0, 25.0), (400.0, 35.0)]
        self.assertAlmostEqual(m.fit_sqrt_response(noisy), (25 * 10 + 35 * 20) / 500.0,
                               msg="least squares through the origin: sum(y sqrt(x)) / sum(x)")
        self.assertIsNone(m.fit_sqrt_response([(0.0, 3.0)]), "no spend: None")
        self.assertIsNone(m.fit_sqrt_response([]))

    def test_allocate(self):
        wide_lo, wide_hi = {"x": 0.0, "y": 0.0}, {"x": 1e9, "y": 1e9}
        got = m.allocate({"x": 1.0, "y": 1.0}, 1000.0, wide_lo, wide_hi)
        self.assertAlmostEqual(got["x"], 500.0, places=3, msg="equal curves: equal split")
        got = m.allocate({"x": 2.0, "y": 1.0}, 1000.0, wide_lo, wide_hi)
        self.assertAlmostEqual(got["x"], 800.0, places=3, msg="unbounded optimum: spend in proportion to a squared")
        got = m.allocate({"x": 2.0, "y": 1.0}, 1000.0, {"x": 0.0, "y": 300.0}, {"x": 1e9, "y": 1e9})
        self.assertAlmostEqual(got["y"], 300.0, places=3, msg="y's lower bound binds")
        self.assertAlmostEqual(got["x"], 700.0, places=3)
        got = m.allocate({"x": 1.0, "y": -0.5}, 1000.0, {"x": 0.0, "y": 100.0}, {"x": 1e9, "y": 1e9})
        self.assertAlmostEqual(got["y"], 100.0, places=3, msg="a channel with a <= 0 gets its lower bound")
        with self.assertRaises(ValueError):
            m.allocate({"x": 1.0, "y": 1.0}, 50.0, {"x": 100.0, "y": 0.0}, {"x": 200.0, "y": 200.0})


class OnDataMixin:
    @classmethod
    def setUpClass(cls):
        cls.raw = cls.get_raw()
        cls.spend = m.clean_spend(cls.raw["spend"])
        cls.orders = m.clean_orders(cls.raw["orders"])
        cls.exp_orders = ref_orders(cls.raw["orders"])
        cls.touches = cls.raw["touchpoints"]

    def test_spend_and_orders(self):
        exp = ref_spend(self.raw["spend"])
        self.assertEqual(sorted(self.spend), sorted(exp), "one value per week and channel")
        for k, v in exp.items():
            self.assertAlmostEqual(self.spend[k], v, places=4, msg="%s %s spend including the agency fee" % k)
        self.assertEqual([o["order_id"] for o in self.orders], [o["order_id"] for o in self.exp_orders],
                         "Q3 orders, one per order_id")

    def test_attribution_all_models(self):
        n = len(self.exp_orders)
        for model in ("first", "last", "linear", "position"):
            exp = ref_credit(self.exp_orders, self.touches, model)
            got = m.attribute(self.orders, self.touches, model)
            self.assertEqual(sorted(got), sorted(exp), model + ": channels with credit")
            for c in exp:
                self.assertAlmostEqual(got[c], exp[c], places=6, msg="%s credit for %s" % (model, c))
            self.assertAlmostEqual(sum(got.values()), n, places=6, msg=model + ": credits add up to orders")

    def test_holdout_against_bootstrap(self):
        groups = ref_test_counts(self.raw["display_test"], self.exp_orders)
        e, h = groups["exposed"], groups["holdout"]
        got = m.holdout_lift(self.raw["display_test"], self.orders)
        self.assertEqual((got["n_exposed"], got["n_holdout"]), (len(e), len(h)))
        self.assertAlmostEqual(got["lift"], sum(e) / len(e) - sum(h) / len(h), places=9)
        rng = random.Random(77)
        diffs = []
        for _ in range(1000):
            diffs.append(sum(rng.choices(e, k=len(e))) / len(e) - sum(rng.choices(h, k=len(h))) / len(h))
        mean = sum(diffs) / len(diffs)
        boot = math.sqrt(sum((d - mean) ** 2 for d in diffs) / (len(diffs) - 1))
        self.assertLess(abs(got["se"] - boot) / boot, 0.1,
                        "the SE should be within 10%% of a bootstrap SE (%.4f); got %.4f" % (boot, got["se"]))

    def test_plan_against_grid_search(self):
        p = m.plan(self.spend, self.orders, self.touches, self.raw["display_test"])
        groups = ref_test_counts(self.raw["display_test"], self.exp_orders)
        incremental = (sum(groups["exposed"]) / len(groups["exposed"]) -
                       sum(groups["holdout"]) / len(groups["holdout"])) * len(groups["exposed"])
        exposed = {u["user_id"] for u in self.raw["display_test"] if u["grp"] == "exposed"}
        window = [o for o in self.exp_orders if o["user_id"] in exposed and "2026-08-03" <= o["order_time"][:10] <= "2026-08-30"]
        cal = incremental / ref_credit(window, self.touches, "linear")["display"]
        self.assertAlmostEqual(p["calibration"], cal, places=9, msg="calibration factor from the display test")
        spend = ref_spend(self.raw["spend"])
        weekly = ref_credit(self.exp_orders, self.touches, "linear", by_week=True)
        weeks = sorted({w for w, _ in spend})
        a, cur = {}, {}
        for c in PAID:
            xs = [spend.get((w, c), 0.0) for w in weeks]
            ys = [weekly.get((w, c), 0.0) * (cal if c == "display" else 1.0) for w in weeks]
            a[c] = sum(y * math.sqrt(x) for x, y in zip(xs, ys)) / sum(xs)
            cur[c] = sum(xs)
            self.assertAlmostEqual(p["a"][c], a[c], places=9, msg=c + ": fitted response a")
            self.assertAlmostEqual(p["current"][c], cur[c], places=4, msg=c + ": current quarter spend")
        budget = sum(cur.values())
        self.assertAlmostEqual(sum(p["proposed"].values()), budget, delta=1.0, msg="the proposal spends the same budget")

        def value(s):
            return sum(a[c] * math.sqrt(s[c] / 13.0) * 13.0 for c in PAID)

        best = -1.0
        steps = 60
        for i in range(steps + 1):
            s1 = cur["paid_search"] * (0.5 + i / steps)
            for j in range(steps + 1):
                s2 = cur["paid_social"] * (0.5 + j / steps)
                s3 = budget - s1 - s2
                if 0.5 * cur["display"] - 1e-6 <= s3 <= 1.5 * cur["display"] + 1e-6:
                    best = max(best, value({"paid_search": s1, "paid_social": s2, "display": s3}))
        self.assertGreaterEqual(value(p["proposed"]), best - 1e-6, "no allocation on a brute-force grid beats yours")
        self.assertAlmostEqual(p["proposed_conversions"], value(p["proposed"]), places=6)
        self.assertAlmostEqual(p["current_conversions"], value(cur), places=6)
        for c in PAID:
            self.assertTrue(0.5 * cur[c] - 1 <= p["proposed"][c] <= 1.5 * cur[c] + 1, c + ": within 50% of today")
        self.assertLess(cal, 1.0, "the planted story: display gets more credit than the extra orders it brings")
        self.assertLess(p["proposed"]["display"], cur["display"], "the planted story: money moves out of display")


class TestOnData(OnDataMixin, unittest.TestCase):
    @staticmethod
    def get_raw():
        return {name: read_rows(name + ".csv") for name in ("spend", "touchpoints", "orders", "display_test")}


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @staticmethod
    def get_raw():
        return make_data.build(seed=OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
