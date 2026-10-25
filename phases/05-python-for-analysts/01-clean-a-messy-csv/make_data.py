"""Build data/orders_raw.csv: a messy synthetic export of 100 orders.

The mess is added on purpose: four date formats, currency strings with $ and INR
(including Indian lakh grouping like 1,20,000), stray spaces, blank cells, a
date written as TBD, and 6 duplicate rows. Run: python3 make_data.py
"""
import csv
import os
import random
from datetime import date, timedelta

random.seed(501)

CUSTOMERS = ["Asha Rao", "Ben Ortiz", "Chen Wei", "Divya Nair", "Eli Brooks", "Farah Khan", "Gopal Iyer", "Hana Sato"]
CITIES = ["Pune", "Austin", "Bengaluru", "Denver", "Mumbai", "Seattle"]
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%d-%b-%Y"]
FIELDS = ["order_id", "order_date", "customer", "city", "amount"]


def indian_grouping(n):
    """45000 -> 45,000 and 120000 -> 1,20,000."""
    s = str(n)
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def render_amount(currency, value):
    if currency == "USD":
        if random.random() < 0.6:
            return "$" + format(value, ",.2f")
        return "USD %.2f" % value
    if random.random() < 0.6:
        return "INR " + indian_grouping(int(value))
    return "Rs %d" % int(value)


def pad(s):
    return random.choice([" ", "  "]) + s + random.choice(["", " "])


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)

    base = []
    for i in range(1, 101):
        d = date(2026, 9, 1) + timedelta(days=random.randint(0, 29))
        currency = random.choice(["USD", "INR"])
        value = round(random.uniform(40, 2000), 2) if currency == "USD" else random.randint(20, 1500) * 100
        base.append({"order_id": str(1000 + i), "date": d, "customer": random.choice(CUSTOMERS),
                     "city": random.choice(CITIES), "currency": currency, "value": value})

    problem = random.sample(range(100), 12)
    blank_date, bad_date, blank_amount, blank_city = problem[:3], problem[3:5], problem[5:9], problem[9:12]

    raw = []
    for idx, b in enumerate(base):
        row = {
            "order_id": b["order_id"],
            "order_date": b["date"].strftime(random.choice(DATE_FORMATS)),
            "customer": b["customer"],
            "city": b["city"],
            "amount": render_amount(b["currency"], b["value"]),
        }
        if random.random() < 0.2:
            row["customer"] = pad(row["customer"])
        if random.random() < 0.1:
            row["customer"] = row["customer"].replace(" ", "  ", 1)
        if random.random() < 0.15:
            row["city"] = pad(row["city"])
        if idx in blank_date:
            row["order_date"] = ""
        if idx in bad_date:
            row["order_date"] = "TBD"
        if idx in blank_amount:
            row["amount"] = ""
        if idx in blank_city:
            row["city"] = ""
        raw.append(row)

    # 6 duplicates of clean rows: 3 exact copies, 3 that differ only in spacing or date format.
    clean_idx = [i for i in range(100) if i not in problem]
    for n, idx in enumerate(random.sample(clean_idx, 6)):
        dup = dict(raw[idx])
        if n == 3:
            dup["customer"] = "  " + dup["customer"].strip() + " "
        if n in (4, 5):
            iso = base[idx]["date"].strftime("%Y-%m-%d")
            other = base[idx]["date"].strftime("%d/%m/%Y")
            dup["order_date"] = other if dup["order_date"] == iso else iso
        raw.insert(random.randint(idx + 1, len(raw)), dup)

    with open(os.path.join(data, "orders_raw.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(raw)
    print("wrote", len(raw), "rows to", os.path.join(data, "orders_raw.csv"))


if __name__ == "__main__":
    main()
