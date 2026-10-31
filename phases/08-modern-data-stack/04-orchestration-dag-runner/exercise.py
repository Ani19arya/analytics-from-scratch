"""Lesson 04: orchestration, a tiny DAG runner. Your turn.

Goal: run the nightly DAG the way a scheduler does (dependency order, retries with
backoff, skip what sits below a failure, rerun only what did not succeed) and make
the loads safe to run twice. The rules are in "The idea" in the README.
Standard library only. The helpers are done; write the five functions marked TODO,
then run: python3 test_lesson.py
"""
import csv
import heapq
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
START = 5 * 60          # 05:00, in minutes after midnight
RETRY_DELAY = 5         # minutes before the first retry; doubles each time


# Given helpers.

class CycleError(Exception):
    pass


def read_jobs(folder=DATA):
    """(dag, jobs): dag {job: set of upstream jobs}, jobs {job: {"minutes": int, "retries": int}}."""
    dag, jobs = {}, {}
    with open(os.path.join(folder, "jobs.csv"), newline="") as f:
        for r in csv.DictReader(f):
            dag[r["job"]] = set(r["depends_on"].split())
            jobs[r["job"]] = {"minutes": int(r["minutes"]), "retries": int(r["retries"])}
    return dag, jobs


def read_failures(folder=DATA):
    """{run_date: set of (job, attempt) that failed}."""
    out = {}
    with open(os.path.join(folder, "failures.csv"), newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["run_date"], set()).add((r["job"], int(r["attempt"])))
    return out


def read_orders(folder=DATA):
    """{order_date: [(order_id, amount), ...]} in file order."""
    out = {}
    with open(os.path.join(folder, "orders.csv"), newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["order_date"], []).append((r["order_id"], float(r["amount"])))
    return out


def outcome_for(failures, run_date):
    """A function (job, attempt) -> True when that attempt succeeds on that night."""
    failed = failures.get(run_date, set())
    return lambda job, attempt: (job, attempt) not in failed


def topo_order(dag):
    """Kahn's algorithm from lesson 02; ties go alphabetically. CycleError on a cycle."""
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
        raise CycleError(sorted(n for n in dag if n not in order))
    return order


def clock(minute):
    """325 -> '05:25'."""
    return "%02d:%02d" % (minute // 60, minute % 60)


# Your turn.

def downstream(dag, job):
    """Every job that depends on job, directly or through other jobs (job itself not included)."""
    # TODO
    raise NotImplementedError


def run_dag(dag, jobs, outcome, start=START, done=()):
    """Run one night. Returns (status, log):
    status {job: "success" | "failed" | "upstream_failed"},
    log [(job, attempt, start_minute, end_minute, "ok" | "fail"), ...] in the order attempts ran."""
    # TODO
    raise NotImplementedError


def finished_at(log, job):
    """End minute of the job's successful attempt in this log, or None."""
    # TODO
    raise NotImplementedError


def last_success(history, job):
    """history [(run_date, status), ...]: the latest run_date on which job succeeded, or None."""
    # TODO
    raise NotImplementedError


def load_partition(con, table, day, rows):
    """Replace one day's rows of table(day, order_id, amount) with rows, atomically.
    rows is any iterable of (order_id, amount); if reading it fails halfway, nothing changes."""
    # TODO
    raise NotImplementedError
