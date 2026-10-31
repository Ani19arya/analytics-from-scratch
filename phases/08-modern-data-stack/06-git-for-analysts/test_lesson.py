"""Tests for lesson 06: git for analysts.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

git is NOT needed. The expected answers are computed here, with code of the
test's own: the file at each commit by replaying the history forwards, line
matching by a longest-common-subsequence table (not difflib), and the
correct revenue figure by a plain Python sum over the orders. Your functions
run on three kinds of data:
1. the committed data/*.csv,
2. a second history and order book built in memory with
   make_data.build(seed=2027), with other authors, commit ids, commit order
   and a different bad edit, so typing out the answers cannot pass,
3. tiny hand-made histories for the edge cases: a single commit, a file
   created later, a line changed and changed back, an empty result list, a
   revert that must conflict, and reverts of a pure insertion and a pure
   deletion.
An optional test replays both histories into a throwaway git repository in a
temporary folder (never this course) and checks your answers against real
git log, git blame and git revert. It is skipped if git is not installed.
"""
import csv
import importlib.util
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402
import replay_in_git  # noqa: E402

TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

SECOND_SEED = 2027
MONTH = "2026-10"
PATH = "revenue.sql"


# Turning build(seed) rows into what the loaders return.

def to_history(tables):
    commits = [dict(c, parent_id=c["parent_id"] or None) for c in tables["commits"]]
    lines = {}
    for r in tables["file_versions"]:
        lines.setdefault((r["commit_id"], r["path"]), []).append((int(r["line_no"]), str(r["line"])))
    return commits, {k: "\n".join(t for _, t in sorted(v)) + "\n" for k, v in lines.items()}


def to_orders(tables):
    return [dict(o, amount=float(o["amount"]), discount=float(o["discount"]), is_test=int(o["is_test"]))
            for o in tables["orders"]]


def committed():
    tables = {}
    for name in ("orders", "commits", "file_versions"):
        with open(os.path.join(HERE, "data", name + ".csv"), newline="") as f:
            tables[name] = list(csv.DictReader(f))
    return tables


# The reference answers, written without difflib.

def ref_snapshots(commits, versions):
    """{commit_id: {path: text}}, built by walking the history forwards from the first commit."""
    order = []
    children = {c["parent_id"]: c for c in commits}
    c = children.get(None)
    while c is not None:
        order.append(c)
        c = children.get(c["commit_id"])
    snaps, files = {}, {}
    for c in order:
        for (cid, path), text in versions.items():
            if cid == c["commit_id"]:
                files[path] = text
        snaps[c["commit_id"]] = dict(files)
    return order, snaps


def lcs_pairs(a, b):
    """Index pairs (i, j) with a[i] == b[j] in a longest common subsequence, by dynamic programming."""
    n, m = len(a), len(b)
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            table[i][j] = table[i + 1][j + 1] + 1 if a[i] == b[j] else max(table[i + 1][j], table[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j]:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def ref_blame(commits, versions, head, path):
    order, snaps = ref_snapshots(commits, versions)
    order = order[:[c["commit_id"] for c in order].index(head) + 1]
    prev, origin = [], []
    for c in order:
        text = snaps[c["commit_id"]].get(path)
        if text is None:
            continue
        lines = text.splitlines()
        kept = dict(lcs_pairs(prev, lines))
        kept = {j: i for i, j in kept.items()}
        origin = [origin[kept[j]] if j in kept else (c["commit_id"], c["author"]) for j in range(len(lines))]
        prev = lines
    return [(line, cid, author) for line, (cid, author) in zip(prev, origin)]


def ref_revert_text(before, after, current):
    """Undo before -> after on current, matching unchanged lines by LCS. None means a conflict."""
    a, b, cur = before.splitlines(), after.splitlines(), current.splitlines()
    pairs = lcs_pairs(a, b)
    hunks, pi, pj = [], 0, 0
    for i, j in pairs + [(len(a), len(b))]:
        if i > pi or j > pj:
            hunks.append((a[pi:i], b[pj:j], a[pi - 1] if pi > 0 else None))
        pi, pj = i + 1, j + 1
    for removed, wrote, anchor in hunks:
        if wrote:
            spots = [k for k in range(len(cur) - len(wrote) + 1) if cur[k:k + len(wrote)] == wrote]
            if len(spots) != 1:
                return None
            cur[spots[0]:spots[0] + len(wrote)] = removed
        elif anchor is None:
            cur[0:0] = removed
        else:
            spots = [k for k, line in enumerate(cur) if line == anchor]
            if len(spots) != 1:
                return None
            cur[spots[0] + 1:spots[0] + 1] = removed
    return "\n".join(cur) + "\n" if cur else ""


def correct_revenue(orders, month):
    """Finance's definition, in plain Python: delivered, not a test, amount net of discount."""
    return round(sum(o["amount"] - o["discount"] for o in orders
                     if o["status"] == "delivered" and o["is_test"] == 0 and o["order_date"][:7] == month), 2)


def ref_changed(results):
    out, before = [], None
    for cid, value in results:
        if (value is None) != (before is None) or (value is not None and abs(value - before) > 0.005):
            out.append(cid)
        before = value
    return out


def sql_revenue(sql, orders, month):
    """The test's own runner: one version of the query on the orders, the value for month or None."""
    if sql is None:
        return None
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE orders (order_id, order_date, status, amount, discount, is_test)")
    con.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?)",
                    [(o["order_id"], o["order_date"], o["status"], o["amount"], o["discount"], o["is_test"]) for o in orders])
    values = [r[1] for r in con.execute(sql).fetchall() if r[0] == month]
    return values[0] if values else None


def ref_revenue_by_commit(commits, versions, orders, month, path=PATH):
    order, snaps = ref_snapshots(commits, versions)
    return [(c["commit_id"], sql_revenue(snaps[c["commit_id"]].get(path), orders, month)) for c in order]


class TestHistory(unittest.TestCase):
    """The same checks, run on any history."""

    def check_history(self, commits, versions, orders, where):
        head = commits[-1]["commit_id"]
        order, snaps = ref_snapshots(commits, versions)

        got = [c["commit_id"] for c in lesson.log(commits, head)]
        self.assertEqual(got, [c["commit_id"] for c in reversed(order)],
                         "%s: log should list every commit from head back to the first, newest first" % where)

        for c in order:
            for path in ("revenue.sql", "orders_by_month.sql", "README.md"):
                self.assertEqual(lesson.file_at(commits, versions, c["commit_id"], path), snaps[c["commit_id"]].get(path),
                                 "%s: file_at(%s, %s) is wrong: a commit that did not touch a file keeps its "
                                 "parent's version, and a file not created yet is None" % (where, c["commit_id"], path))

        self.assertEqual(lesson.blame(commits, versions, head, PATH), ref_blame(commits, versions, head, PATH),
                         "%s: blame should give each line the commit that last changed it" % where)

        results = lesson.revenue_by_commit(commits, versions, head, PATH, orders, MONTH)
        want = ref_revenue_by_commit(commits, versions, orders, MONTH)
        self.assertEqual([r[0] for r in results], [r[0] for r in want],
                         "%s: revenue_by_commit should have one row per commit, oldest first" % where)
        for (cid, value), (_, expected) in zip(results, want):
            self.assertAlmostEqual(value, expected, delta=0.005,
                                   msg="%s: revenue at commit %s, expected %r" % (where, cid, expected))

        changed = lesson.commits_that_changed(results)
        self.assertEqual(changed, ref_changed(want),
                         "%s: commits_that_changed should list the commits whose number differs from the one before" % where)
        self.assertEqual(len(changed), 3, "%s: the number should change three times: created, the bad edit, "
                                          "the discount fix" % where)

        bad = changed[1]  # the first change after the query was created
        by_id = {c["commit_id"]: c for c in commits}
        expected_text = ref_revert_text(snaps[by_id[bad]["parent_id"]][PATH], snaps[bad][PATH], snaps[head][PATH])
        reverted = lesson.revert(commits, versions, head, bad, PATH)
        self.assertEqual(reverted, expected_text,
                         "%s: revert should undo only commit %s and keep every later change" % (where, bad))
        self.assertAlmostEqual(sql_revenue(reverted, orders, MONTH), correct_revenue(orders, MONTH), delta=0.005,
                               msg="%s: after the revert the query should give finance's number (delivered, not a "
                                   "test, net of discount)" % where)
        first = changed[0]
        self.assertNotAlmostEqual(sql_revenue(snaps[first][PATH], orders, MONTH), correct_revenue(orders, MONTH),
                                  delta=0.005, msg="%s: restoring the first version is not the same as a revert" % where)


class TestCommittedData(TestHistory):
    def test_committed_history(self):
        tables = committed()
        commits, versions = to_history(tables)
        loaded_commits, loaded_versions = lesson.load_history(os.path.join(HERE, "data"))
        self.assertEqual(loaded_commits, commits, "load_history is given: do not change it")
        self.assertEqual(loaded_versions, versions, "load_history is given: do not change it")
        self.check_history(commits, versions, to_orders(tables), "committed data")


class TestSecondDataset(TestHistory):
    def test_second_history(self):
        tables = {k: [{c: str(v) for c, v in r.items()} for r in rows] for k, rows in make_data.build(SECOND_SEED).items()}
        commits, versions = to_history(tables)
        self.check_history(commits, versions, to_orders(tables), "second dataset (seed %d)" % SECOND_SEED)


def tiny(steps):
    """steps: [(commit_id, author, {path: [lines]})] -> (commits, versions)."""
    commits, versions, parent = [], {}, None
    for cid, author, files in steps:
        commits.append({"commit_id": cid, "parent_id": parent, "author": author,
                        "committed_at": "2026-10-01 10:00:00", "message": "change " + cid})
        for path, lines in files.items():
            versions[(cid, path)] = "\n".join(lines) + "\n"
        parent = cid
    return commits, versions


SQL_A = ["SELECT strftime('%Y-%m', order_date) AS month,", "  SUM(amount) AS revenue", "FROM orders",
         "WHERE status = 'delivered'", "GROUP BY month;"]
ORDERS = [{"order_id": 1, "order_date": "2026-10-02", "status": "delivered", "amount": 10.0, "discount": 0.0, "is_test": 0},
          {"order_id": 2, "order_date": "2026-10-03", "status": "refunded", "amount": 5.0, "discount": 0.0, "is_test": 0}]


class TestEdgeCases(unittest.TestCase):
    def test_single_commit(self):
        commits, versions = tiny([("a1", "Asha", {"q.sql": ["SELECT 1;", "-- one"]})])
        self.assertEqual([c["commit_id"] for c in lesson.log(commits, "a1")], ["a1"], "a single commit: log is just that commit")
        self.assertIsNone(lesson.file_at(commits, versions, "a1", "other.sql"), "a file that never existed is None")
        self.assertEqual(lesson.blame(commits, versions, "a1", "q.sql"), [("SELECT 1;", "a1", "Asha"), ("-- one", "a1", "Asha")],
                         "in a single commit every line comes from that commit")

    def test_file_created_later(self):
        commits, versions = tiny([("a1", "Asha", {"README.md": ["# queries"]}),
                                  ("b2", "Ravi", {PATH: SQL_A}),
                                  ("c3", "Omar", {"README.md": ["# queries", "more"]})])
        self.assertIsNone(lesson.file_at(commits, versions, "a1", PATH), "revenue.sql did not exist at the first commit")
        self.assertEqual(lesson.file_at(commits, versions, "c3", PATH), "\n".join(SQL_A) + "\n",
                         "c3 did not touch revenue.sql, so it is the version from b2")
        results = lesson.revenue_by_commit(commits, versions, "c3", PATH, ORDERS, MONTH)
        self.assertEqual([r[0] for r in results], ["a1", "b2", "c3"], "one row per commit, oldest first")
        self.assertIsNone(results[0][1], "no query at a1, so revenue is None")
        self.assertAlmostEqual(results[1][1], 10.0, msg="b2 counts the delivered order only")
        self.assertEqual(lesson.commits_that_changed(results), ["b2"], "only b2 changed the number (from None to 10.0)")

    def test_changed_list(self):
        self.assertEqual(lesson.commits_that_changed([]), [], "no commits, no changes")
        self.assertEqual(lesson.commits_that_changed([("a", None), ("b", None)]), [], "None to None is not a change")
        series = [("a", None), ("b", 10.0), ("c", 10.0), ("d", 12.5), ("e", 10.0), ("f", 0.0)]
        self.assertEqual(lesson.commits_that_changed(series), ["b", "d", "e", "f"],
                         "a number going back to an earlier value is still a change, and so is a drop to 0")

    def test_blame_changed_back(self):
        commits, versions = tiny([("a1", "Asha", {PATH: ["x", "y", "z"]}),
                                  ("b2", "Leena", {PATH: ["x", "Y", "z"]}),
                                  ("c3", "Omar", {"other.sql": ["o"]}),
                                  ("d4", "Ravi", {PATH: ["x", "y", "z"]})])
        self.assertEqual(lesson.blame(commits, versions, "d4", PATH), [("x", "a1", "Asha"), ("y", "d4", "Ravi"), ("z", "a1", "Asha")],
                         "y was changed to Y and back: blame names the commit that last changed the line (d4), "
                         "even though the text matches a1")

    def test_revert_conflict(self):
        commits, versions = tiny([("a1", "Asha", {PATH: SQL_A}),
                                  ("b2", "Leena", {PATH: SQL_A[:3] + ["WHERE status <> 'cancelled'"] + SQL_A[4:]}),
                                  ("c3", "Omar", {PATH: SQL_A[:3] + ["WHERE status NOT IN ('cancelled', 'pending')"] + SQL_A[4:]})])
        with self.assertRaises(lesson.RevertConflict, msg="c3 changed the line b2 wrote, so undoing b2 must raise "
                                                          "RevertConflict instead of guessing"):
            lesson.revert(commits, versions, "c3", "b2", PATH)

    def test_revert_insertion_and_deletion(self):
        with_test = SQL_A[:4] + ["  AND is_test = 0"] + SQL_A[4:]
        commits, versions = tiny([("a1", "Asha", {PATH: SQL_A}),
                                  ("b2", "Leena", {PATH: with_test}),
                                  ("c3", "Omar", {PATH: ["-- revenue"] + with_test})])
        self.assertEqual(lesson.revert(commits, versions, "c3", "b2", PATH), "\n".join(["-- revenue"] + SQL_A) + "\n",
                         "b2 only added a line: the revert removes it and keeps c3's comment")
        commits, versions = tiny([("a1", "Asha", {PATH: with_test}),
                                  ("b2", "Leena", {PATH: SQL_A}),
                                  ("c3", "Omar", {PATH: SQL_A + ["-- end"]})])
        self.assertEqual(lesson.revert(commits, versions, "c3", "b2", PATH), "\n".join(with_test + ["-- end"]) + "\n",
                         "b2 only deleted a line: the revert puts it back after the line it used to follow")


@unittest.skipUnless(shutil.which("git"), "git is not installed; this optional check compares with real git")
class TestAgainstRealGit(unittest.TestCase):
    def compare(self, data_dir, where):
        commits, versions = lesson.load_history(data_dir)
        orders = lesson.load_orders(data_dir)
        head = commits[-1]["commit_id"]
        tmp = tempfile.mkdtemp()
        try:
            repo = os.path.join(tmp, "repo")
            hashes = replay_in_git.replay(repo, data_dir)
            env = dict(replay_in_git.clean_env(repo), GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="test@example.com",
                       GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="test@example.com")
            out = replay_in_git.git(repo, "log", "--format=%an%x09%s", env=env).splitlines()
            self.assertEqual(out, ["%s\t%s" % (c["author"], c["message"]) for c in lesson.log(commits, head)],
                             "%s: your log does not match git log" % where)
            porcelain = replay_in_git.git(repo, "blame", "--line-porcelain", PATH, env=env).splitlines()
            authors = [line[len("author "):] for line in porcelain if line.startswith("author ")]
            self.assertEqual(authors, [a for _, _, a in lesson.blame(commits, versions, head, PATH)],
                             "%s: your blame authors do not match git blame" % where)
            results = lesson.revenue_by_commit(commits, versions, head, PATH, orders, MONTH)
            bad = lesson.commits_that_changed(results)[1]
            replay_in_git.git(repo, "-c", "commit.gpgsign=false", "revert", "--no-edit", hashes[bad], env=env)
            with open(os.path.join(repo, PATH)) as f:
                self.assertEqual(f.read(), lesson.revert(commits, versions, head, bad, PATH),
                                 "%s: your revert does not match git revert" % where)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_committed_history_matches_git(self):
        self.compare(os.path.join(HERE, "data"), "committed data")

    def test_second_history_matches_git(self):
        tmp = tempfile.mkdtemp()
        try:
            for name, rows in make_data.build(SECOND_SEED).items():
                with open(os.path.join(tmp, name + ".csv"), "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                    w.writeheader()
                    w.writerows(rows)
            self.compare(tmp, "second dataset (seed %d)" % SECOND_SEED)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
