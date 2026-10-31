"""Tests for lesson 08-02: dbt from scratch.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

dbt is NOT needed. The expected answers are computed here on their own:
the refs by a plain string scan (not a regex), the build order by Python's
graphlib plus a hand-written check, and every test's failure count by plain
Python over the raw rows (dedupe, fan-out and orphans counted by hand).
Your runner is checked on:
1. the project in models/ over the committed data/*.csv,
2. the same project over a second raw dataset from make_data.build(seed=2027),
   where the number of duplicates and orphans changes and one problem is gone,
   so typing out the failure counts cannot pass,
3. tiny hand-made projects and tables: an empty project, a diamond, a cycle
   with a model downstream of it, a self-reference, a ref to a missing model,
   odd quoting and spacing, no config, a bad config, and tests over NULLs.
"""
import csv
import graphlib
import importlib.util
import os
import random
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
ACCEPTED = ["delivered", "cancelled", "refunded", "pending"]


# Reference answers.

def scan_refs(sql):
    """Find ref('x') inside {{ }} by walking the string."""
    out, i = set(), 0
    while True:
        i = sql.find("{{", i)
        if i < 0:
            return sorted(out)
        j = sql.find("}}", i)
        inner = sql[i + 2:j].strip()
        if inner.startswith("ref"):
            arg = inner[3:].strip()[1:-1].strip()  # drop ( and )
            out.add(arg.strip("'\""))
        i = j + 2


def ref_order(dag):
    done, order = set(), []
    while len(order) < len(dag):
        ready = sorted(n for n in dag if n not in done and dag[n] <= done)
        if not ready:
            return order, sorted(n for n in dag if n not in done)
        order.append(ready[0])
        done.add(ready[0])
    return order, []


def ref_test_failures(tables):
    cust_rows = [(int(c["customer_id"]), c["city"].strip()) for c in tables["raw_customers"]]
    cust_count = {}
    for cid, _ in cust_rows:
        cust_count[cid] = cust_count.get(cid, 0) + 1
    orders = [dict(o, status=o["status"].strip().lower(), order_id=int(o["order_id"]),
                   customer_id=int(o["customer_id"]), amount=float(o["amount"])) for o in tables["raw_orders"]]
    order_ids = {o["order_id"] for o in orders}
    oid_count = {}
    for o in orders:
        oid_count[o["order_id"]] = oid_count.get(o["order_id"], 0) + 1
    pay_ids = {}
    for p in tables["raw_payments"]:
        pay_ids[p["payment_id"]] = pay_ids.get(p["payment_id"], 0) + 1
    fct_rows = []
    for o in orders:
        matches = [city for cid, city in cust_rows if cid == o["customer_id"]] or [None]
        for city in matches:
            fct_rows.append((o["order_id"], city, o["amount"] if o["status"] == "delivered" else None))
    fct_count = {}
    for oid, _, _ in fct_rows:
        fct_count[oid] = fct_count.get(oid, 0) + 1
    by_city = {}
    for _, city, rev in fct_rows:
        g = by_city.setdefault(city, [0, 0.0])
        if rev is not None:
            g[0] += 1
            g[1] += rev
    failures = [
        sum(1 for k in cust_count.values() if k > 1),
        0,
        sum(1 for k in oid_count.values() if k > 1),
        0,
        len({o["status"] for o in orders} - set(ACCEPTED)),
        sum(1 for k in pay_ids.values() if k > 1),
        sum(1 for p in tables["raw_payments"] if int(p["order_id"]) not in order_ids),
        sum(1 for k in fct_count.values() if k > 1),
        sum(1 for o in orders if o["customer_id"] not in cust_count),
        0,
    ]
    return failures, by_city


def committed():
    tables = {}
    for name in ("raw_orders", "raw_customers", "raw_payments"):
        with open(os.path.join(HERE, "data", name + ".csv"), newline="") as f:
            tables[name] = list(csv.DictReader(f))
    return tables


class DbtTest(unittest.TestCase):
    def call(self, fn, *args):
        try:
            return getattr(lesson, fn)(*args)
        except NotImplementedError:
            self.fail("%s is not written yet: fill it in in exercise.py" % fn)

    def project_run(self, tables, label):
        models = lesson.read_project()
        con = lesson.load_raw(sqlite3.connect(":memory:"), tables)
        built = self.call("run_project", con, models)
        names = [n for n, _ in built]
        dag = {n: set(scan_refs(sql)) for n, sql in models.items()}
        ts = graphlib.TopologicalSorter(dag)
        ts.prepare()  # raises if graphlib finds a cycle; this project has none
        self.assertEqual(sorted(names), sorted(models), "%s: run_project must build every model once" % label)
        for i, n in enumerate(names):
            for d in dag[n]:
                self.assertLess(names.index(d), i, "%s: %s was built before %s, which it refs" % (label, n, d))
        self.assertEqual(names, ref_order(dag)[0], "%s: when several models are ready, build the alphabetically first one first" % label)
        for n, kind in built:
            want = "table" if "materialized='table'" in models[n] else "view"
            self.assertEqual(kind, want, "%s: %s should be built as a %s, from its config block" % (label, n, want))
            got = con.execute("SELECT type FROM sqlite_master WHERE name = ?", (n,)).fetchone()
            self.assertEqual(got and got[0], want, "%s: %s should exist in the database as a %s" % (label, n, want))
        results = self.call("run_tests", con, lesson.read_tests())
        want_fail, by_city = ref_test_failures(tables)
        self.assertEqual(len(results), len(want_fail), "%s: run_tests must return one result per test, in order" % label)
        for r, w, t in zip(results, want_fail, lesson.read_tests()):
            self.assertEqual((r["model"], r["column"], r["test"]), (t["model"], t["column"], t["test"]), "%s: results must be in the same order as the tests" % label)
            self.assertEqual(r["failures"], w, "%s: %s on %s.%s should return %d failing rows, not %d" % (label, t["test"], t["model"], t["column"], w, r["failures"]))
            self.assertEqual(r["status"], "pass" if w == 0 else "fail", "%s: status is 'fail' exactly when failures > 0" % label)
        mart = {row[0]: (row[1], row[2]) for row in con.execute("SELECT city, delivered_orders, revenue FROM mart_revenue_by_city")}
        self.assertEqual(set(mart), set(by_city), "%s: mart_revenue_by_city has the wrong cities: check compile_sql replaced every ref" % label)
        for city, (n, rev) in by_city.items():
            self.assertEqual(mart[city][0], n, "%s: mart_revenue_by_city %s delivered_orders should be %d" % (label, city, n))
            self.assertAlmostEqual(mart[city][1], rev, 1, "%s: mart_revenue_by_city %s revenue should be %.2f" % (label, city, rev))
        again = self.call("run_project", con, models)
        self.assertEqual(again, built, "%s: running the project a second time must work and give the same order" % label)
        return results

    def test_committed_project(self):
        res = self.project_run(committed(), "committed data")
        failing = [(r["test"], r["model"]) for r in res if r["status"] == "fail"]
        self.assertEqual(len(failing), 4, "committed data: four tests should fail (duplicate customers, a new status, orphan payments, fan-out in fct_orders)")

    def test_second_dataset(self):
        self.project_run(make_data.build(SECOND_SEED), "seed %d" % SECOND_SEED)

    def test_parse_refs(self):
        cases = [
            ("SELECT 1", []),
            ("SELECT * FROM {{ ref('b') }} JOIN {{ref('a')}} USING (id) JOIN {{ ref('b') }}", ["a", "b"]),
            ('SELECT * FROM {{ ref( "x_1" ) }}', ["x_1"]),
            ("{{ config(materialized='table') }} SELECT * FROM {{ ref('y') }}", ["y"]),
        ]
        for sql, want in cases:
            self.assertEqual(self.call("parse_refs", sql), want, "parse_refs(%r) should be %r" % (sql, want))
            self.assertEqual(scan_refs(sql), want)
        for n, sql in lesson.read_project().items():
            self.assertEqual(self.call("parse_refs", sql), scan_refs(sql), "parse_refs is wrong on models/%s.sql" % n)

    def test_config_and_compile(self):
        self.assertEqual(self.call("parse_config", "SELECT 1"), "view", "no config block means a view, as in dbt")
        self.assertEqual(self.call("parse_config", "{{ config( materialized = \"table\" ) }}\nSELECT 1"), "table", "spaces and double quotes are allowed in config")
        with self.assertRaises(ValueError, msg="materialized='incremental' is not supported here: raise ValueError"):
            self.call("parse_config", "{{ config(materialized='incremental') }} SELECT 1")
        out = self.call("compile_sql", "{{ config(materialized='table') }}\nSELECT * FROM {{ ref( \"a\" ) }} JOIN {{ref('b')}}")
        self.assertEqual(" ".join(out.split()), "SELECT * FROM a JOIN b", "compile_sql must drop the config block and replace every ref with the bare name")

    def test_ordering_edge_cases(self):
        self.assertEqual(self.call("topo_order", {}), [], "an empty project has an empty build order")
        diamond = {"d": {"b", "c"}, "c": {"a"}, "b": {"a"}, "a": set()}
        self.assertEqual(self.call("topo_order", diamond), ["a", "b", "c", "d"], "diamond: a first, then b and c alphabetically, then d")
        shuffled = list(diamond.items())
        random.Random(7).shuffle(shuffled)
        self.assertEqual(self.call("topo_order", dict(shuffled)), ["a", "b", "c", "d"], "the order must not depend on the order the models were listed in")
        cyc = {"a": {"b"}, "b": {"a"}, "c": {"b"}, "z": set()}
        with self.assertRaises(lesson.CycleError, msg="a refs b and b refs a: raise CycleError") as cm:
            self.call("topo_order", cyc)
        self.assertEqual(cm.exception.nodes, ["a", "b", "c"], "CycleError should list the models that can never be built: the cycle and everything downstream of it")
        with self.assertRaises(graphlib.CycleError):
            graphlib.TopologicalSorter(cyc).prepare()
        with self.assertRaises(lesson.CycleError, msg="a model that refs itself is a cycle of one"):
            self.call("topo_order", {"a": {"a"}})
        with self.assertRaises(ValueError, msg="a ref to a model that does not exist must raise ValueError in build_dag"):
            self.call("build_dag", {"a": "SELECT * FROM {{ ref('missing') }}"})
        dag = self.call("build_dag", lesson.read_project())
        self.assertEqual({k: set(v) for k, v in dag.items()}, {n: set(scan_refs(s)) for n, s in lesson.read_project().items()},
                         "build_dag should map each model to the set of models it refs")

    def test_tests_on_tiny_tables(self):
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE p (id, kind)")
        con.executemany("INSERT INTO p VALUES (?, ?)", [(1, "a"), (2, "a"), (2, "b"), (None, None), (None, "c"), (3, "c")])
        con.execute("CREATE TABLE ch (pid)")
        con.executemany("INSERT INTO ch VALUES (?)", [(1,), (1,), (4,), (None,), (5,)])
        tests = [
            {"model": "p", "column": "id", "test": "unique"},
            {"model": "p", "column": "id", "test": "not_null"},
            {"model": "p", "column": "kind", "test": "accepted_values", "values": ["a", "b"]},
            {"model": "ch", "column": "pid", "test": "relationships", "to": "p", "field": "id"},
            {"model": "p", "column": "kind", "test": "accepted_values", "values": ["a", "b", "c"]},
        ]
        got = [r["failures"] for r in self.call("run_tests", con, tests)]
        self.assertEqual(got, [1, 2, 1, 2, 0],
                         "unique ignores NULLs (only id 2 repeats), not_null counts 2 NULLs, accepted_values counts distinct bad values ('c' once), relationships skips NULL children (4 and 5 are orphans)")
        self.assertEqual(self.call("run_tests", con, []), [], "no tests, no results")


if __name__ == "__main__":
    unittest.main(verbosity=2)
