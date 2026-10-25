"""Solution: clean a messy CSV export with the standard library only."""
import csv
import os
import re
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# The export mixes these. Slashes are day first: the file comes from the India office.
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%d-%b-%Y"]

# A currency marker, optional spaces, then digits with optional commas and decimals.
AMOUNT = re.compile(r"^(\$|USD|INR|RS\.?)\s*([\d,]+(?:\.\d+)?)$", re.IGNORECASE)
CURRENCY = {"$": "USD", "USD": "USD", "INR": "INR", "RS": "INR", "RS.": "INR"}


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def normalize_space(value):
    """Strip both ends and collapse runs of inner spaces to one."""
    return " ".join(value.split())


def parse_date(value):
    """Return the date as YYYY-MM-DD, or None if no known format fits."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def parse_amount(value):
    """Return (amount as float, 'USD' or 'INR'), or None if it is not a money string."""
    m = AMOUNT.match(value.strip())
    if not m:
        return None
    return float(m.group(2).replace(",", "")), CURRENCY[m.group(1).upper()]


def clean_rows(raw_rows):
    """Return (clean_rows, report). Rows are checked in a fixed order of reasons."""
    clean, seen = [], set()
    report = {"rows_in": len(raw_rows), "rows_out": 0, "trimmed_cells": 0, "filled_city": 0,
              "dropped": {}, "dropped_rows": []}

    def drop(order_id, reason):
        report["dropped"][reason] = report["dropped"].get(reason, 0) + 1
        report["dropped_rows"].append((order_id, reason))

    for raw in raw_rows:
        rec = {}
        for key, value in raw.items():
            tidy = normalize_space(value or "")
            if tidy != (value or ""):
                report["trimmed_cells"] += 1
            rec[key] = tidy

        if rec["order_date"] == "":
            drop(rec["order_id"], "blank_date")
            continue
        iso = parse_date(rec["order_date"])
        if iso is None:
            drop(rec["order_id"], "bad_date")
            continue
        if rec["amount"] == "":
            drop(rec["order_id"], "blank_amount")
            continue
        money = parse_amount(rec["amount"])
        if money is None:
            drop(rec["order_id"], "bad_amount")
            continue
        city = rec["city"]
        if city == "":
            city = "Unknown"
            report["filled_city"] += 1

        row = {"order_id": rec["order_id"], "order_date": iso, "customer": rec["customer"],
               "city": city, "amount": money[0], "currency": money[1]}
        key = tuple(row.values())
        if key in seen:
            drop(rec["order_id"], "duplicate")
            continue
        seen.add(key)
        clean.append(row)

    report["rows_out"] = len(clean)
    return clean, report


def main():
    clean, report = clean_rows(load_csv("orders_raw.csv"))
    print("rows in:", report["rows_in"], " rows out:", report["rows_out"])
    print("cells with stray spaces fixed:", report["trimmed_cells"])
    print("blank cities filled with Unknown:", report["filled_city"])
    for reason, n in sorted(report["dropped"].items()):
        print("dropped", reason, n)
    print("first clean row:", clean[0])


if __name__ == "__main__":
    main()
