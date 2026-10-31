"""Lesson 04: orchestration, a tiny DAG runner. Worked answer.

A night's run, one job at a time in dependency order, starting at 05:00:
- a job whose upstream jobs all succeeded runs; a failed attempt is retried after a
  wait of RETRY_DELAY x 2 ** (attempt - 1) minutes, up to its retries
- a job with any upstream job not successful is not run: "upstream_failed"
- a rerun passes the jobs that already succeeded as done; they are not run again
Loads write one day's partition with DELETE then INSERT inside one transaction,
so running a load twice, or retrying after a crash halfway, gives the same table.
"""
import csv
import heapq
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "data")
START = 5 * 60          # 05:00, in minutes after midnight
RETRY_DELAY = 5         # minutes before the first retry; doubles each time


# Given helpers (the same in exercise.py).

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


# The runner.

def downstream(dag, job):
    """Every job that depends on job, directly or through other jobs (job itself not included)."""
    children = {n: set() for n in dag}
    for n, deps in dag.items():
        for d in deps:
            children[d].add(n)
    out, stack = set(), [job]
    while stack:
        for c in children.get(stack.pop(), ()):
            if c not in out:
                out.add(c)
                stack.append(c)
    return out


def run_dag(dag, jobs, outcome, start=START, done=()):
    """Run one night. Returns (status, log):
    status {job: "success" | "failed" | "upstream_failed"},
    log [(job, attempt, start_minute, end_minute, "ok" | "fail"), ...] in the order attempts ran."""
    status, log, now = {}, [], start
    done = set(done)
    for job in topo_order(dag):
        if job in done:
            status[job] = "success"
            continue
        if any(status[d] != "success" for d in dag[job]):
            status[job] = "upstream_failed"
            continue
        status[job] = "failed"
        for attempt in range(1, jobs[job]["retries"] + 2):
            end = now + jobs[job]["minutes"]
            ok = outcome(job, attempt)
            log.append((job, attempt, now, end, "ok" if ok else "fail"))
            now = end
            if ok:
                status[job] = "success"
                break
            if attempt <= jobs[job]["retries"]:
                now += RETRY_DELAY * 2 ** (attempt - 1)
    return status, log


def finished_at(log, job):
    """End minute of the job's successful attempt in this log, or None."""
    for j, _, _, end, result in log:
        if j == job and result == "ok":
            return end
    return None


def last_success(history, job):
    """history [(run_date, status), ...]: the latest run_date on which job succeeded, or None."""
    good = [d for d, status in history if status.get(job) == "success"]
    return max(good) if good else None


def load_partition(con, table, day, rows):
    """Replace one day's rows of table(day, order_id, amount) with rows, atomically.
    rows is any iterable of (order_id, amount); if reading it fails halfway, nothing changes."""
    with con:
        con.execute("CREATE TABLE IF NOT EXISTS %s (day TEXT, order_id TEXT, amount REAL)" % table)
        con.execute("DELETE FROM %s WHERE day = ?" % table, (day,))
        con.executemany("INSERT INTO %s VALUES (?, ?, ?)" % table, ((day, o, a) for o, a in rows))


if __name__ == "__main__":
    dag, jobs = read_jobs()
    failures = read_failures()
    history = []
    for night in sorted(read_orders()):
        status, log = run_dag(dag, jobs, outcome_for(failures, night))
        history.append((night, status))
        bad = sorted(j for j, s in status.items() if s != "success")
        email = finished_at(log, "finance_email")
        print("%s  attempts %2d  finance_email %s  not successful: %s"
              % (night, len(log), clock(email) if email else "not sent", ", ".join(bad) or "-"))
    print("dashboard data as of:", last_success(history, "dashboard_refresh"))
