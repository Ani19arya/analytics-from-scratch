"""Tests for lesson 04: orchestration, a tiny DAG runner. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected statuses and timings are computed here independently: statuses by recursion
over each job's upstream jobs, timings by counting attempts and backoff waits per job.
The tests run on the committed data and on a second dataset built with another seed."""
import csv
import importlib.util
import os
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 9
START = 300
DELAY = 5
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")


def load_module():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load_module()
sys.path.insert(0, HERE)
import make_data  # noqa: E402


def read_csv(folder, name):
    with open(os.path.join(folder, name + ".csv"), newline="") as f:
        return list(csv.DictReader(f))


def tables_from_rows(tables):
    dag = {r["job"]: set(r["depends_on"].split()) for r in tables["jobs"]}
    jobs = {r["job"]: {"minutes": int(r["minutes"]), "retries": int(r["retries"])} for r in tables["jobs"]}
    failed = {}
    for r in tables["failures"]:
        failed.setdefault(r["run_date"], set()).add((r["job"], int(r["attempt"])))
    orders = {}
    for r in tables["orders"]:
        orders.setdefault(r["order_date"], []).append((r["order_id"], float(r["amount"])))
    return dag, jobs, failed, orders


def ref_order(dag):
    order, left = [], set(dag)
    while left:
        ready = sorted(j for j in left if dag[j] <= set(order))
        order.append(ready[0])
        left.remove(ready[0])
    return order


def ref_run(dag, jobs, failed, start=START, done=()):
    """Statuses by recursion, then timings job by job."""
    memo = {}

    def attempts_needed(job):
        for k in range(1, jobs[job]["retries"] + 2):
            if (job, k) not in failed:
                return k, True
        return jobs[job]["retries"] + 1, False

    def status(job):
        if job not in memo:
            if job in done:
                memo[job] = "success"
            elif all(status(d) == "success" for d in dag[job]):
                memo[job] = "success" if attempts_needed(job)[1] else "failed"
            else:
                memo[job] = "upstream_failed"
        return memo[job]

    statuses = {j: status(j) for j in dag}
    log, now = [], start
    for job in ref_order(dag):
        if job in done or statuses[job] == "upstream_failed":
            continue
        n, ok = attempts_needed(job)
        for k in range(1, n + 1):
            result = "ok" if (ok and k == n) else "fail"
            log.append((job, k, now, now + jobs[job]["minutes"], result))
            now += jobs[job]["minutes"]
            if result == "fail" and k <= jobs[job]["retries"]:
                now += DELAY * 2 ** (k - 1)
    return statuses, log


def never_fails(job, attempt):
    return True


def failing(pairs):
    pairs = set(pairs)
    return lambda job, attempt: (job, attempt) not in pairs


DIAMOND = {"a": set(), "b": {"a"}, "c": {"a"}, "d": {"b", "c"}, "e": set()}


def ten(retries=1):
    return {j: {"minutes": 10, "retries": retries} for j in DIAMOND}


class TestSmallCases(unittest.TestCase):
    def test_downstream(self):
        self.assertEqual(m.downstream(DIAMOND, "a"), {"b", "c", "d"}, "everything below a, through b and c")
        self.assertEqual(m.downstream(DIAMOND, "b"), {"d"})
        self.assertEqual(m.downstream(DIAMOND, "d"), set(), "a last job blocks nothing")
        self.assertEqual(m.downstream(DIAMOND, "e"), set())

    def test_clean_night(self):
        status, log = m.run_dag(DIAMOND, ten(), never_fails, start=0)
        self.assertEqual(status, {j: "success" for j in DIAMOND})
        self.assertEqual([(j, a, s, e) for j, a, s, e, _ in log],
                         [("a", 1, 0, 10), ("b", 1, 10, 20), ("c", 1, 20, 30), ("d", 1, 30, 40), ("e", 1, 40, 50)],
                         "one job at a time, in dependency order, ties alphabetical")

    def test_failure_skips_downstream_only(self):
        status, log = m.run_dag(DIAMOND, ten(), failing([("b", 1), ("b", 2)]), start=0)
        self.assertEqual(status, {"a": "success", "b": "failed", "c": "success", "d": "upstream_failed",
                                  "e": "success"},
                         "d sits below the failed b and is skipped; c and e do not depend on b and still run")
        self.assertEqual(log[1:3], [("b", 1, 10, 20, "fail"), ("b", 2, 25, 35, "fail")],
                         "b fails, waits 5 minutes, fails again; with 1 retry it stops there")
        self.assertEqual(log[3], ("c", 1, 35, 45, "ok"), "no wait after the last attempt")
        self.assertNotIn("d", [x[0] for x in log], "an upstream_failed job never starts")

    def test_backoff(self):
        status, log = m.run_dag({"x": set()}, {"x": {"minutes": 10, "retries": 2}},
                                failing([("x", 1), ("x", 2)]), start=0)
        self.assertEqual(status, {"x": "success"})
        self.assertEqual(log, [("x", 1, 0, 10, "fail"), ("x", 2, 15, 25, "fail"), ("x", 3, 35, 45, "ok")],
                         "the waits double: 5 minutes, then 10")
        self.assertEqual(m.finished_at(log, "x"), 45)
        status, log = m.run_dag({"x": set()}, {"x": {"minutes": 3, "retries": 0}}, failing([("x", 1)]), start=0)
        self.assertEqual((status, len(log)), ({"x": "failed"}, 1), "retries 0 means one attempt only")
        self.assertIsNone(m.finished_at(log, "x"), "a job that never succeeded has no finish time")

    def test_rerun(self):
        status, log = m.run_dag(DIAMOND, ten(), never_fails, start=540, done={"a", "c", "e"})
        self.assertEqual(status, {j: "success" for j in DIAMOND})
        self.assertEqual([(j, s) for j, _, s, _, _ in log], [("b", 540), ("d", 550)],
                         "a rerun runs only the jobs that are not done, and done jobs count as success upstream")

    def test_cycle(self):
        with self.assertRaises(m.CycleError):
            m.run_dag({"a": {"b"}, "b": {"a"}}, {"a": {"minutes": 1, "retries": 0},
                                                 "b": {"minutes": 1, "retries": 0}}, never_fails)

    def test_last_success(self):
        history = [("2026-10-12", {"x": "success"}), ("2026-10-13", {"x": "success"}),
                   ("2026-10-14", {"x": "upstream_failed"})]
        self.assertEqual(m.last_success(history, "x"), "2026-10-13")
        self.assertIsNone(m.last_success(history, "y"))
        self.assertIsNone(m.last_success([], "x"))

    def test_load_partition_idempotent_and_atomic(self):
        con = sqlite3.connect(":memory:")
        m.load_partition(con, "raw", "2026-10-13", [("1", 10.0), ("2", 20.0)])
        m.load_partition(con, "raw", "2026-10-14", [("3", 5.0)])
        m.load_partition(con, "raw", "2026-10-14", [("3", 5.0)])
        self.assertEqual(con.execute("SELECT day, COUNT(*), SUM(amount) FROM raw GROUP BY day ORDER BY day").fetchall(),
                         [("2026-10-13", 2, 30.0), ("2026-10-14", 1, 5.0)],
                         "loading the same day twice must not double it, and other days stay as they were")

        def crashes():
            yield ("3", 5.0)
            yield ("4", 6.0)
            raise IOError("connection reset")
        with self.assertRaises(IOError):
            m.load_partition(con, "raw", "2026-10-14", crashes())
        self.assertEqual(con.execute("SELECT COUNT(*), SUM(amount) FROM raw WHERE day = '2026-10-14'").fetchone(),
                         (1, 5.0), "a load that crashes halfway must leave the day exactly as it was")
        m.load_partition(con, "raw", "2026-10-14", [])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM raw WHERE day = '2026-10-14'").fetchone(), (0,),
                         "loading an empty day leaves it empty")


class OnDataMixin:
    tables = None

    def test_every_night(self):
        dag, jobs, failed, _ = tables_from_rows(self.tables)
        for night in sorted({r["order_date"] for r in self.tables["orders"]}):
            fails = failed.get(night, set())
            want = ref_run(dag, jobs, fails)
            got = m.run_dag(dag, jobs, lambda j, a: (j, a) not in fails)
            self.assertEqual(got[0], want[0], "%s: statuses differ" % night)
            self.assertEqual(got[1], want[1], "%s: attempts or their times differ" % night)

    def test_failed_night_and_rerun(self):
        dag, jobs, failed, _ = tables_from_rows(self.tables)
        night = "2026-10-14"
        status, _ = m.run_dag(dag, jobs, lambda j, a: (j, a) not in failed[night])
        blocked = {j for j, s in status.items() if s != "success"}
        self.assertEqual(blocked, {"extract_payments"} | m.downstream(dag, "extract_payments"))
        self.assertEqual(blocked - {"extract_payments"}, {j for j, s in status.items() if s == "upstream_failed"})
        done = {j for j, s in status.items() if s == "success"}
        status2, log2 = m.run_dag(dag, jobs, never_fails, start=540, done=done)
        self.assertEqual(status2, {j: "success" for j in dag})
        self.assertEqual({x[0] for x in log2}, blocked, "the 09:00 rerun runs only what did not succeed at 05:00")
        self.assertEqual(log2, ref_run(dag, jobs, set(), 540, done)[1])

    def test_loads(self):
        _, _, _, orders = tables_from_rows(self.tables)
        con = sqlite3.connect(":memory:")
        for day in sorted(orders):
            m.load_partition(con, "raw_orders", day, orders[day])
            m.load_partition(con, "raw_orders", day, orders[day])
        n = sum(len(v) for v in orders.values())
        total = round(sum(a for v in orders.values() for _, a in v), 2)
        got = con.execute("SELECT COUNT(*), ROUND(SUM(amount), 2) FROM raw_orders").fetchone()
        self.assertEqual(got, (n, total), "every night loaded twice must equal every night loaded once")


class TestOnData(OnDataMixin, unittest.TestCase):
    tables = {name: read_csv(DATA, name) for name in ("jobs", "failures", "orders")}


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""
    tables = make_data.build(seed=OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
