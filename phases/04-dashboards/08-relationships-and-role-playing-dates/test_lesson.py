"""Tests for lesson 08: relationships, role-playing dates and many-to-many.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

Every expected answer is computed here with plain Python over the raw rows,
never read from the solution. The same checks run on the committed CSV files,
on a second dataset built in memory with another seed, on a tiny hand-made
model (a repeated bridge pair, an unshipped order, a zero amount, a tie, an
order with no campaign) and on a model with no campaign rows at all.

Optional export check: if you rebuild the ship month visual in Power BI and
export it to export/revenue_by_ship_month.csv (columns year_month, revenue),
the test compares it with the data. Without the file that test is skipped.
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

SECOND_SEED = 4087
TABLES = {
    "dim_date": ["date", "year_month"],
    "orders": ["order_id", "order_date", "ship_date", "amount"],
    "campaigns": ["campaign_id", "campaign_name"],
    "order_campaign": ["order_id", "campaign_id"],
}
EXPORT = os.path.join(HERE, "export", "revenue_by_ship_month.csv")


def cast(value):
    if value == "" or value is None:
        return None
    if not isinstance(value, str):
        return value
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def read_csv_tables():
    out = {}
    for table in TABLES:
        with open(os.path.join(HERE, "data", table + ".csv"), newline="") as f:
            out[table] = [{k: cast(v) for k, v in row.items()} for row in csv.DictReader(f)]
    return out


def tables_from_build(seed):
    spec = importlib.util.spec_from_file_location("make_data", os.path.join(HERE, "make_data.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    built = module.build(seed=seed)
    return {t: [{k: cast(str(v)) for k, v in r.items()} for r in rows] for t, rows in built.items()}


def load_db(tables):
    con = sqlite3.connect(":memory:")
    for table, cols in TABLES.items():
        con.execute("CREATE TABLE %s (%s)" % (table, ", ".join(cols)))
        con.executemany("INSERT INTO %s VALUES (%s)" % (table, ", ".join("?" * len(cols))),
                        [[r[c] for c in cols] for r in tables[table]])
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


def days(start, end):
    import datetime
    d, e, out = datetime.date.fromisoformat(start), datetime.date.fromisoformat(end), []
    while d <= e:
        out.append({"date": d.isoformat(), "year_month": d.isoformat()[:7]})
        d += datetime.timedelta(days=1)
    return out


# ---- Plain Python references ------------------------------------------------

def month_of(tables, date_value):
    for d in tables["dim_date"]:
        if d["date"] == date_value:
            return d["year_month"]
    return None


def ref_by_month(tables, key):
    groups = {}
    for o in tables["orders"]:
        month = month_of(tables, o[key])
        if month is None and key == "order_date":
            continue
        groups.setdefault(month, []).append(o["amount"])
    months = sorted(m for m in groups if m is not None) + ([None] if None in groups else [])
    return [(m, len(groups[m]), round(sum(groups[m]), 2)) for m in months]


def distinct_pairs(tables):
    return sorted({(b["order_id"], b["campaign_id"]) for b in tables["order_campaign"]})


def ref_revenue_by_campaign(tables):
    amount = {o["order_id"]: o["amount"] for o in tables["orders"]}
    name = {c["campaign_id"]: c["campaign_name"] for c in tables["campaigns"]}
    groups = {}
    for order_id, campaign_id in distinct_pairs(tables):
        groups.setdefault(name[campaign_id], []).append(amount[order_id])
    return [(n, len(groups[n]), round(sum(groups[n]), 2)) for n in sorted(groups)]


def ref_campaign_totals(tables):
    amount = {o["order_id"]: o["amount"] for o in tables["orders"]}
    pairs = distinct_pairs(tables)
    touched = {p[0] for p in pairs}
    return [(round(sum(amount[p[0]] for p in pairs), 2),
             round(sum(a for k, a in amount.items() if k in touched), 2),
             round(sum(a for k, a in amount.items() if k not in touched), 2),
             round(sum(amount.values()), 2))]


def ref_allocated(tables):
    amount = {o["order_id"]: o["amount"] for o in tables["orders"]}
    name = {c["campaign_id"]: c["campaign_name"] for c in tables["campaigns"]}
    pairs = distinct_pairs(tables)
    n_campaigns = {}
    for order_id, _ in pairs:
        n_campaigns[order_id] = n_campaigns.get(order_id, 0) + 1
    groups = {}
    for order_id, campaign_id in pairs:
        groups[name[campaign_id]] = groups.get(name[campaign_id], 0) + amount[order_id] / n_campaigns[order_id]
    return [(n, round(groups[n], 2)) for n in sorted(groups)]


# ---- The checks ---------------------------------------------------------------

class ModelChecks:
    tables = None

    @classmethod
    def setUpClass(cls):
        cls.con = load_db(cls.tables)
        cls.queries = load_queries(SQL_FILE)

    def run_query(self, name):
        sql = self.queries.get(name, "")
        if not sql:
            self.fail("query '%s' is empty in %s: write it first" % (name, os.path.basename(SQL_FILE)))
        return [tuple(r) for r in self.con.execute(sql).fetchall()]

    def assertRowsEqual(self, actual, expected, what, tol=0.011):
        self.assertEqual(len(actual), len(expected),
                         "%s: got %d rows, expected %d" % (what, len(actual), len(expected)))
        for a, e in zip(actual, expected):
            self.assertEqual(len(a), len(e), "%s: row %r should have the columns of %r" % (what, a, e))
            for x, y in zip(a, e):
                if isinstance(y, float):
                    self.assertIsNotNone(x, "%s: got NULL in %r, expected %r" % (what, a, e))
                    self.assertAlmostEqual(x, y, delta=tol, msg="%s: row %r, expected %r" % (what, a, e))
                else:
                    self.assertEqual(x, y, "%s: row %r, expected %r" % (what, a, e))

    def test_revenue_by_order_month(self):
        self.assertRowsEqual(self.run_query("revenue_by_order_month"), ref_by_month(self.tables, "order_date"),
                             "revenue_by_order_month (join dim_date on order_date)")

    def test_revenue_by_ship_month_keeps_unshipped_orders(self):
        actual = self.run_query("revenue_by_ship_month")
        expected = ref_by_month(self.tables, "ship_date")
        if expected and expected[-1][0] is None and (not actual or actual[-1][0] is not None):
            self.fail("revenue_by_ship_month: the orders with no ship_date are missing; keep them on a NULL month "
                      "row at the end so the ship view adds up to the same total as the order view")
        self.assertRowsEqual(actual, expected, "revenue_by_ship_month (join the SAME dim_date on ship_date)")

    def test_both_date_views_add_up_to_the_same_total(self):
        by_order = sum(r[2] for r in self.run_query("revenue_by_order_month"))
        by_ship = sum(r[2] for r in self.run_query("revenue_by_ship_month"))
        self.assertAlmostEqual(by_order, by_ship, delta=0.05,
                               msg="order month total %.2f and ship month total %.2f differ: the role changes "
                                   "which month an order lands in, never whether it is counted" % (by_order, by_ship))

    def test_revenue_by_campaign_counts_each_pair_once(self):
        actual = self.run_query("revenue_by_campaign")
        expected = ref_revenue_by_campaign(self.tables)
        for a, e in zip(actual, expected):
            if len(a) == 3 and a[0] == e[0] and a[1] > e[1]:
                self.fail("campaign %s: %d orders, expected %d. The bridge repeats some (order, campaign) pairs: "
                          "take DISTINCT pairs before you join" % (e[0], a[1], e[1]))
        self.assertRowsEqual(actual, expected, "revenue_by_campaign")

    def test_campaign_totals_show_the_double_count(self):
        self.assertRowsEqual(self.run_query("campaign_totals"), ref_campaign_totals(self.tables),
                             "campaign_totals (sum of rows, each order once, orders with no campaign, all orders)")

    def test_allocated_revenue_adds_up(self):
        actual = self.run_query("revenue_by_campaign_allocated")
        self.assertRowsEqual(actual, ref_allocated(self.tables), "revenue_by_campaign_allocated", tol=0.02)
        if actual:
            self.assertAlmostEqual(sum(r[1] for r in actual), ref_campaign_totals(self.tables)[0][1], delta=0.05,
                                   msg="allocated rows must add up to the revenue of orders with a campaign")


class TestCommittedData(ModelChecks, unittest.TestCase):
    tables = read_csv_tables()

    def test_data_has_the_traps(self):
        self.assertTrue(any(o["ship_date"] is None for o in self.tables["orders"]), "data should have unshipped orders")
        self.assertLess(len(distinct_pairs(self.tables)), len(self.tables["order_campaign"]),
                        "data should repeat some bridge pairs")


class TestSecondDataset(ModelChecks, unittest.TestCase):
    """Built in memory with another seed: hard-coded answers fail here."""
    tables = tables_from_build(SECOND_SEED)


class TestTinyEdgeCases(ModelChecks, unittest.TestCase):
    """Order 1 has two campaigns and a repeated pair, order 2 ships next month,
    order 3 is unshipped, order 4 has no campaign and a zero amount, and two
    campaigns tie on revenue."""
    tables = {
        "dim_date": days("2026-01-01", "2026-02-28"),
        "orders": [
            {"order_id": 1, "order_date": "2026-01-05", "ship_date": "2026-01-06", "amount": 100.0},
            {"order_id": 2, "order_date": "2026-01-30", "ship_date": "2026-02-02", "amount": 50.0},
            {"order_id": 3, "order_date": "2026-02-27", "ship_date": None, "amount": 30.0},
            {"order_id": 4, "order_date": "2026-02-10", "ship_date": "2026-02-10", "amount": 0.0},
        ],
        "campaigns": [{"campaign_id": 1, "campaign_name": "A"}, {"campaign_id": 2, "campaign_name": "B"},
                      {"campaign_id": 3, "campaign_name": "C"}],
        "order_campaign": [{"order_id": 1, "campaign_id": 1}, {"order_id": 1, "campaign_id": 1},
                           {"order_id": 1, "campaign_id": 2}, {"order_id": 2, "campaign_id": 3},
                           {"order_id": 3, "campaign_id": 3}],
    }


class TestNoCampaigns(ModelChecks, unittest.TestCase):
    """An empty bridge: campaign queries return no rows and the totals are 0."""
    tables = {
        "dim_date": days("2026-03-01", "2026-03-31"),
        "orders": [{"order_id": 9, "order_date": "2026-03-03", "ship_date": "2026-03-04", "amount": 12.5}],
        "campaigns": [{"campaign_id": 1, "campaign_name": "A"}],
        "order_campaign": [],
    }


@unittest.skipUnless(os.path.exists(EXPORT), "optional: export/revenue_by_ship_month.csv not present")
class TestOptionalPowerBIExport(unittest.TestCase):
    def test_export_matches_the_data(self):
        expected = {m: r for m, _, r in ref_by_month(read_csv_tables(), "ship_date")}
        with open(EXPORT, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        got = {}
        for row in rows:
            month = (row.get("year_month") or "").strip()
            month = None if month in ("", "(Blank)") else month
            got[month] = float(str(row.get("revenue", "0")).replace(",", ""))
        for month, revenue in expected.items():
            self.assertIn(month, got, "your export has no row for ship month %r" % (month,))
            self.assertAlmostEqual(got[month], revenue, delta=0.05,
                                   msg="ship month %r: export says %.2f, the data says %.2f" % (month, got[month], revenue))


if __name__ == "__main__":
    unittest.main()
