"""Tests for lesson 05: define a metric precisely. Run: python3 test_lesson.py
With CHECK_SOLUTION=1 the tests run against solution/solution.py instead.

Expected answers are computed here from the raw CSV rows with a separate
implementation (it converts time zones with astimezone, not by adding minutes).
The checks run on the committed data, on a second dataset built with another seed,
under three different specs, and on small hand-made orders that each test one edge:
a month boundary in India time, a cancelled order, a full refund, a partial refund,
a free meal, a blank refund (NULL), a test account, a deleted and an erased customer."""
import csv
import datetime
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CUSTOMERS = os.path.join(HERE, "data", "customers.csv")
ORDERS = os.path.join(HERE, "data", "orders.csv")
MONTH = "2026-10"
OTHER_SEED = 77
if os.environ.get("CHECK_SOLUTION") == "1":
    TARGET = os.path.join(HERE, "solution", "solution.py")
else:
    TARGET = os.path.join(HERE, "exercise.py")


def load():
    spec = importlib.util.spec_from_file_location("lesson_module", TARGET)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load()
sys.path.insert(0, HERE)
import make_data  # noqa: E402

FINANCE = {"utc_offset_minutes": 330, "statuses": ["delivered"], "exclude_full_refunds": True,
           "exclude_test_accounts": True, "keep_deleted_customers": True}
DASHBOARD = {"utc_offset_minutes": 0, "statuses": ["delivered", "cancelled"], "exclude_full_refunds": False,
             "exclude_test_accounts": False, "keep_deleted_customers": True}
CURRENT_ONLY = dict(FINANCE, keep_deleted_customers=False)


def reference(customers_path, orders_path, month, spec):
    """Independent count: read the raw text, convert with astimezone, apply each rule."""
    with open(customers_path, newline="") as f:
        cust = {r["customer_id"]: r for r in csv.DictReader(f)}
    zone = datetime.timezone(datetime.timedelta(minutes=spec["utc_offset_minutes"]))
    active = set()
    with open(orders_path, newline="") as f:
        for r in csv.DictReader(f):
            when = datetime.datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).astimezone(zone)
            if "%04d-%02d" % (when.year, when.month) != month:
                continue
            if r["status"] not in spec["statuses"]:
                continue
            amount = float(r["amount"])
            refunded = float(r["refunded_amount"] or 0)
            if spec["exclude_full_refunds"] and refunded > 0 and refunded >= amount:
                continue
            c = cust.get(r["customer_id"])
            if spec["exclude_test_accounts"] and c is not None and c["is_test"] == "1":
                continue
            if not spec["keep_deleted_customers"] and (c is None or c["deleted_at"] != ""):
                continue
            active.add(int(r["customer_id"]))
    return active


def order(cid, created_at, status="delivered", amount=500.0, refunded=0.0, oid=1):
    return {"order_id": oid, "customer_id": cid, "created_at": created_at, "status": status,
            "amount": amount, "refunded_amount": refunded}


class TestSpec(unittest.TestCase):
    def test_spec_says_what_the_sentence_says(self):
        why = {"utc_offset_minutes": "India time is UTC+05:30, which is 330 minutes",
               "statuses": "only delivered orders count",
               "exclude_full_refunds": "orders refunded in full do not count",
               "exclude_test_accounts": "staff test accounts are not customers",
               "keep_deleted_customers": "deleted and erased customers still count for months they were active"}
        for key, want in FINANCE.items():
            got = m.SPEC[key]
            if key == "statuses":
                got = sorted(got) if got is not None else got
            self.assertEqual(got, want, "SPEC[%r] should be %r: %s." % (key, want, why[key]))


class TestTime(unittest.TestCase):
    def test_parse_utc(self):
        t = m.parse_utc("2026-10-01T18:45:00Z")
        self.assertEqual(t, datetime.datetime(2026, 10, 1, 18, 45, tzinfo=datetime.timezone.utc),
                         "return an aware datetime in UTC")

    def test_month_edges_in_india(self):
        cases = [("2026-09-30T18:29:59Z", "2026-09"), ("2026-09-30T18:30:00Z", "2026-10"),
                 ("2026-10-31T18:29:59Z", "2026-10"), ("2026-10-31T18:30:00Z", "2026-11")]
        for created, want in cases:
            self.assertEqual(m.local_month(created, 330), want,
                             "%s UTC is %s in India (UTC+05:30)" % (created, want))

    def test_month_in_utc(self):
        self.assertEqual(m.local_month("2026-09-30T18:30:00Z", 0), "2026-09")
        self.assertEqual(m.local_month("2026-12-31T23:59:59Z", 0), "2026-12")
        self.assertEqual(m.local_month("2026-12-31T23:59:59Z", 330), "2027-01", "the year changes too")


class TestRules(unittest.TestCase):
    real = {"customer_id": 1, "email": "a@example.com", "is_test": 0, "deleted_at": None}
    tester = {"customer_id": 2, "email": "qa2@tiffinbell.test", "is_test": 1, "deleted_at": None}
    deleted = {"customer_id": 3, "email": "c@example.com", "is_test": 0, "deleted_at": "2026-10-20T10:00:00Z"}

    def test_full_refund(self):
        self.assertTrue(m.is_full_refund(order(1, "2026-10-05T07:00:00Z", amount=500.0, refunded=500.0)))
        self.assertFalse(m.is_full_refund(order(1, "2026-10-05T07:00:00Z", amount=500.0, refunded=200.0)),
                         "a partial refund still leaves a delivered meal")
        self.assertFalse(m.is_full_refund(order(1, "2026-10-05T07:00:00Z", amount=0.0, refunded=0.0)),
                         "a free meal (amount 0, refunded 0) was not refunded")
        self.assertFalse(m.is_full_refund(order(1, "2026-10-05T07:00:00Z", amount=500.0, refunded=0.0)))

    def test_qualifies(self):
        o = order(1, "2026-10-05T07:00:00Z")
        self.assertTrue(m.qualifies(o, self.real, FINANCE))
        self.assertFalse(m.qualifies(order(1, "2026-10-05T07:00:00Z", status="cancelled"), self.real, FINANCE))
        self.assertTrue(m.qualifies(order(1, "2026-10-05T07:00:00Z", status="cancelled"), self.real, DASHBOARD),
                        "the dashboard spec counts cancelled orders: read the statuses from the spec")
        self.assertFalse(m.qualifies(o, self.tester, FINANCE), "test accounts are excluded")
        self.assertTrue(m.qualifies(o, self.tester, DASHBOARD))
        self.assertTrue(m.qualifies(o, self.deleted, FINANCE), "a deleted customer still counts")
        self.assertTrue(m.qualifies(o, None, FINANCE), "an erased customer (no row) is still a real customer")
        self.assertFalse(m.qualifies(o, self.deleted, CURRENT_ONLY))
        self.assertFalse(m.qualifies(o, None, CURRENT_ONLY))


class TestHandMade(unittest.TestCase):
    """One customer per edge. Customer 9 has no row (erased)."""

    customers = {
        1: {"customer_id": 1, "email": "a@example.com", "is_test": 0, "deleted_at": None},
        2: {"customer_id": 2, "email": "b@example.com", "is_test": 0, "deleted_at": None},
        3: {"customer_id": 3, "email": "c@example.com", "is_test": 0, "deleted_at": None},
        4: {"customer_id": 4, "email": "d@example.com", "is_test": 0, "deleted_at": None},
        5: {"customer_id": 5, "email": "e@example.com", "is_test": 0, "deleted_at": None},
        6: {"customer_id": 6, "email": "qa6@tiffinbell.test", "is_test": 1, "deleted_at": None},
        7: {"customer_id": 7, "email": "g@example.com", "is_test": 0, "deleted_at": "2026-11-02T09:00:00Z"},
        8: {"customer_id": 8, "email": "h@example.com", "is_test": 0, "deleted_at": None},
    }
    orders = [
        order(1, "2026-09-30T19:00:00Z", oid=1),                                 # 1 Oct 00:30 India: counts
        order(2, "2026-10-31T19:00:00Z", oid=2),                                 # 1 Nov 00:30 India: not October
        order(3, "2026-10-10T07:00:00Z", status="cancelled", oid=3),             # cancelled
        order(4, "2026-10-10T07:00:00Z", amount=400.0, refunded=400.0, oid=4),   # full refund
        order(5, "2026-10-10T07:00:00Z", amount=0.0, refunded=0.0, oid=5),       # free meal: counts
        order(6, "2026-10-10T07:00:00Z", oid=6),                                 # test account
        order(7, "2026-10-10T07:00:00Z", oid=7),                                 # deleted later: counts
        order(8, "2026-10-10T07:00:00Z", amount=400.0, refunded=100.0, oid=8),   # partial refund: counts
        order(8, "2026-10-12T07:00:00Z", oid=9),                                 # same customer again
        order(9, "2026-10-15T07:00:00Z", oid=10),                                # erased customer: counts
    ]

    def test_finance_spec(self):
        self.assertEqual(m.active_customers(self.orders, self.customers, MONTH, FINANCE), {1, 5, 7, 8, 9},
                         "each customer here tests one rule; see the comments on the orders in TestHandMade")

    def test_dashboard_spec(self):
        self.assertEqual(m.active_customers(self.orders, self.customers, MONTH, DASHBOARD), {2, 3, 4, 5, 6, 7, 8, 9},
                         "in UTC, customer 1's order is in September and customer 2's is in October")

    def test_empty(self):
        self.assertEqual(m.active_customers([], self.customers, MONTH, FINANCE), set(), "no orders, no actives")
        self.assertEqual(m.active_customers(self.orders, self.customers, "2026-12", FINANCE), set())

    def test_distinct(self):
        got = m.active_customers(self.orders, self.customers, MONTH, FINANCE)
        self.assertIsInstance(got, set, "return a set, so a customer with two orders counts once")

    def test_reconcile(self):
        steps = [("finance", FINANCE), ("dashboard", DASHBOARD)]
        self.assertEqual(list(m.reconcile(self.orders, self.customers, MONTH, steps)),
                         [("finance", 5), ("dashboard", 8)])
        self.assertEqual(list(m.reconcile(self.orders, self.customers, MONTH, [])), [])


class ReadEdges(unittest.TestCase):
    def test_blank_refund_and_deleted_at(self):
        tmp = tempfile.mkdtemp()
        try:
            make_data.write_all(tmp, {
                "customers": [{"customer_id": 1, "email": "a@example.com", "is_test": 0, "deleted_at": ""}],
                "orders": [{"order_id": 1, "customer_id": 1, "created_at": "2026-10-02T07:00:00Z",
                            "status": "delivered", "amount": 300, "refunded_amount": ""}]})
            cust = m.read_customers(os.path.join(tmp, "customers.csv"))
            self.assertIsNone(cust[1]["deleted_at"], "a blank deleted_at means the account was not deleted: None")
            self.assertEqual(cust[1]["is_test"], 0)
            orders = m.read_orders(os.path.join(tmp, "orders.csv"))
            self.assertEqual(orders[0]["refunded_amount"], 0.0, "a blank refund (NULL) means no refund: 0.0")
            self.assertEqual(orders[0]["customer_id"], 1)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class OnData:
    def test_three_specs(self):
        customers = m.read_customers(self.customers_path)
        orders = m.read_orders(self.orders_path)
        for name, spec in (("finance", FINANCE), ("dashboard", DASHBOARD), ("current only", CURRENT_ONLY)):
            want = reference(self.customers_path, self.orders_path, MONTH, spec)
            got = m.active_customers(orders, customers, MONTH, dict(spec, name=name))
            self.assertEqual(got, want, "%s spec: expected %d customers, got %d" % (name, len(want), len(got)))

    def test_bridge(self):
        customers = m.read_customers(self.customers_path)
        orders = m.read_orders(self.orders_path)
        steps = m.bridge_steps()
        got = list(m.reconcile(orders, customers, MONTH, steps))
        self.assertEqual([label for label, _ in got], [label for label, _ in steps])
        self.assertEqual(got[0][1], len(reference(self.customers_path, self.orders_path, MONTH, DASHBOARD)))
        self.assertEqual(got[-1][1], len(reference(self.customers_path, self.orders_path, MONTH, FINANCE)),
                         "the last step of the bridge must land on the finance number")


class TestOnData(OnData, unittest.TestCase):
    customers_path = CUSTOMERS
    orders_path = ORDERS


class TestOnSecondDataset(OnData, unittest.TestCase):
    """Same checks on data built with another seed, so hard-coded answers fail."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        make_data.write_all(cls.tmp, make_data.build(seed=OTHER_SEED))
        cls.customers_path = os.path.join(cls.tmp, "customers.csv")
        cls.orders_path = os.path.join(cls.tmp, "orders.csv")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_differs(self):
        self.assertNotEqual(reference(self.customers_path, self.orders_path, MONTH, FINANCE),
                            reference(CUSTOMERS, ORDERS, MONTH, FINANCE), "the second dataset should differ")


if __name__ == "__main__":
    unittest.main()
