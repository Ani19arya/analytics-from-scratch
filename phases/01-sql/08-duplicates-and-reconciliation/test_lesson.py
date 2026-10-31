"""Tests for lesson 08: duplicates and reconciliation.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected answers are computed with plain Python strings and dictionaries,
never with SQL. Your queries run on three kinds of data:
1. the committed data/*.csv,
2. a second dataset built in memory with make_data.build(seed=2026), so a
   query that just types out the answers cannot pass,
3. tiny hand-made tables for the edge cases: empty tables, two copies with
   the same updated_at (a tie), contacts with no email (NULL), the case, space
   and +tag variants of one address, and a month the app has but the CRM does
   not (a zero).
"""
import csv
import os
import re
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")

TABLES = {"crm_contacts": ["contact_id", "email", "full_name", "signup_date", "plan", "updated_at", "source"],
          "app_signups": ["month", "signups"]}
SECOND_SEED = 2026


def cast(value):
    if value is None or value == "":
        return None
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def read_csv(table):
    with open(os.path.join(HERE, "data", table + ".csv"), newline="") as f:
        return [{k: cast(v) for k, v in row.items()} for row in csv.DictReader(f)]


def as_loaded(rows):
    """Values exactly as they would come back from the CSV file."""
    return [{k: cast(None if v is None else str(v)) for k, v in r.items()} for r in rows]


def make_db(data):
    con = sqlite3.connect(":memory:")
    for table, cols in TABLES.items():
        con.execute("CREATE TABLE %s (%s)" % (table, ", ".join(cols)))
        con.executemany(
            "INSERT INTO %s VALUES (%s)" % (table, ", ".join("?" * len(cols))),
            [[r.get(c) for c in cols] for r in data.get(table, [])],
        )
    return con


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


# The reference answers, in plain Python.

def customer_key(row):
    """Spaces trimmed, lower case, +tag removed before the @; no email means the contact is its own customer."""
    email = row["email"]
    e = email.strip(" ").lower() if email is not None else ""
    if e == "":
        return "contact:" + row["contact_id"]
    at = e.find("@")
    plus = e.find("+")
    if 0 <= plus < at:
        return e[:plus] + e[at:]
    return e


def survivor_rows(d):
    best = {}
    for r in d["crm_contacts"]:
        k = customer_key(r)
        cur = best.get(k)
        # newest updated_at wins; on a tie, the smallest contact_id
        if cur is None or r["updated_at"] > cur["updated_at"] or (
                r["updated_at"] == cur["updated_at"] and r["contact_id"] < cur["contact_id"]):
            best[k] = r
    return best


def ref_survivors(d):
    rows = [(k, r["contact_id"], r["plan"], r["signup_date"]) for k, r in survivor_rows(d).items()]
    return sorted(rows, key=lambda t: (t[3], t[0]))


def ref_plan_counts(d):
    counts = {}
    for r in survivor_rows(d).values():
        counts[r["plan"]] = counts.get(r["plan"], 0) + 1
    return sorted(counts.items())


def ref_reconciliation(d):
    rows, keys = {}, {}
    for r in d["crm_contacts"]:
        m = r["signup_date"][:7]
        rows[m] = rows.get(m, 0) + 1
        keys.setdefault(m, set()).add(customer_key(r))
    app = {a["month"]: a["signups"] for a in d["app_signups"]}
    out = []
    for m in sorted(set(rows) | set(app)):
        u = len(keys.get(m, ()))
        out.append((m, rows.get(m, 0), u, app.get(m, 0), u - app.get(m, 0)))
    return out


class SqlTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queries = load_queries(SQL_FILE)

    def run_query(self, con, name):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        try:
            return [tuple(r) for r in con.execute(sql).fetchall()]
        except sqlite3.Error as e:
            self.fail("query '%s' did not run: %s" % (name, e))

    def assertRowsEqual(self, actual, expected, where):
        self.assertEqual(
            len(actual), len(expected),
            "%s: got %d rows, expected %d. Expected rows start %r" % (where, len(actual), len(expected), expected[:4]),
        )
        for a, e in zip(actual, expected):
            self.assertEqual(tuple(a), tuple(e), "%s: row %r, expected %r" % (where, a, e))

    def check_all(self, d, where):
        con = make_db(d)
        self.assertRowsEqual(self.run_query(con, "survivors"), ref_survivors(d), where + ", survivors")
        self.assertRowsEqual(self.run_query(con, "plan_counts"), ref_plan_counts(d), where + ", plan_counts")
        self.assertRowsEqual(self.run_query(con, "reconciliation"), ref_reconciliation(d), where + ", reconciliation")


class TestCommittedData(SqlTestCase):
    def setUp(self):
        self.d = {t: read_csv(t) for t in TABLES}
        self.con = make_db(self.d)

    def test_survivors(self):
        got = self.run_query(self.con, "survivors")
        self.assertEqual(len(got), sum(a["signups"] for a in self.d["app_signups"]),
                         "survivors should have one row per real customer, as many as the app counted; "
                         "check the case, space and +tag variants and the contacts with no email")
        self.assertRowsEqual(got, ref_survivors(self.d), "survivors (keep the newest row of each customer)")

    def test_plan_counts(self):
        self.assertRowsEqual(self.run_query(self.con, "plan_counts"), ref_plan_counts(self.d),
                             "plan_counts (count the plan on each customer's newest row)")

    def test_reconciliation(self):
        got = self.run_query(self.con, "reconciliation")
        self.assertRowsEqual(got, ref_reconciliation(self.d), "reconciliation")
        self.assertTrue(all(r[4] == 0 for r in got),
                        "after a correct dedupe every month should match the app, difference 0")


class TestSecondDataset(SqlTestCase):
    def test_same_queries_on_new_data(self):
        d = {t: as_loaded(rows) for t, rows in make_data.build(seed=SECOND_SEED).items()}
        self.check_all(d, "second dataset (seed %d)" % SECOND_SEED)


def contact(cid, email, plan="free", updated="2026-09-01 10:00:00", signup="2026-09-01", source="app_sync"):
    return {"contact_id": cid, "email": email, "full_name": "Name " + cid, "signup_date": signup, "plan": plan,
            "updated_at": updated, "source": source}


class TestEdgeCases(SqlTestCase):
    def test_empty_tables(self):
        self.check_all({"crm_contacts": [], "app_signups": []}, "empty tables (every query returns no rows)")

    def test_variants_of_one_address(self):
        d = {"crm_contacts": [
            contact("C1", "asha.rao1@post.example", "free", "2026-09-02 08:00:00"),
            contact("C2", "ASHA.RAO1@POST.EXAMPLE", "plus", "2026-09-05 08:00:00", source="import_mkt"),
            contact("C3", "  asha.rao1@post.example ", "free", "2026-09-03 08:00:00", source="import_mkt"),
            contact("C4", "asha.rao1+webinar@post.example", "free", "2026-09-04 08:00:00", source="import_mkt")],
            "app_signups": [{"month": "2026-09", "signups": 1}]}
        self.check_all(d, "four spellings of asha.rao1@post.example are one customer, and the newest row (C2, "
                          "plan plus) survives")

    def test_tie_on_updated_at(self):
        d = {"crm_contacts": [contact("C9", "bo@inbox.example", "family"),
                              contact("C5", "bo@inbox.example", "family", source="import_mkt")],
             "app_signups": [{"month": "2026-09", "signups": 1}]}
        self.check_all(d, "two exact copies with the same updated_at: the tie goes to the smaller contact_id, C5")

    def test_no_email(self):
        d = {"crm_contacts": [contact("C1", None, "free"), contact("C2", None, "plus"),
                              contact("C3", "cy@inbox.example", "plus")],
             "app_signups": [{"month": "2026-09", "signups": 3}]}
        self.check_all(d, "C1 and C2 have no email: they are two separate customers, keyed contact:C1 and "
                          "contact:C2, not one NULL group")

    def test_month_missing_on_one_side(self):
        d = {"crm_contacts": [contact("C1", "di@inbox.example", signup="2026-08-20", updated="2026-08-21 09:00:00")],
             "app_signups": [{"month": "2026-08", "signups": 1}, {"month": "2026-09", "signups": 2}]}
        self.check_all(d, "the app counted 2 signups in 2026-09 and the CRM has none: show 2026-09 with 0 CRM rows "
                          "and a difference of -2, not drop the month")


if __name__ == "__main__":
    unittest.main()
