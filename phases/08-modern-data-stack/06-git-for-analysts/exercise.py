"""Git for analysts: answer who changed the revenue query, and undo it, from a recorded history.

Exercise. The helpers at the top are done for you. Fill in the six functions
marked TODO, then run: python3 test_lesson.py

Python 3.9+ standard library only; git is not needed.

A commit is a saved snapshot of the files, with an author, a time, a message
and a parent (the commit before it). The history is in data/:
- commits.csv: commit_id, parent_id, author, committed_at, message (oldest first)
- file_versions.csv: the full text of each file a commit created or changed
"""
import csv
import difflib
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


class RevertConflict(Exception):
    """The change cannot be undone cleanly: the lines it touched were changed again later."""


# Given helpers. You do not need to change these.

def load_history(data_dir=DATA):
    """Return (commits, versions).

    commits:  list of dicts, oldest first, parent_id None for the first commit.
    versions: {(commit_id, path): text} for every file a commit created or changed.
    """
    with open(os.path.join(data_dir, "commits.csv"), newline="") as f:
        commits = [dict(r, parent_id=r["parent_id"] or None) for r in csv.DictReader(f)]
    lines = {}
    with open(os.path.join(data_dir, "file_versions.csv"), newline="") as f:
        for r in csv.DictReader(f):
            lines.setdefault((r["commit_id"], r["path"]), []).append((int(r["line_no"]), r["line"]))
    versions = {k: "\n".join(text for _, text in sorted(v)) + "\n" for k, v in lines.items()}
    return commits, versions


def load_orders(data_dir=DATA):
    with open(os.path.join(data_dir, "orders.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["amount"] = float(r["amount"])
        r["discount"] = float(r["discount"])
        r["is_test"] = int(r["is_test"])
    return rows


def run_revenue(sql, orders, month):
    """Run one version of the revenue query on the orders and return the revenue for month ('YYYY-MM').

    The query returns (month, revenue) rows. Returns None if sql is None or
    the month has no row.
    """
    if sql is None:
        return None
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE orders (order_id, order_date, status, amount, discount, is_test)")
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
                    [(o["order_id"], o["order_date"], o["status"], o["amount"], o["discount"], o["is_test"]) for o in orders])
    for row in con.execute(sql).fetchall():
        if row[0] == month:
            return row[1]
    return None


def diff_opcodes(old_lines, new_lines):
    """How to turn old_lines into new_lines, as difflib opcodes.

    Each item is (tag, i1, i2, j1, j2): old_lines[i1:i2] became new_lines[j1:j2].
    tag is 'equal', 'replace', 'delete' (only old lines) or 'insert' (only new lines).
    """
    return difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False).get_opcodes()


# Your turn.

def log(commits, head):
    """The commits from head back to the first commit, newest first, following parent_id.

    Returns a list of commit dicts. The first commit has parent_id None.
    """
    # TODO: start at head, look the commit up by its id, then go to its parent until there is none.
    raise NotImplementedError


def file_at(commits, versions, commit_id, path):
    """The text of path as it was at commit_id, or None if the file did not exist yet.

    versions only holds the files a commit created or changed. A commit that did
    not touch the file keeps the version from its parent.
    """
    # TODO: walk log(commits, commit_id) and return the first version you find for path.
    raise NotImplementedError


def blame(commits, versions, head, path):
    """For each line of path at head: (line, commit_id, author) of the commit that last changed it."""
    # TODO: go through the commits oldest first. Keep two lists: the lines of the file so far,
    # and for each line, the (commit_id, author) it came from. At each commit that has a
    # version of path, use diff_opcodes(previous_lines, new_lines): 'equal' lines keep their
    # origin; every other new line comes from this commit.
    raise NotImplementedError


def revenue_by_commit(commits, versions, head, path, orders, month):
    """[(commit_id, revenue)] for every commit from the first to head, oldest first.

    revenue is what that commit's version of the query returns for month, or None.
    """
    # TODO: use log, file_at and run_revenue.
    raise NotImplementedError


def commits_that_changed(results):
    """The commit_ids whose revenue differs from the commit before (None to a number counts).

    results is the list from revenue_by_commit. Treat two numbers less than 0.005 apart as equal.
    """
    # TODO
    raise NotImplementedError


def find_block(lines, block):
    """Every start index where block appears as consecutive lines of lines."""
    return [i for i in range(len(lines) - len(block) + 1) if lines[i:i + len(block)] == block]


def revert(commits, versions, head, bad_commit, path):
    """The text of path at head with only bad_commit's change to it undone.

    Every later change is kept. Raise RevertConflict if the lines bad_commit
    wrote are no longer at head exactly once.
    """
    # TODO:
    # 1. before = the file at bad_commit's parent ("" if none), after = the file at bad_commit.
    # 2. current = the lines of the file at head.
    # 3. For each opcode of diff_opcodes(before lines, after lines) that is not 'equal':
    #    - if bad_commit wrote lines (after[j1:j2] is not empty), find them in current with
    #      find_block; exactly one match, or raise RevertConflict. Replace them with before[i1:i2].
    #    - if it only deleted lines, put before[i1:i2] back after the line before[i1 - 1]
    #      (or at the very top when i1 is 0).
    # 4. Return the lines joined with "\n", plus a final "\n".
    raise NotImplementedError


if __name__ == "__main__":
    commits, versions = load_history()
    orders = load_orders()
    head = commits[-1]["commit_id"]
    results = revenue_by_commit(commits, versions, head, "revenue.sql", orders, "2026-10")
    for cid, value in results:
        print(cid, value)
    print("changed the number:", commits_that_changed(results))
