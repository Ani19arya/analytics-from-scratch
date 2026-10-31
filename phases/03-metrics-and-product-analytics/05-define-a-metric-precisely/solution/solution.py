"""Lesson 05 solution: define a metric precisely, as a spec that code can run."""
import csv
import datetime

# The written definition, agreed with finance, turned into values code can check.
SPEC = {
    "name": "monthly_active_customers",
    "counts": "distinct customer_id",
    "utc_offset_minutes": 330,           # India Standard Time, UTC+05:30, no daylight saving
    "statuses": ["delivered"],
    "exclude_full_refunds": True,        # refunded_amount > 0 and refunded_amount >= amount
    "exclude_test_accounts": True,       # customers.is_test = 1
    "keep_deleted_customers": True,      # deleted or erased accounts still count for months they were active
}

# What the growth dashboard has been counting: any order created in the UTC month.
DASHBOARD_SPEC = {
    "name": "customers_with_any_order_utc",
    "counts": "distinct customer_id",
    "utc_offset_minutes": 0,
    "statuses": ["delivered", "cancelled"],
    "exclude_full_refunds": False,
    "exclude_test_accounts": False,
    "keep_deleted_customers": True,
}


def parse_utc(text):
    """'2026-10-01T18:45:00Z' -> an aware datetime in UTC."""
    return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)


def local_month(created_at, offset_minutes):
    """The 'YYYY-MM' the order falls in, on a clock offset_minutes ahead of UTC."""
    local = parse_utc(created_at) + datetime.timedelta(minutes=offset_minutes)
    return local.strftime("%Y-%m")


def read_customers(path):
    out = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            out[int(row["customer_id"])] = {"customer_id": int(row["customer_id"]), "email": row["email"],
                                            "is_test": int(row["is_test"]),
                                            "deleted_at": row["deleted_at"] or None}
    return out


def read_orders(path):
    out = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            out.append({"order_id": int(row["order_id"]), "customer_id": int(row["customer_id"]),
                        "created_at": row["created_at"], "status": row["status"],
                        "amount": float(row["amount"]),
                        "refunded_amount": float(row["refunded_amount"]) if row["refunded_amount"] else 0.0})
    return out


def is_full_refund(order):
    return order["refunded_amount"] > 0 and order["refunded_amount"] >= order["amount"]


def qualifies(order, customer, spec):
    """Does this order make its customer active under the spec (ignoring the month)?
    customer is the customers row, or None if the row was erased."""
    if order["status"] not in spec["statuses"]:
        return False
    if spec["exclude_full_refunds"] and is_full_refund(order):
        return False
    if spec["exclude_test_accounts"] and customer is not None and customer["is_test"] == 1:
        return False
    if not spec["keep_deleted_customers"] and (customer is None or customer["deleted_at"] is not None):
        return False
    return True


def active_customers(orders, customers, month, spec):
    """The set of customer_ids active in `month` ('YYYY-MM') under the spec."""
    active = set()
    for order in orders:
        if local_month(order["created_at"], spec["utc_offset_minutes"]) != month:
            continue
        if qualifies(order, customers.get(order["customer_id"]), spec):
            active.add(order["customer_id"])
    return active


def reconcile(orders, customers, month, steps):
    """steps: a list of (label, spec). Return [(label, count)] in the same order."""
    return [(label, len(active_customers(orders, customers, month, spec))) for label, spec in steps]


def bridge_steps():
    """From the dashboard definition to the spec, changing one rule at a time."""
    steps = [("dashboard: any order, UTC month", dict(DASHBOARD_SPEC))]
    current = dict(DASHBOARD_SPEC)
    for label, key in (("+ India time month", "utc_offset_minutes"), ("+ delivered only", "statuses"),
                       ("+ no full refunds", "exclude_full_refunds"), ("+ no test accounts", "exclude_test_accounts")):
        current = dict(current)
        current[key] = SPEC[key]
        steps.append((label, current))
    return steps


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    customers = read_customers(os.path.join(here, "..", "data", "customers.csv"))
    orders = read_orders(os.path.join(here, "..", "data", "orders.csv"))
    for label, count in reconcile(orders, customers, "2026-10", bridge_steps()):
        print("%-32s %d" % (label, count))
