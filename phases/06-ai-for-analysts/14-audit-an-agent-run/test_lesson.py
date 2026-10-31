"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Reference revenue and the correct growth are recomputed here in plain Python from the order
rows, not with SQL. Verdicts are checked against the answer key make_data.py recorded when it
planted each problem, on the committed data and on a second seed. The database file is
hashed after the audit, so an audit that writes fails.
"""
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
OTHER_SEED = 1676


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def py_revenue(orders, month):
    return round(sum(float(o["amount"]) for o in orders if o["status"] == "completed" and str(o["order_date"])[:7] == month), 2)


def py_growth(orders, a, b):
    ra, rb = py_revenue(orders, a), py_revenue(orders, b)
    return None if ra == 0 else round((rb - ra) / ra * 100, 1)


class DbCase(unittest.TestCase):
    orders = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="w6-audit-")
        cls.path = os.path.join(cls.tmp, "shop.db")
        lesson.build_db(cls.path, cls.orders)
        cls.hash = file_hash(cls.path)
        cls.conn = lesson.open_readonly(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmp, ignore_errors=True)


def sql_for(month, completed=True):
    where = "status = 'completed' AND " if completed else ""
    return "SELECT ROUND(SUM(amount), 2) FROM orders WHERE %sorder_date >= '%s-01' AND order_date < '%s-01'" % (
        where, month, lesson.next_month(month))


def trace(*steps):
    """steps: (tool, args, observation). Numbered from 1."""
    return [{"step": i, "tool": t, "args": a, "observation": o} for i, (t, a, o) in enumerate(steps, 1)]


class TestHandMade(DbCase):
    orders = [
        {"order_id": 1, "customer_id": 1, "order_date": "2026-08-03", "status": "completed", "amount": "120.00"},
        {"order_id": 2, "customer_id": 1, "order_date": "2026-08-09", "status": "cancelled", "amount": "50.00"},
        {"order_id": 3, "customer_id": 2, "order_date": "2026-09-01", "status": "completed", "amount": "80.00"},
        {"order_id": 4, "customer_id": 2, "order_date": "2026-09-30", "status": "completed", "amount": "24.00"},
    ]
    target_run = {"run_id": "T", "month_from": "2026-08", "month_to": "2026-09"}

    def audit(self, steps):
        return lesson.audit_run(self.conn, self.target_run, steps)

    def test_reference(self):
        self.assertEqual(lesson.reference_revenue(self.conn, "2026-08"), 120.0, "only completed orders count")
        self.assertEqual(lesson.reference_revenue(self.conn, "2026-09"), 104.0, "the last day of the month counts")
        self.assertEqual(lesson.reference_revenue(self.conn, "2026-12"), 0.0, "a month with no orders has revenue 0.0")
        self.assertEqual(lesson.correct_growth(self.conn, "2026-08", "2026-09"), -13.3)
        self.assertIsNone(lesson.correct_growth(self.conn, "2026-12", "2026-09"), "growth from zero is undefined: return None")

    def test_supports(self):
        self.assertTrue(lesson.supports("rows: [(3.8742,)]", 4, 0), "about 4 is supported by 3.8742 at 0 decimals")
        self.assertFalse(lesson.supports("3.8742", 4.0, 1), "4.0 written with one decimal is not 3.9")
        self.assertTrue(lesson.supports("-11.6542", 11.7, 1), "fell 11.7 is supported by -11.6542")
        self.assertFalse(lesson.supports("", 1, 0))

    def test_clean_and_precision(self):
        steps = trace(("run_sql", {"sql": sql_for("2026-08")}, "rows: [(120.0,)]"),
                      ("run_sql", {"sql": sql_for("2026-09")}, "rows: [(104.0,)]"),
                      ("calculate", {"expression": "(104.0 - 120.0) / 120.0 * 100"}, "-13.3333"),
                      ("final", {"answer": "Revenue fell about 13% from August to September."}, ""))
        got = self.audit(steps)
        self.assertEqual((got["verdict"], got["bad_step"], got["checked_steps"]), ("ok", None, [1, 2, 3]))
        self.assertEqual(got["correct"], -13.3)
        steps[3]["args"]["answer"] = "Revenue fell 13.5% from August to September."
        got = self.audit(steps)
        self.assertEqual((got["verdict"], got["bad_step"]), ("unsupported", 4), "13.5 is in no observation")

    def test_lineage_ignores_side_steps(self):
        steps = trace(("run_sql", {"sql": sql_for("2026-08", completed=False)}, "rows: [(170.0,)]"),
                      ("run_sql", {"sql": sql_for("2026-08")}, "rows: [(120.0,)]"),
                      ("run_sql", {"sql": sql_for("2026-09")}, "rows: [(104.0,)]"),
                      ("calculate", {"expression": "(104.0 - 120.0) / 120.0 * 100"}, "-13.3333"),
                      ("final", {"answer": "Revenue fell 13.3%."}, ""))
        self.assertEqual(lesson.trace_lineage(steps), {"depends_on": [2, 3, 4], "unsupported": []})
        self.assertEqual(self.audit(steps)["verdict"], "ok", "step 1 uses the wrong definition but the answer does not depend on it")

    def test_earliest_problem_wins(self):
        steps = trace(("run_sql", {"sql": sql_for("2026-08", completed=False)}, "rows: [(170.0,)]"),
                      ("run_sql", {"sql": sql_for("2026-09")}, "rows: [(104.0,)]"),
                      ("calculate", {"expression": "(104.0 - 170.0) / 104.0 * 100"}, "-63.4615"),
                      ("final", {"answer": "Revenue fell 63.5%."}, ""))
        got = self.audit(steps)
        self.assertEqual((got["verdict"], got["bad_step"]), ("wrong_definition", 1), "report the first step that went wrong")

    def test_replay_and_unsupported_input(self):
        steps = trace(("run_sql", {"sql": sql_for("2026-08")}, "rows: [(118.0,)]"),
                      ("run_sql", {"sql": sql_for("2026-09")}, "rows: [(104.0,)]"),
                      ("calculate", {"expression": "(104.0 - 118.0) / 118.0 * 100"}, "-11.8644"),
                      ("final", {"answer": "Revenue fell 11.9%."}, ""))
        self.assertEqual(self.audit(steps)["verdict"], "replay_mismatch", "rerunning step 1 gives 120.0, not the logged 118.0")
        steps = trace(("run_sql", {"sql": sql_for("2026-09")}, "rows: [(104.0,)]"),
                      ("calculate", {"expression": "(104.0 - 98.0) / 98.0 * 100"}, "6.1224"),
                      ("final", {"answer": "Revenue grew 6.1%."}, ""))
        lin = lesson.trace_lineage(steps)
        self.assertEqual(lin["unsupported"], [(2, "98.0")], "98.0 in the calculation came from nowhere (100 is a constant)")
        self.assertEqual((self.audit(steps)["verdict"], self.audit(steps)["bad_step"]), ("unsupported", 2))
        steps = trace(("run_sql", {"sql": "SELECT nonsense FROM nowhere"}, "rows: [(5,)]"), ("final", {"answer": "It is 5."}, ""))
        self.assertEqual(self.audit(steps)["verdict"], "replay_mismatch", "SQL that no longer runs cannot be replayed")

    def test_no_final_and_no_numbers(self):
        steps = trace(("run_sql", {"sql": sql_for("2026-08")}, "rows: [(100.0,)]"))
        self.assertEqual(self.audit(steps)["verdict"], "no_answer")
        self.assertEqual(self.audit([])["verdict"], "no_answer")
        steps = trace(("final", {"answer": "I could not work it out."}, ""))
        got = self.audit(steps)
        self.assertEqual((got["verdict"], got["checked_steps"]), ("ok", []), "an answer with no numbers depends on no step")
        self.assertEqual(file_hash(self.path), self.hash)


class KeyCase(DbCase):
    runs = None
    steps = None

    def check_key(self, label):
        results = lesson.audit_all(self.conn, self.runs, self.steps)
        self.assertEqual([r["run_id"] for r in results], [r["run_id"] for r in self.runs])
        for run, got in zip(self.runs, results):
            want_step = int(run["planted_step"]) if str(run["planted_step"]) else None
            want_deps = [int(x) for x in str(run["depends_on"]).split(",") if x]
            self.assertEqual(got["verdict"], run["planted_verdict"], "%s %s (%s): expected %s, got %s" % (
                label, run["run_id"], run["why"], run["planted_verdict"], got["verdict"]))
            self.assertEqual(got["bad_step"], want_step, "%s %s: the first bad step is %s" % (label, run["run_id"], want_step))
            self.assertEqual(got["checked_steps"], want_deps, "%s %s: the answer depends on steps %s" % (label, run["run_id"], want_deps))
            self.assertEqual(got["correct"], py_growth(self.orders, run["month_from"], run["month_to"]),
                             "%s %s: correct growth is completed revenue only, whole months" % (label, run["run_id"]))
        for month in ["2026-08", "2026-09", "2026-10"]:
            self.assertAlmostEqual(lesson.reference_revenue(self.conn, month), py_revenue(self.orders, month), places=2)
        self.assertEqual(file_hash(self.path), self.hash, "the audit changed the database")


class TestCommitted(KeyCase):
    orders = lesson.load_csv("orders.csv")
    runs = lesson.load_csv("runs.csv")
    steps = lesson.steps_by_run(lesson.load_csv("run_steps.csv"))

    def test_key(self):
        self.check_key("committed data")


SECOND = make_data.build(seed=OTHER_SEED)


class TestSecondDataset(KeyCase):
    orders = SECOND["orders"]
    runs = SECOND["runs"]
    steps = lesson.steps_by_run([{k: str(v) for k, v in r.items()} for r in SECOND["run_steps"]])

    def test_key(self):
        self.check_key("seed %d" % OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
