"""Tests for lesson 11: attribution models. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Every expected number is computed here in plain Python, never read from the solution.
The tests run on the committed data and on a second dataset built with another seed."""
import csv
import datetime
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 9
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load()
sys.path.insert(0, HERE)
import make_data  # noqa: E402

T = datetime.datetime(2026, 10, 1, 12, 0)


def ago(days, minutes=0):
    return T - datetime.timedelta(days=days, minutes=minutes)


def reference(folder):
    """Independent route: work on the text timestamps, convert each touch to an age in
    minutes before its purchase, and hand out credit per model directly."""
    def minutes(text):
        d = datetime.datetime.strptime(text, "%Y-%m-%d %H:%M")
        return int((d - datetime.datetime(2026, 1, 1)).total_seconds() // 60)

    touches = {}
    with open(os.path.join(folder, "touchpoints.csv"), newline="") as f:
        for r in csv.DictReader(f):
            touches.setdefault(r["user_id"], []).append((minutes(r["touch_time"]), r["channel"]))
    credit = {k: {} for k in ("first", "last", "linear", "time_decay", "linear_revenue")}
    n, revenue = 0, 0.0
    with open(os.path.join(folder, "conversions.csv"), newline="") as f:
        for r in csv.DictReader(f):
            n += 1
            rev = float(r["revenue"])
            revenue += rev
            c = minutes(r["conversion_time"])
            path = sorted((t, ch) for t, ch in touches.get(r["user_id"], []) if 0 <= c - t <= 30 * 24 * 60)
            if not path:
                for k in credit:
                    credit[k]["(none)"] = credit[k].get("(none)", 0.0) + (rev if k == "linear_revenue" else 1.0)
                continue
            credit["first"][path[0][1]] = credit["first"].get(path[0][1], 0.0) + 1.0
            credit["last"][path[-1][1]] = credit["last"].get(path[-1][1], 0.0) + 1.0
            for _, ch in path:
                credit["linear"][ch] = credit["linear"].get(ch, 0.0) + 1.0 / len(path)
                credit["linear_revenue"][ch] = credit["linear_revenue"].get(ch, 0.0) + rev / len(path)
            raw = [2.0 ** (-(c - t) / (7 * 24 * 60.0)) for t, _ in path]
            for (_, ch), w in zip(path, raw):
                credit["time_decay"][ch] = credit["time_decay"].get(ch, 0.0) + w / sum(raw)
    return credit, n, revenue


class TestSmallCases(unittest.TestCase):
    def test_parse_time(self):
        self.assertEqual(m.parse_time("2026-10-01 14:05"), datetime.datetime(2026, 10, 1, 14, 5))

    def test_each_model(self):
        path = [(ago(10), "paid_social"), (ago(3), "search"), (ago(0, 30), "email")]
        self.assertEqual(m.weights(path, "first", T), {"paid_social": 1.0})
        self.assertEqual(m.weights(path, "last", T), {"email": 1.0})
        lin = m.weights(path, "linear", T)
        for ch in ("paid_social", "search", "email"):
            self.assertAlmostEqual(lin[ch], 1 / 3)
        td = m.weights(path, "time_decay", T)
        raw = [0.5 ** (10 / 7), 0.5 ** (3 / 7), 0.5 ** ((30 / 1440) / 7)]
        self.assertAlmostEqual(td["paid_social"], raw[0] / sum(raw), places=12,
                               msg="time decay: weight 0.5 ** (days before purchase / 7), scaled to add up to 1")
        self.assertAlmostEqual(sum(td.values()), 1.0, places=12)
        self.assertGreater(td["email"], td["search"])

    def test_repeated_channel_and_half_life(self):
        path = [(ago(7), "search"), (ago(0), "search")]
        self.assertEqual(m.weights(path, "linear", T), {"search": 1.0},
                         "two touches by the same channel add up to that channel's share")
        td = m.weights([(ago(7), "a"), (ago(0), "b")], "time_decay", T)
        self.assertAlmostEqual(td["a"], 1 / 3, places=12, msg="one half-life older means half the weight: 0.5 / 1.5")
        td14 = m.weights([(ago(7), "a"), (ago(0), "b")], "time_decay", T, half_life_days=14.0)
        self.assertGreater(td14["a"], td["a"], "a longer half-life gives older touches more weight")

    def test_empty_path_and_unknown_model(self):
        for model in ("first", "last", "linear", "time_decay"):
            self.assertEqual(m.weights([], model, T), {"(none)": 1.0},
                             "a purchase with no touch still counts: credit it to '(none)'")
        with self.assertRaises(ValueError):
            m.weights([(ago(1), "search")], "u_shaped", T)

    def test_load_window_and_ties(self):
        tmp = tempfile.mkdtemp()
        try:
            with open(os.path.join(tmp, "touchpoints.csv"), "w", newline="") as f:
                f.write("user_id,touch_time,channel\n"
                        "a,2026-09-01 12:00,affiliate\n"     # exactly 30 days before: in
                        "a,2026-09-01 11:59,paid_social\n"   # 30 days and 1 minute: out
                        "a,2026-10-01 12:00,search\n"        # at the purchase time: in
                        "a,2026-10-01 12:00,email\n"         # same minute: order by channel name
                        "a,2026-10-01 12:01,paid_social\n"   # after the purchase: out
                        "b,2026-09-20 09:00,search\n")
            with open(os.path.join(tmp, "conversions.csv"), "w", newline="") as f:
                f.write("user_id,conversion_time,revenue\n"
                        "a,2026-10-01 12:00,49.00\nc,2026-09-15 08:00,29.00\n")
            purchases = m.load(os.path.join(tmp, "touchpoints.csv"), os.path.join(tmp, "conversions.csv"))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual([p["user_id"] for p in purchases], ["c", "a"], "purchases are listed oldest first")
        a = purchases[1]
        self.assertEqual([ch for _, ch in a["path"]], ["affiliate", "email", "search"],
                         "keep touches from exactly 30 days before up to the purchase minute; "
                         "drop later ones; same minute sorts by channel name")
        self.assertEqual(purchases[0]["path"], [], "a buyer with no touches has an empty path")
        self.assertAlmostEqual(a["revenue"], 49.0)
        self.assertEqual(m.attribute(purchases, "last"), {"search": 1.0, "(none)": 1.0})
        self.assertEqual(m.attribute(purchases, "first", value="revenue"), {"affiliate": 49.0, "(none)": 29.0})
        self.assertEqual(m.attribute([], "linear"), {}, "no purchases: no credit")


class OnDataMixin:
    folder = DATA

    def purchases(self):
        return m.load(os.path.join(self.folder, "touchpoints.csv"), os.path.join(self.folder, "conversions.csv"))

    def test_models_match_reference(self):
        ref, n, _ = reference(self.folder)
        purchases = self.purchases()
        self.assertEqual(len(purchases), n)
        for model in ("first", "last", "linear", "time_decay"):
            got = m.attribute(purchases, model)
            self.assertEqual(set(got), set(ref[model]), "%s: wrong set of channels" % model)
            for ch, want in ref[model].items():
                self.assertAlmostEqual(got[ch], want, places=9, msg="%s credit for %s: expected %.3f" % (model, ch, want))

    def test_credits_sum_to_conversions(self):
        _, n, revenue = reference(self.folder)
        purchases = self.purchases()
        for model in ("first", "last", "linear", "time_decay"):
            self.assertAlmostEqual(sum(m.attribute(purchases, model).values()), n, places=9,
                                   msg="%s: credits must add up to the %d purchases" % (model, n))
            self.assertAlmostEqual(sum(m.attribute(purchases, model, value="revenue").values()), revenue, places=6)

    def test_linear_revenue(self):
        ref, _, _ = reference(self.folder)
        got = m.attribute(self.purchases(), "linear", value="revenue")
        for ch, want in ref["linear_revenue"].items():
            self.assertAlmostEqual(got[ch], want, places=6)

    def test_spread(self):
        ref, _, _ = reference(self.folder)
        got = m.spread(self.purchases())
        for ch in ref["linear"]:
            vals = [ref[k].get(ch, 0.0) for k in ("first", "last", "linear", "time_decay")]
            self.assertAlmostEqual(got[ch][0], min(vals), places=9)
            self.assertAlmostEqual(got[ch][1], max(vals), places=9)


class TestOnData(OnDataMixin, unittest.TestCase):
    pass


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.folder = cls.tmp
        make_data.write_all(make_data.build(seed=OTHER_SEED), cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
