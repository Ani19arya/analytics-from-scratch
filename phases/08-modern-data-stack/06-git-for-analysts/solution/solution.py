"""Git for analysts: answer who changed the revenue query, and undo it, from a recorded history.

Worked answer. Python 3.9+ standard library only; git is not needed.

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
DATA = os.path.join(os.path.dirname(HERE), "data")


class RevertConflict(Exception):
    """The change cannot be undone cleanly: the lines it touched were changed again later."""


# Given helpers (the exercise has these too).

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


# The answers.

def log(commits, head):
    """The commits from head back to the first commit, newest first, following parent_id."""
    by_id = {c["commit_id"]: c for c in commits}
    out, cid = [], head
    while cid is not None:
        c = by_id[cid]
        out.append(c)
        cid = c["parent_id"]
    return out


def file_at(commits, versions, commit_id, path):
    """The text of path as it was at commit_id, or None if the file did not exist yet.

    A commit that did not touch the file keeps the version from its parent.
    """
    for c in log(commits, commit_id):
        if (c["commit_id"], path) in versions:
            return versions[(c["commit_id"], path)]
    return None


def blame(commits, versions, head, path):
    """For each line of path at head: (line, commit_id, author) of the commit that last changed it."""
    origins, previous = [], []
    for c in reversed(log(commits, head)):
        if (c["commit_id"], path) not in versions:
            continue
        lines = versions[(c["commit_id"], path)].splitlines()
        new = []
        for tag, i1, i2, j1, j2 in diff_opcodes(previous, lines):
            if tag == "equal":
                new.extend(origins[i1:i2])            # unchanged lines keep their origin
            else:
                new.extend((c["commit_id"], c["author"]) for _ in range(j1, j2))  # new or changed here
        origins, previous = new, lines
    return [(line, cid, author) for line, (cid, author) in zip(previous, origins)]


def revenue_by_commit(commits, versions, head, path, orders, month):
    """[(commit_id, revenue)] for every commit from the first to head, oldest first.

    revenue is what that commit's version of the query returns for month, or None.
    """
    return [(c["commit_id"], run_revenue(file_at(commits, versions, c["commit_id"], path), orders, month))
            for c in reversed(log(commits, head))]


def commits_that_changed(results):
    """The commit_ids whose revenue differs from the commit before (None to a number counts)."""
    out, before = [], None
    for cid, value in results:
        changed = (value is None) != (before is None) or (value is not None and abs(value - before) > 0.005)
        if changed:
            out.append(cid)
        before = value
    return out


def find_block(lines, block):
    """Every start index where block appears as consecutive lines of lines."""
    return [i for i in range(len(lines) - len(block) + 1) if lines[i:i + len(block)] == block]


def revert(commits, versions, head, bad_commit, path):
    """The text of path at head with only bad_commit's change to it undone.

    Every later change is kept. Raises RevertConflict if the lines bad_commit
    wrote are no longer there exactly once at head.
    """
    by_id = {c["commit_id"]: c for c in commits}
    before = (file_at(commits, versions, by_id[bad_commit]["parent_id"], path)
              if by_id[bad_commit]["parent_id"] else None) or ""
    after = file_at(commits, versions, bad_commit, path) or ""
    old, new = before.splitlines(), after.splitlines()
    current = (file_at(commits, versions, head, path) or "").splitlines()
    for tag, i1, i2, j1, j2 in diff_opcodes(old, new):
        if tag == "equal":
            continue
        wrote, removed = new[j1:j2], old[i1:i2]
        if wrote:
            spots = find_block(current, wrote)
            if len(spots) != 1:
                raise RevertConflict("the lines %r are not at head exactly once" % wrote)
            current[spots[0]:spots[0] + len(wrote)] = removed
        else:
            # bad_commit only deleted lines: put them back after the line that came before them
            if i1 == 0:
                current[0:0] = removed
                continue
            spots = find_block(current, [old[i1 - 1]])
            if len(spots) != 1:
                raise RevertConflict("cannot find where %r went" % removed)
            current[spots[0] + 1:spots[0] + 1] = removed
    return "\n".join(current) + "\n" if current else ""


if __name__ == "__main__":
    commits, versions = load_history()
    orders = load_orders()
    head = commits[-1]["commit_id"]
    results = revenue_by_commit(commits, versions, head, "revenue.sql", orders, "2026-10")
    for cid, value in results:
        print(cid, value)
    print("changed the number:", commits_that_changed(results))
