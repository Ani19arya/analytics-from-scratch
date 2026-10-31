"""Tests for lesson 09: one metric, one definition: the semantic layer.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected values are computed here with plain Python sets over the raw rows, never
read from the solution. compile_metric is checked with a model the TEST owns, so it is
tested apart from your MODEL; your MODEL's active_users is then checked against the
agreed definition. Everything runs on the committed CSVs and on a second dataset from
make_data.build(seed=4097) built in memory, plus small hand-made cases: an empty
window, a NULL user_id, a staff account, a user who only received pushes.
"""
import csv
import importlib.util
import os
import sqlite3
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" \
    else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
ENGAGED = {"app_open", "workout_logged"}

TEST_MODEL = {
    "from": "events JOIN users ON users.user_id = events.user_id",
    "time": "events.event_date",
    "dimensions": {"month": "substr(events.event_date, 1, 7)", "platform": "users.platform",
                   "country": "users.country"},
    "metrics": {
        "engaged_real_users": {"label": "x", "measure": "COUNT(DISTINCT events.user_id)", "filters": [
            ["engaged", "events.event_type IN ('app_open', 'workout_logged')"],
            ["real", "users.is_internal = 0"]]},
        "workouts": {"label": "y", "measure": "COUNT(*)", "filters": [
            ["workout", "events.event_type = 'workout_logged'"]]},
    },
}


def normalise(raw):
    users = [{"user_id": int(u["user_id"]), "platform": u["platform"], "country": u["country"],
              "is_internal": int(u["is_internal"])} for u in raw["users"]]
    events = [{"event_id": int(e["event_id"]), "user_id": None if e["user_id"] in ("", None) else int(e["user_id"]),
               "event_date": e["event_date"], "event_type": e["event_type"]} for e in raw["events"]]
    return {"users": users, "events": events}


def read_committed():
    out = {}
    for t in ("users", "events"):
        with open(os.path.join(HERE, "data", t + ".csv"), newline="") as f:
            out[t] = list(csv.DictReader(f))
    return normalise(out)


def to_db(tables):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE users (user_id INTEGER, platform TEXT, country TEXT, is_internal INTEGER)")
    con.execute("CREATE TABLE events (event_id INTEGER, user_id INTEGER, event_date TEXT, event_type TEXT)")
    con.executemany("INSERT INTO users VALUES (?,?,?,?)",
                    [[u["user_id"], u["platform"], u["country"], u["is_internal"]] for u in tables["users"]])
    con.executemany("INSERT INTO events VALUES (?,?,?,?)",
                    [[e["event_id"], e["user_id"], e["event_date"], e["event_type"]] for e in tables["events"]])
    return con


# ---- plain Python references ---------------------------------------------------

def joined(tables, start, end):
    users = {u["user_id"]: u for u in tables["users"]}
    return [(e, users[e["user_id"]]) for e in tables["events"]
            if e["user_id"] in users and start <= e["event_date"] < end]


def dim_value(dim, e, u):
    return e["event_date"][:7] if dim == "month" else u[dim]


def ref_metric(tables, metric, start, end, dimensions=(), skip=()):
    rules = {"engaged": lambda e, u: e["event_type"] in ENGAGED, "real": lambda e, u: u["is_internal"] == 0,
             "workout": lambda e, u: e["event_type"] == "workout_logged"}
    names = [n for n, _ in TEST_MODEL["metrics"][metric]["filters"] if n not in skip]
    groups = {}
    for e, u in joined(tables, start, end):
        if all(rules[n](e, u) for n in names):
            key = tuple(dim_value(d, e, u) for d in dimensions)
            groups.setdefault(key, []).append(e)
    if not dimensions:
        rows = groups.get((), [])
        value = len({e["user_id"] for e in rows}) if metric == "engaged_real_users" else len(rows)
        return [(value,)]
    out = []
    for key in sorted(groups):
        rows = groups[key]
        value = len({e["user_id"] for e in rows}) if metric == "engaged_real_users" else len(rows)
        out.append(key + (value,))
    return out


def ref_active_users(tables, start, end, engaged=True, real=True):
    return len({e["user_id"] for e, u in joined(tables, start, end)
                if (not engaged or e["event_type"] in ENGAGED) and (not real or u["is_internal"] == 0)})


WINDOWS = [("2026-10-01", "2026-11-01"), ("2026-09-01", "2026-10-01"), ("2026-09-15", "2026-10-15"),
           ("2026-01-01", "2026-02-01")]
DIMS = [(), ("platform",), ("month", "country"), ("country", "platform")]


class LayerChecks:
    tables = None

    @classmethod
    def setUpClass(cls):
        cls.con = to_db(cls.tables)

    def test_compile_matches_plain_python(self):
        for metric in TEST_MODEL["metrics"]:
            for start, end in WINDOWS:
                for dims in DIMS:
                    got = lesson.query_metric(self.con, TEST_MODEL, metric, start, end, list(dims))
                    want = ref_metric(self.tables, metric, start, end, dims)
                    self.assertEqual(got, want, "%s from %s to %s by %s: expected %r, got %r. Check the half-open "
                                     "window (>= start, < end), the filters and the GROUP BY / ORDER BY"
                                     % (metric, start, end, list(dims), want[:3], got[:3]))

    def test_skip_filters(self):
        got = lesson.query_metric(self.con, TEST_MODEL, "engaged_real_users", "2026-10-01", "2026-11-01",
                                  skip_filters=["real"])
        want = ref_metric(self.tables, "engaged_real_users", "2026-10-01", "2026-11-01", skip=("real",))
        self.assertEqual(got, want, "skip_filters=['real'] must drop only that filter: expected %r" % (want,))

    def test_your_model_defines_active_users_as_agreed(self):
        for start, end in WINDOWS:
            got = lesson.query_metric(self.con, lesson.MODEL, "active_users", start, end)
            want = ref_active_users(self.tables, start, end)
            self.assertEqual(got, [(want,)], "MODEL active_users from %s to %s should be %d: real users (is_internal "
                             "= 0) with an app_open or workout_logged event, pushes do not count" % (start, end, want))

    def test_filter_bridge(self):
        start, end = "2026-10-01", "2026-11-01"
        steps = lesson.filter_bridge(self.con, lesson.MODEL, "active_users", start, end)
        names = [n for n, _ in lesson.MODEL["metrics"]["active_users"]["filters"]]
        self.assertEqual([s[0] for s in steps], ["no filters"] + names,
                         "the bridge starts at 'no filters' then adds each filter in model order")
        self.assertEqual(steps[0][1], ref_active_users(self.tables, start, end, False, False),
                         "the first step is the metric with no filters at all")
        self.assertIsNone(steps[0][2], "the first step has no change: use None")
        self.assertEqual(steps[-1][1], ref_active_users(self.tables, start, end),
                         "the last step must equal the full definition")
        for prev, step in zip(steps, steps[1:]):
            self.assertEqual(step[2], step[1] - prev[1], "step %r: change must be value minus the previous value"
                             % (step[0],))


class TestCommittedData(LayerChecks, unittest.TestCase):
    tables = read_committed()

    def test_data_has_the_traps(self):
        self.assertTrue(any(e["user_id"] is None for e in self.tables["events"]), "data should have anonymous events")
        self.assertGreater(ref_active_users(self.tables, "2026-10-01", "2026-11-01", False, False),
                           ref_active_users(self.tables, "2026-10-01", "2026-11-01", True, False),
                           "pushes should inflate the unfiltered count")


class TestSecondDataset(LayerChecks, unittest.TestCase):
    """Built in memory with another seed: hard-coded answers fail here."""
    tables = normalise(make_data.build(seed=4097))


class TestTinyEdgeCases(LayerChecks, unittest.TestCase):
    """User 1 is real and engaged, 2 only gets pushes, 3 is staff, and one anonymous app_open."""
    tables = {
        "users": [{"user_id": 1, "platform": "ios", "country": "IN", "is_internal": 0},
                  {"user_id": 2, "platform": "ios", "country": "IN", "is_internal": 0},
                  {"user_id": 3, "platform": "android", "country": "GB", "is_internal": 1}],
        "events": [{"event_id": 1, "user_id": 1, "event_date": "2026-10-01", "event_type": "app_open"},
                   {"event_id": 2, "user_id": 1, "event_date": "2026-10-31", "event_type": "workout_logged"},
                   {"event_id": 3, "user_id": 2, "event_date": "2026-10-05", "event_type": "push_received"},
                   {"event_id": 4, "user_id": 3, "event_date": "2026-10-06", "event_type": "app_open"},
                   {"event_id": 5, "user_id": None, "event_date": "2026-10-07", "event_type": "app_open"},
                   {"event_id": 6, "user_id": 1, "event_date": "2026-11-01", "event_type": "app_open"}],
    }


class TestCompileRules(unittest.TestCase):
    def test_dates_are_parameters_not_pasted(self):
        sql, params = lesson.compile_metric(TEST_MODEL, "workouts", "2026-10-01", "2026-11-01")
        self.assertNotIn("2026-10-01", sql, "bind start and end as parameters (?), do not paste them into the SQL")
        self.assertEqual(list(params), ["2026-10-01", "2026-11-01"], "params should be [start, end]")

    def test_unknown_names_are_refused(self):
        bad = [("no_such_metric", (), ()), ("workouts", ("platform; DROP TABLE users",), ()),
               ("workouts", (), ("no_such_filter",))]
        for metric, dims, skip in bad:
            with self.assertRaises(ValueError, msg="compile_metric must raise ValueError for %r %r %r: only names in "
                                   "the model may reach the SQL" % (metric, dims, skip)):
                lesson.compile_metric(TEST_MODEL, metric, "2026-10-01", "2026-11-01", list(dims), list(skip))

    def test_empty_or_reversed_window_is_refused(self):
        for start, end in (("2026-10-01", "2026-10-01"), ("2026-11-01", "2026-10-01")):
            with self.assertRaises(ValueError, msg="start must be before end"):
                lesson.compile_metric(TEST_MODEL, "workouts", start, end)

    def test_window_with_no_rows(self):
        con = to_db({"users": [], "events": []})
        self.assertEqual(lesson.query_metric(con, TEST_MODEL, "workouts", "2026-10-01", "2026-11-01"), [(0,)],
                         "no rows and no dimensions: one row with 0")
        self.assertEqual(lesson.query_metric(con, TEST_MODEL, "workouts", "2026-10-01", "2026-11-01", ["platform"]),
                         [], "no rows by platform: no rows")


class TestLabelClashes(unittest.TestCase):
    def d(self, label, measure, *sqls):
        return {"label": label, "measure": measure, "filters": [["f%d" % i, s] for i, s in enumerate(sqls)]}

    def test_cases(self):
        a, b = "users.is_internal = 0", "events.event_type = 'app_open'"
        cases = [
            ({}, []),
            ({"x": self.d("Active users", "COUNT(*)", a, b), "y": self.d("Active users", "COUNT(*)", b, a)}, []),
            ({"x": self.d("Active users", "COUNT(*)", a), "y": {"label": "Active users", "measure": "COUNT(*)",
                                                              "filters": [["other_name", a]]}}, []),
            ({"x": self.d("Active users", "COUNT(*)", a), "y": self.d("Active users", "COUNT(*)")}, ["Active users"]),
            ({"x": self.d("Revenue", "SUM(a)"), "y": self.d("Revenue", "SUM(b)"), "z": self.d("Orders", "COUNT(*)")},
             ["Revenue"]),
        ]
        for definitions, want in cases:
            self.assertEqual(lesson.label_clashes(definitions), want,
                             "label_clashes(%r) should be %r: compare the measure and the SET of filter SQL"
                             % (sorted(definitions), want))

    def test_the_two_dashboards_clash(self):
        defs = {"product": lesson.PRODUCT_DASHBOARD, "growth": lesson.GROWTH_DASHBOARD,
                "layer": lesson.MODEL["metrics"]["active_users"]}
        self.assertEqual(lesson.label_clashes(defs), ["Active users"],
                         "the product and growth dashboards both say Active users with different filters")


if __name__ == "__main__":
    unittest.main()
