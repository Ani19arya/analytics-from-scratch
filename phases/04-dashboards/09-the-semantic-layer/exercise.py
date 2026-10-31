"""Lesson 09: one metric, one definition: the semantic layer. Your turn.

A tiny semantic layer: MODEL holds every metric ONCE, as data. compile_metric turns a
metric name, a date window and some dimensions into SQL. Every dashboard asks the layer
instead of writing its own SQL, so "Active users" means one thing everywhere.
load_db, query_metric, main and the two dashboard definitions are done for you.
Write the active_users filters in MODEL, then compile_metric, filter_bridge and
label_clashes. Run from this folder: python3 test_lesson.py
"""
import csv
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")

MODEL = {
    "from": "events JOIN users ON users.user_id = events.user_id",
    "time": "events.event_date",
    "dimensions": {
        "month": "substr(events.event_date, 1, 7)",
        "platform": "users.platform",
        "country": "users.country",
    },
    "metrics": {
        "active_users": {
            "label": "Active users",
            "description": "Distinct real users (not staff or test accounts) who opened the app "
                           "or logged a workout in the window. A push notification we sent does not count.",
            "measure": "COUNT(DISTINCT events.user_id)",
            # TODO: the agreed definition as a list of [name, SQL condition] pairs.
            # Read the description above and the columns of users and events.
            "filters": [],
        },
        "workouts": {
            "label": "Workouts logged",
            "description": "Workout events from real users in the window.",
            "measure": "COUNT(*)",
            "filters": [
                ["workout_event", "events.event_type = 'workout_logged'"],
                ["not_internal", "users.is_internal = 0"],
            ],
        },
    },
}

# The two dashboards Fitloop has today. Each wrote its own "Active users".
PRODUCT_DASHBOARD = {"label": "Active users", "measure": "COUNT(DISTINCT events.user_id)", "filters": []}
GROWTH_DASHBOARD = {"label": "Active users", "measure": "COUNT(DISTINCT events.user_id)",
                    "filters": [["engaged_event", "events.event_type IN ('app_open', 'workout_logged')"]]}


def load_db(data_dir=DATA):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE users (user_id INTEGER, platform TEXT, country TEXT, is_internal INTEGER)")
    con.execute("CREATE TABLE events (event_id INTEGER, user_id INTEGER, event_date TEXT, event_type TEXT)")
    for table, cols in (("users", 4), ("events", 4)):
        with open(os.path.join(data_dir, table + ".csv"), newline="") as f:
            rows = [[None if v == "" else v for v in r.values()] for r in csv.DictReader(f)]
        con.executemany("INSERT INTO %s VALUES (%s)" % (table, ",".join("?" * cols)), rows)
    return con


def compile_metric(model, metric, start, end, dimensions=(), skip_filters=()):
    """Return (sql, params) for one metric over the half-open window [start, end).

    The SELECT lists the dimensions in the order given, then the metric AS value.
    GROUP BY and ORDER BY the dimensions (none: one row). Every filter of the metric
    goes in the WHERE clause, except the ones named in skip_filters. start and end
    are bound as parameters, never pasted into the SQL. Raise ValueError for an
    unknown metric, an unknown dimension or filter name, or start >= end."""
    raise NotImplementedError("TODO: write compile_metric")


def query_metric(con, model, metric, start, end, dimensions=(), skip_filters=()):
    sql, params = compile_metric(model, metric, start, end, dimensions, skip_filters)
    return [tuple(r) for r in con.execute(sql, params).fetchall()]


def filter_bridge(con, model, metric, start, end):
    """Walk from the metric with NO filters to the full definition, adding one filter
    at a time in the order the model lists them.
    Return [(step, value, change), ...]: the first step is ("no filters", value, None),
    then one step per filter, named after it, with change = value - previous value."""
    raise NotImplementedError("TODO: write filter_bridge")


def label_clashes(definitions):
    """definitions: {source name: {"label", "measure", "filters"}}.
    Return a sorted list of labels that two or more sources define differently
    (a different measure, or a different SET of filter conditions: order does not matter,
    and the filter's name does not matter, only its SQL)."""
    raise NotImplementedError("TODO: write label_clashes")


def main():
    con = load_db()
    start, end = "2026-10-01", "2026-11-01"
    sql, params = compile_metric(MODEL, "active_users", start, end)
    print(sql, params, sep="\n")
    print("active users, October:", query_metric(con, MODEL, "active_users", start, end)[0][0])
    for step in filter_bridge(con, MODEL, "active_users", start, end):
        print(step)
    print(query_metric(con, MODEL, "active_users", start, end, dimensions=["platform"]))
    print(label_clashes({"product": PRODUCT_DASHBOARD, "growth": GROWTH_DASHBOARD,
                         "semantic layer": MODEL["metrics"]["active_users"]}))


if __name__ == "__main__":
    main()
