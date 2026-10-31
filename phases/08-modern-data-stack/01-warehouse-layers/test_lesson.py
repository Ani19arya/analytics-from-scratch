"""Tests for lesson 08-01: warehouse layers.

python3 test_lesson.py                    checks exercise.sql
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.sql

The expected tables are computed here in plain Python straight from the raw
rows (latest load wins, dates and money parsed by hand), never with SQL.
Your models are built by warehouse.py on three kinds of data:
1. the committed data/*.csv,
2. a second raw layer built in memory with make_data.build(seed=2027), with
   other cities, counts and messy values, so typing out the answers cannot pass,
3. tiny hand-made raw tables for the edge cases: empty tables, a delivered
   order whose amount is still empty (NULL), a city and month with only
   cancelled orders (a real zero), an order whose customer has not landed, a
   thousands comma, the old date format and a customer who moved.
It also checks that the raw layer is unchanged after a build, that two
rebuilds give identical tables, and that both marts agree on total revenue.
"""
import os
import sqlite3
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402
import warehouse  # noqa: E402

if os.environ.get("CHECK_SOLUTION") == "1":
    SQL_FILE = os.path.join(HERE, "solution", "solution.sql")
else:
    SQL_FILE = os.path.join(HERE, "exercise.sql")

MODELS = ["stg_customers", "stg_orders", "fct_orders", "mart_city_month", "mart_customers"]
SECOND_SEED = 2027


# The reference answers, in plain Python.

def latest(rows, key):
    best = {}
    for r in rows:
        k = int(r[key])
        if k not in best or int(r["load_id"]) > int(best[k]["load_id"]):
            best[k] = r
    return best


def clean_city(text):
    text = (text or "").strip()
    return text.capitalize() if text else None


def parse_date(text):
    if len(text) >= 10 and text[2] == "/" and text[5] == "/":
        return "%s-%s-%s" % (text[6:10], text[3:5], text[0:2])
    return text[:10]


def parse_money(text):
    text = (text or "").strip().replace(",", "")
    return float(text) if text else None


def ref(tables):
    custs = {k: clean_city(r["city"]) for k, r in latest(tables["raw_customers"], "customer_id").items()}
    orders = {}
    for k, r in latest(tables["raw_orders"], "order_id").items():
        status = r["status"].strip().lower()
        amount = parse_money(r["amount"])
        discount = float(r["discount"])
        rev = (amount - discount) if (status == "delivered" and amount is not None) else None
        date = parse_date(r["ordered_at"])
        orders[k] = {"customer_id": int(r["customer_id"]), "city": custs.get(int(r["customer_id"])) or "Unknown",
                     "order_date": date, "order_month": date[:7], "status": status, "amount": amount,
                     "revenue": rev}
    city_month = {}
    for o in orders.values():
        g = city_month.setdefault((o["city"], o["order_month"]), [0, 0.0, 0])
        if o["status"] == "delivered":
            g[0] += 1
            if o["revenue"] is None:
                g[2] += 1
            else:
                g[1] += o["revenue"]
    per_cust = {}
    for o in orders.values():
        g = per_cust.setdefault(o["customer_id"], {"city": o["city"], "months": [], "orders": 0,
                                                   "delivered": 0, "revenue": 0.0})
        g["months"].append(o["order_month"])
        g["orders"] += 1
        if o["status"] == "delivered":
            g["delivered"] += 1
            g["revenue"] += o["revenue"] or 0.0
    return {"custs": custs, "orders": orders, "city_month": city_month, "per_cust": per_cust}


def committed():
    return warehouse.read_csv_tables()


class WarehouseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = warehouse.read_models(SQL_FILE)

    def build(self, tables):
        names = [n for n, _ in self.models]
        for m in MODELS:
            if m not in names:
                self.fail("model '%s' is missing from %s: keep every '-- model:' marker" % (m, os.path.basename(SQL_FILE)))
        for name, sql in self.models:
            if not sql.strip():
                self.fail("model '%s' is empty in %s: write its SELECT first" % (name, os.path.basename(SQL_FILE)))
        try:
            return warehouse.rebuild(self.models, tables)
        except (sqlite3.Error, ValueError) as e:
            self.fail("the models did not build: %s" % e)

    def check_all(self, tables, label):
        con = self.build(tables)
        r = ref(tables)
        # staging
        stg_c = {row["customer_id"]: row["city"] for row in warehouse.rows(con, "stg_customers")}
        self.assertEqual(len(stg_c), len(r["custs"]), "%s: stg_customers must have one row per customer_id (keep the highest load_id)" % label)
        self.assertEqual(stg_c, r["custs"], "%s: stg_customers city must be the latest load, trimmed, capitalised, and NULL when empty" % label)
        stg_o = {row["order_id"]: row for row in warehouse.rows(con, "stg_orders")}
        self.assertEqual(len(stg_o), len(r["orders"]), "%s: stg_orders must have one row per order_id, %d, not %d (keep the highest load_id)" % (label, len(r["orders"]), len(stg_o)))
        for oid, want in r["orders"].items():
            got = stg_o[oid]
            self.assertEqual(got["status"], want["status"], "%s: order %d status should be %r: the latest load, lower case" % (label, oid, want["status"]))
            self.assertEqual(got["order_date"], want["order_date"], "%s: order %d order_date should be %s: turn DD/MM/YYYY into YYYY-MM-DD" % (label, oid, want["order_date"]))
            if want["amount"] is None:
                self.assertIsNone(got["amount"], "%s: order %d has an empty amount, which must become NULL, not 0" % (label, oid))
            else:
                self.assertAlmostEqual(got["amount"], want["amount"], 2, "%s: order %d amount should be %.2f: remove the thousands comma and cast to REAL" % (label, oid, want["amount"]))
        # fact
        fct = {row["order_id"]: row for row in warehouse.rows(con, "fct_orders")}
        self.assertEqual(set(fct), set(r["orders"]), "%s: fct_orders must keep every order, also those whose customer has not landed (LEFT JOIN)" % label)
        for oid, want in r["orders"].items():
            self.assertEqual(fct[oid]["city"], want["city"], "%s: order %d city should be %r ('Unknown' when the customer is missing)" % (label, oid, want["city"]))
            if want["revenue"] is None:
                self.assertIsNone(fct[oid]["revenue"], "%s: order %d is not revenue (not delivered, or amount unknown), so revenue must be NULL" % (label, oid))
            else:
                self.assertAlmostEqual(fct[oid]["revenue"], want["revenue"], 2, "%s: order %d revenue should be amount - discount for a delivered order" % (label, oid))
        # marts
        cm = {(row["city"], row["order_month"]): row for row in warehouse.rows(con, "mart_city_month")}
        self.assertEqual(set(cm), set(r["city_month"]), "%s: mart_city_month needs one row per city and month that has any order" % label)
        for k, (n, rev, missing) in r["city_month"].items():
            self.assertEqual(cm[k]["delivered_orders"], n, "%s: %s delivered_orders should be %d" % (label, k, n))
            self.assertAlmostEqual(cm[k]["revenue"], round(rev, 2), 2, "%s: %s revenue should be %.2f (0, not NULL, when nothing was delivered)" % (label, k, rev))
            self.assertEqual(cm[k]["missing_amount"], missing, "%s: %s missing_amount should be %d delivered orders with no amount" % (label, k, missing))
        mc = {row["customer_id"]: row for row in warehouse.rows(con, "mart_customers")}
        self.assertEqual(set(mc), set(r["per_cust"]), "%s: mart_customers needs one row per customer who ordered" % label)
        for cid, g in r["per_cust"].items():
            got = mc[cid]
            self.assertEqual((got["city"], got["first_order_month"], got["orders"], got["delivered_orders"]),
                             (g["city"], min(g["months"]), g["orders"], g["delivered"]),
                             "%s: customer %d should be (city, first_order_month, orders, delivered_orders) = %r" % (label, cid, (g["city"], min(g["months"]), g["orders"], g["delivered"])))
            self.assertAlmostEqual(got["revenue"], round(g["revenue"], 2), 2, "%s: customer %d revenue should be %.2f, using the same revenue column as fct_orders" % (label, cid, g["revenue"]))
        # one definition of revenue
        total = sum(v[1] for v in r["city_month"].values())
        a = con.execute("SELECT COALESCE(SUM(revenue), 0) FROM mart_city_month").fetchone()[0]
        b = con.execute("SELECT COALESCE(SUM(revenue), 0) FROM mart_customers").fetchone()[0]
        self.assertAlmostEqual(a, b, 1, "%s: the two marts disagree on total revenue (%.2f vs %.2f): compute revenue once, in fct_orders" % (label, a, b))
        self.assertAlmostEqual(a, total, 1, "%s: total revenue should be %.2f" % (label, total))
        return con

    def test_committed_data(self):
        self.check_all(committed(), "committed data")

    def test_second_dataset(self):
        self.check_all(make_data.build(SECOND_SEED), "seed %d" % SECOND_SEED)

    def test_raw_is_never_edited_and_rebuild_is_deterministic(self):
        tables = committed()
        fresh = warehouse.load_raw(sqlite3.connect(":memory:"), tables)
        before = {t: warehouse.fingerprint(fresh, t) for t in warehouse.RAW}
        con1 = self.build(tables)
        con2 = self.build(tables)
        for t in warehouse.RAW:
            self.assertEqual(warehouse.fingerprint(con1, t), before[t], "%s changed during the build: models must only read raw" % t)
        for name in MODELS:
            self.assertEqual(warehouse.fingerprint(con1, name), warehouse.fingerprint(con2, name),
                             "%s differs between two builds from the same raw data: avoid anything that depends on run time or row order" % name)

    def test_edge_cases(self):
        empty = {"raw_orders": [], "raw_customers": []}
        con = self.build(empty)
        for name in MODELS:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM %s" % name).fetchone()[0], 0, "%s should be empty when raw is empty" % name)
        tiny = {
            "raw_customers": [
                {"load_id": 1, "customer_id": 1, "city": " pune", "signup_date": "2026-08-01"},
                {"load_id": 1, "customer_id": 2, "city": "NAGPUR ", "signup_date": "2026-08-01"},
                {"load_id": 4, "customer_id": 2, "city": "Thane", "signup_date": "2026-08-01"},  # moved
                {"load_id": 1, "customer_id": 3, "city": "", "signup_date": "2026-08-01"},
            ],
            "raw_orders": [
                {"load_id": 1, "order_id": 10, "customer_id": 1, "ordered_at": "05/08/2026 10:00", "status": "PENDING", "amount": "", "discount": "0.00"},
                {"load_id": 2, "order_id": 10, "customer_id": 1, "ordered_at": "05/08/2026 10:00", "status": "Delivered", "amount": "1,200.50", "discount": "0.50"},
                {"load_id": 2, "order_id": 11, "customer_id": 2, "ordered_at": "2026-08-06 09:00:00", "status": "cancelled", "amount": "300", "discount": "0.00"},
                {"load_id": 3, "order_id": 12, "customer_id": 1, "ordered_at": "2026-08-07 09:00:00", "status": "delivered", "amount": "", "discount": "0.00"},
                {"load_id": 3, "order_id": 13, "customer_id": 9, "ordered_at": "2026-09-01 09:00:00", "status": "delivered", "amount": "50", "discount": "5.00"},
                {"load_id": 3, "order_id": 14, "customer_id": 3, "ordered_at": "2026-09-02 09:00:00", "status": "delivered", "amount": "20.5", "discount": "0.00"},
            ],
        }
        con = self.check_all(tiny, "hand-made edge cases")
        cm = {(r["city"], r["order_month"]): r for r in warehouse.rows(con, "mart_city_month")}
        self.assertEqual((cm[("Pune", "2026-08")]["revenue"], cm[("Pune", "2026-08")]["missing_amount"]), (1200.0, 1),
                         "Pune August: 1,200.50 - 0.50 = 1,200.00 of revenue, and one delivered order with no amount yet")
        self.assertEqual((cm[("Thane", "2026-08")]["delivered_orders"], cm[("Thane", "2026-08")]["revenue"]), (0, 0),
                         "Thane August has only a cancelled order: 0 delivered and revenue 0, not NULL")
        self.assertAlmostEqual(cm[("Unknown", "2026-09")]["revenue"], 65.5, 2,
                               "September: order 13 has no customer row and order 14 has an empty city, so both are Unknown: 45 + 20.5")


if __name__ == "__main__":
    unittest.main(verbosity=2)
