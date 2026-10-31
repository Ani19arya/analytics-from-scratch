"""Lesson 08-02 solution: a tiny dbt. Parse refs, order the models, build them, test them."""
import csv
import heapq
import json
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
MODELS = os.path.join(HERE, "models")
RAW_TABLES = ["raw_orders", "raw_customers", "raw_payments"]


class CycleError(Exception):
    """The models cannot be ordered. .nodes is the sorted list of models left over."""

    def __init__(self, nodes):
        self.nodes = sorted(nodes)
        super().__init__("dependency cycle among: " + ", ".join(self.nodes))


# Given helpers.

def read_csv_tables(data_dir=DATA):
    tables = {}
    for name in RAW_TABLES:
        with open(os.path.join(data_dir, name + ".csv"), newline="") as f:
            tables[name] = list(csv.DictReader(f))
    return tables


def load_raw(con, tables=None):
    """Create each raw table with the CSV's columns and insert the rows as text."""
    tables = read_csv_tables() if tables is None else tables
    for name in RAW_TABLES:
        rows = tables.get(name, [])
        cols = list(rows[0].keys()) if rows else ["id"]
        con.execute("DROP TABLE IF EXISTS %s" % name)
        con.execute("CREATE TABLE %s (%s)" % (name, ", ".join(cols)))
        con.executemany("INSERT INTO %s VALUES (%s)" % (name, ", ".join("?" * len(cols))),
                        [[r[c] for c in cols] for r in rows])
    return con


def read_project(models_dir=MODELS):
    """{model_name: sql_text} for every .sql file in models/."""
    out = {}
    for fname in sorted(os.listdir(models_dir)):
        if fname.endswith(".sql"):
            with open(os.path.join(models_dir, fname)) as f:
                out[fname[:-4]] = f.read()
    return out


def read_tests(path=os.path.join(MODELS, "schema.json")):
    with open(path) as f:
        return json.load(f)["tests"]


def drop_relation(con, name):
    """Drop a table or a view called name, whichever it is."""
    row = con.execute("SELECT type FROM sqlite_master WHERE name = ?", (name,)).fetchone()
    if row:
        con.execute("DROP %s %s" % (row[0].upper(), name))


# The runner.

REF = re.compile(r"""\{\{\s*ref\(\s*['"]([A-Za-z_][A-Za-z0-9_]*)['"]\s*\)\s*\}\}""")
CONFIG = re.compile(r"""\{\{\s*config\((.*?)\)\s*\}\}""", re.S)
MATERIALIZED = re.compile(r"""materialized\s*=\s*['"](\w+)['"]""")


def parse_refs(sql):
    return sorted(set(REF.findall(sql)))


def parse_config(sql):
    m = CONFIG.search(sql)
    if m:
        mm = MATERIALIZED.search(m.group(1))
        if mm:
            if mm.group(1) not in ("view", "table"):
                raise ValueError("materialized must be view or table, not %r" % mm.group(1))
            return mm.group(1)
    return "view"


def compile_sql(sql):
    return REF.sub(lambda m: m.group(1), CONFIG.sub("", sql)).strip()


def build_dag(models):
    dag = {}
    for name, sql in models.items():
        deps = parse_refs(sql)
        for d in deps:
            if d not in models:
                raise ValueError("model %s refers to %s, which does not exist" % (name, d))
        dag[name] = set(deps)
    return dag


def topo_order(dag):
    """Kahn's algorithm. Among models that are ready at the same time, the alphabetically first goes first."""
    waiting = {n: len(deps) for n, deps in dag.items()}
    children = {n: [] for n in dag}
    for n, deps in dag.items():
        for d in deps:
            children[d].append(n)
    ready = [n for n, k in waiting.items() if k == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        n = heapq.heappop(ready)
        order.append(n)
        for c in children[n]:
            waiting[c] -= 1
            if waiting[c] == 0:
                heapq.heappush(ready, c)
    if len(order) < len(dag):
        raise CycleError([n for n in dag if n not in order])
    return order


def run_project(con, models):
    built = []
    for name in topo_order(build_dag(models)):
        kind = parse_config(models[name])
        drop_relation(con, name)
        con.execute("CREATE %s %s AS %s" % (kind.upper(), name, compile_sql(models[name])))
        built.append((name, kind))
    return built


def test_sql(t):
    m, c = t["model"], t["column"]
    if t["test"] == "unique":
        return "SELECT %s FROM %s WHERE %s IS NOT NULL GROUP BY %s HAVING COUNT(*) > 1" % (c, m, c, c)
    if t["test"] == "not_null":
        return "SELECT * FROM %s WHERE %s IS NULL" % (m, c)
    if t["test"] == "accepted_values":
        vals = ", ".join("'%s'" % v.replace("'", "''") for v in t["values"])
        return "SELECT %s FROM %s WHERE %s NOT IN (%s) GROUP BY %s" % (c, m, c, vals, c)
    if t["test"] == "relationships":
        return ("SELECT child.%s FROM %s AS child LEFT JOIN %s AS parent ON parent.%s = child.%s "
                "WHERE child.%s IS NOT NULL AND parent.%s IS NULL" % (c, m, t["to"], t["field"], c, c, t["field"]))
    raise ValueError("unknown test %r" % t["test"])


def run_tests(con, tests):
    results = []
    for t in tests:
        n = len(con.execute(test_sql(t)).fetchall())
        results.append({"model": t["model"], "column": t["column"], "test": t["test"],
                        "failures": n, "status": "pass" if n == 0 else "fail"})
    return results


if __name__ == "__main__":
    con = load_raw(sqlite3.connect(":memory:"))
    for name, kind in run_project(con, read_project()):
        print("built", kind.ljust(5), name)
    for r in run_tests(con, read_tests()):
        print(r["status"].upper().ljust(4), r["failures"], r["test"], r["model"] + "." + r["column"])
