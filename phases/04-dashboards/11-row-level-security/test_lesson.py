"""Tests for lesson 11: row-level security.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Every expected answer is computed here in plain Python over the raw rows, never
read from the solution. The two per-user queries run once for every login in the
mapping table and for logins that must see nothing: a stranger, an empty string,
NULL, and a user who has left. The same checks run on the committed CSV files,
on a second dataset built in memory with another seed, on a hand-made table (a
duplicate pair, a '*' user, mixed case and spaces, a NULL city, a zero amount)
and on empty tables.
"""
import csv
import importlib.util
import os
import re
import sqlite3
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")

SECOND_SEED = 4117
TABLES = {
    "sales": ["order_id", "order_date", "city", "amount"],
    "user_access": ["user_email", "city", "active"],
}


def cast(value, keep_text=False):
    if value == "" or value is None:
        return None
    if not isinstance(value, str) or keep_text:
        return value
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def clean(tables):
    """Cast numbers, keep emails exactly as typed (spaces and all), blank city as NULL."""
    out = {"sales": [], "user_access": []}
    for r in tables["sales"]:
        out["sales"].append({"order_id": str(r["order_id"]), "order_date": str(r["order_date"]),
                             "city": cast(r["city"], True), "amount": float(r["amount"])})
    for r in tables["user_access"]:
        out["user_access"].append({"user_email": r["user_email"], "city": cast(r["city"], True),
                                   "active": int(r["active"])})
    return out


def read_csv_tables():
    out = {}
    for table in TABLES:
        with open(os.path.join(HERE, "data", table + ".csv"), newline="") as f:
            out[table] = list(csv.DictReader(f))
    return clean(out)


def tables_from_build(seed):
    spec = importlib.util.spec_from_file_location("make_data", os.path.join(HERE, "make_data.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return clean(module.build(seed=seed))


def load_queries(path):
    queries, name, buf = {}, None, []
    with open(path) as f:
        for line in f:
            m = re.match(r"\s*--\s*query:\s*(\w+)", line)
            if m:
                if name:
                    queries[name] = "".join(buf)
                name, buf = m.group(1), []
            elif name is not None and not line.strip().startswith("--"):
                buf.append(line)
    if name:
        queries[name] = "".join(buf)
    return {k: v.strip() for k, v in queries.items()}


# ---- Plain Python references ------------------------------------------------

def norm(email):
    return None if email is None else email.strip().lower()


def grants(tables, user):
    """The set of cities a login may see; '*' means all. None or unknown: empty."""
    u = norm(user)
    return {a["city"] for a in tables["user_access"] if u is not None and norm(a["user_email"]) == u
            and a["active"] == 1}


def can_see(granted, city):
    return "*" in granted or (city is not None and city in granted)


def ref_visible_sales(tables, user):
    g = grants(tables, user)
    return [(s["order_id"], s["order_date"], s["city"], s["amount"])
            for s in sorted(tables["sales"], key=lambda s: s["order_id"]) if can_see(g, s["city"])]


def group(rows):
    groups = {}
    for city, amount in rows:
        groups.setdefault("Unassigned" if city is None else city, []).append(amount)
    return [(c, len(groups[c]), round(sum(groups[c]), 2)) for c in sorted(groups)]


def ref_revenue_by_city(tables, user):
    g = grants(tables, user)
    return group([(s["city"], s["amount"]) for s in tables["sales"] if can_see(g, s["city"])])


def ref_access_audit(tables):
    out = []
    for u in sorted({norm(a["user_email"]) for a in tables["user_access"]}):
        g = grants(tables, u)
        seen = [s["amount"] for s in tables["sales"] if can_see(g, s["city"])]
        out.append((u, len(seen), round(sum(seen), 2)))
    return out


def ref_uncovered(tables):
    covered = {a["city"] for a in tables["user_access"] if a["active"] == 1}
    return group([(s["city"], s["amount"]) for s in tables["sales"] if s["city"] not in covered])


def logins(tables):
    """Every email as typed, the same emails in capitals, and logins that must see nothing."""
    typed = sorted({a["user_email"] for a in tables["user_access"]})
    return typed + [t.upper() for t in typed] + ["stranger@example.com", "", None, "*"]


# ---- The checks ---------------------------------------------------------------

class RlsChecks:
    tables = None

    @classmethod
    def setUpClass(cls):
        cls.queries = load_queries(SQL_FILE)
        cls.con = sqlite3.connect(":memory:")
        for table, cols in TABLES.items():
            cls.con.execute("CREATE TABLE %s (%s)" % (table, ", ".join(cols)))
            cls.con.executemany("INSERT INTO %s VALUES (%s)" % (table, ", ".join("?" * len(cols))),
                                [[r[c] for c in cols] for r in cls.tables[table]])

    def run_query(self, name, user=None, with_user=False):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        params = {"user": user} if with_user else {}
        return [tuple(r) for r in self.con.execute(sql, params).fetchall()]

    def assertRowsEqual(self, actual, expected, what):
        self.assertEqual(len(actual), len(expected),
                         "%s: got %d rows, expected %d" % (what, len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%s: row %r should have the columns of %r" % (what, a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "%s: got NULL in %r, expected %r" % (what, a, e))
                    self.assertAlmostEqual(x, y, delta=0.011, msg="%s: row %r, expected %r" % (what, a, e))
                else:
                    self.assertEqual(x, y, "%s: row %r, expected %r" % (what, a, e))

    def test_visible_sales_for_every_login(self):
        for user in logins(self.tables):
            actual = self.run_query("visible_sales", user, True)
            expected = ref_visible_sales(self.tables, user)
            if not expected and actual:
                self.fail("visible_sales: login %r should see nothing (no active mapping row), but saw %d rows. "
                          "Deny by default" % (user, len(actual)))
            if len({r[0] for r in actual}) < len(actual):
                self.fail("visible_sales: login %r sees some orders twice. A pair typed twice in user_access "
                          "must not duplicate sales: use EXISTS or IN, not a JOIN" % (user,))
            self.assertRowsEqual(actual, expected, "visible_sales for %r (match emails ignoring case and spaces; "
                                                   "only active rows; '*' sees every city and unassigned orders)"
                                 % (user,))

    def test_visible_revenue_by_city_for_every_login(self):
        for user in logins(self.tables):
            self.assertRowsEqual(self.run_query("visible_revenue_by_city", user, True),
                                 ref_revenue_by_city(self.tables, user),
                                 "visible_revenue_by_city for %r (NULL city shows as 'Unassigned')" % (user,))

    def test_access_audit(self):
        self.assertRowsEqual(self.run_query("access_audit"), ref_access_audit(self.tables),
                             "access_audit (one row per cleaned email, 0 and 0.0 for someone who sees nothing)")

    def test_uncovered_sales(self):
        self.assertRowsEqual(self.run_query("uncovered_sales"), ref_uncovered(self.tables),
                             "uncovered_sales (cities no ACTIVE city-level row covers, plus unassigned orders)")


class TestCommittedData(RlsChecks, unittest.TestCase):
    tables = read_csv_tables()

    def test_data_has_the_traps(self):
        emails = [a["user_email"] for a in self.tables["user_access"]]
        self.assertTrue(any(e != e.strip().lower() for e in emails), "data should have a messy email")
        pairs = [(norm(a["user_email"]), a["city"]) for a in self.tables["user_access"]]
        self.assertLess(len(set(pairs)), len(pairs), "data should repeat a pair")
        self.assertTrue(any(s["city"] is None for s in self.tables["sales"]), "data should have unassigned sales")


class TestSecondDataset(RlsChecks, unittest.TestCase):
    """Built in memory with another seed: hard-coded answers fail here."""
    tables = tables_from_build(SECOND_SEED)


class TestTinyEdgeCases(RlsChecks, unittest.TestCase):
    """head sees all four orders; ravi has Pune twice and Nashik inactive; MEERA is
    typed with capitals and spaces; T3 has no city and T4 is 0.00."""
    tables = {
        "sales": [
            {"order_id": "T1", "order_date": "2026-10-01", "city": "Pune", "amount": 100.0},
            {"order_id": "T2", "order_date": "2026-10-01", "city": "Nashik", "amount": 50.0},
            {"order_id": "T3", "order_date": "2026-10-02", "city": None, "amount": 70.0},
            {"order_id": "T4", "order_date": "2026-10-02", "city": "Pune", "amount": 0.0},
        ],
        "user_access": [
            {"user_email": "head@x.example.com", "city": "*", "active": 1},
            {"user_email": "ravi@x.example.com", "city": "Pune", "active": 1},
            {"user_email": "ravi@x.example.com", "city": "Pune", "active": 1},
            {"user_email": "ravi@x.example.com", "city": "Nashik", "active": 0},
            {"user_email": "  MEERA@X.example.com", "city": "Nashik", "active": 1},
            {"user_email": "gone@x.example.com", "city": "*", "active": 0},
        ],
    }


class TestEmptyTables(RlsChecks, unittest.TestCase):
    """No sales and no mapping: every query returns no rows instead of an error."""
    tables = {"sales": [], "user_access": []}


if __name__ == "__main__":
    unittest.main()
