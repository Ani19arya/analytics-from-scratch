"""dbt from scratch: parse {{ ref() }}, order the models, build them, test them.

Exercise. The helpers at the top are done for you. Fill in the seven functions
marked TODO, then run: python3 test_lesson.py

Python 3.9+ standard library only; dbt is not needed.

A project is a folder of .sql files in models/, one model per file. A model
reads other models with {{ ref('name') }} and says how to build itself with
{{ config(materialized='view') }} or 'table' (view when there is no config).
models/schema.json lists the tests, the same ones a dbt schema.yml declares.
"""
import csv
import heapq
import json
import os
import re
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
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


# The runner. Your turn.

def parse_refs(sql):
    """The distinct model names inside {{ ref('...') }} in sql, sorted.

    Allow single or double quotes and any spaces inside the braces:
    {{ref('a')}}, {{ ref( "a" ) }}. A ref inside a comment still counts (dbt does the same).
    """
    raise NotImplementedError("TODO: parse_refs")


def parse_config(sql):
    """'view' or 'table' from {{ config(materialized='...') }}; 'view' when there is no config.

    Raise ValueError for any other materialization.
    """
    raise NotImplementedError("TODO: parse_config")


def compile_sql(sql):
    """The SQL SQLite can run: the config block removed, each {{ ref('x') }} replaced by x, stripped."""
    raise NotImplementedError("TODO: compile_sql")


def build_dag(models):
    """{name: set of the models it refs} for models = {name: sql}.

    Raise ValueError naming both models when a ref points at a model that does not exist.
    """
    raise NotImplementedError("TODO: build_dag")


def topo_order(dag):
    """Every model, each one after all the models it depends on.

    Use Kahn's algorithm: repeatedly take a model whose dependencies are all
    done. When several are ready at once, take the alphabetically first, so the
    order is the same on every run. If models are left that can never be ready,
    raise CycleError(those models).
    """
    raise NotImplementedError("TODO: topo_order")


def run_project(con, models):
    """Build every model in topo_order as a VIEW or TABLE (CREATE VIEW x AS ... / CREATE TABLE x AS ...).

    Drop what is there first (drop_relation), so running twice works.
    Return [(name, 'view' or 'table'), ...] in build order.
    """
    raise NotImplementedError("TODO: run_project")


def run_tests(con, tests):
    """Run each test in tests (as read_tests returns them) and return, in the same order,
    {"model", "column", "test", "failures", "status"} with status 'pass' or 'fail'.

    failures is the number of rows the test query returns, as in dbt:
    - unique: one row per non-NULL value that appears more than once,
    - not_null: one row per NULL,
    - accepted_values: one row per distinct non-NULL value not in t["values"],
    - relationships: one row per non-NULL child value with no match in t["to"].t["field"].
    """
    raise NotImplementedError("TODO: run_tests")
