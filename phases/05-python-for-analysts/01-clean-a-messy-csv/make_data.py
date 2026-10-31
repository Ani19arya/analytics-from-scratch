"""Build data/orders_raw.csv: a messy synthetic export of 100 orders.

The mess is added on purpose: four date formats, currency strings with $ and INR
(including Indian lakh grouping like 1,20,000), stray spaces, blank cells, a
date written as TBD, an amount that is only "$," (a copy and paste glitch),
6 duplicate rows, and one order exported twice with two different amounts
(a conflict). The currency follows the city: US cities pay in USD, Indian
cities in INR.

    python3 make_data.py            # writes data/orders_raw.csv for the default seed
    build(seed)                     # returns {"orders_raw": rows} without writing anything
    expected(seed)                  # what a correct cleaner returns, from the generator's own records
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 501

CUSTOMERS = ["Asha Rao", "Ben Ortiz", "Chen Wei", "Divya Nair", "Eli Brooks", "Farah Khan", "Gopal Iyer", "Hana Sato"]
CITY_CURRENCY = {"Pune": "INR", "Austin": "USD", "Bengaluru": "INR", "Denver": "USD", "Mumbai": "INR", "Seattle": "USD"}
CITIES = list(CITY_CURRENCY)
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


def render_amount(rng, currency, value):
    if currency == "USD":
        if rng.random() < 0.6:
            return "$" + format(value, ",.2f")
        return "USD %.2f" % value
    if rng.random() < 0.6:
        return "INR " + indian_grouping(int(value))
    return "Rs %d" % int(value)


def pad(rng, s):
    return rng.choice([" ", "  "]) + s + rng.choice(["", " "])


def _generate(seed):
    """Return (raw rows, tags, base orders). tags[i] = (what a correct cleaner does with raw row i, base index)."""
    rng = random.Random(seed)
    base = []
    for i in range(1, 101):
        d = date(2026, 9, 1) + timedelta(days=rng.randint(0, 29))
        city = rng.choice(CITIES)
        currency = CITY_CURRENCY[city]
        value = round(rng.uniform(40, 2000), 2) if currency == "USD" else float(rng.randint(20, 1500) * 100)
        base.append({"order_id": str(1000 + i), "date": d, "customer": rng.choice(CUSTOMERS),
                     "city": city, "currency": currency, "value": value})

    problem = rng.sample(range(100), 14)
    blank_date, bad_date, blank_amount, bad_amount = problem[:3], problem[3:5], problem[5:9], problem[9:10]
    blank_city, conflict = problem[10:13], problem[13]

    raw, tags = [], []
    for idx, b in enumerate(base):
        row = {
            "order_id": b["order_id"],
            "order_date": b["date"].strftime(rng.choice(DATE_FORMATS)),
            "customer": b["customer"],
            "city": b["city"],
            "amount": render_amount(rng, b["currency"], b["value"]),
        }
        if rng.random() < 0.2:
            row["customer"] = pad(rng, row["customer"])
        if rng.random() < 0.1:
            row["customer"] = row["customer"].replace(" ", "  ", 1)
        if rng.random() < 0.15:
            row["city"] = pad(rng, row["city"])
        tag = "ok"
        if idx in blank_date:
            row["order_date"], tag = "", "blank_date"
        if idx in bad_date:
            row["order_date"], tag = "TBD", "bad_date"
        if idx in blank_amount:
            row["amount"], tag = "", "blank_amount"
        if idx in bad_amount:
            row["amount"], tag = "$,", "bad_amount"
        if idx in blank_city:
            row["city"] = ""
        if idx == conflict:
            tag = "conflict"
        raw.append(row)
        tags.append((tag, idx))

    # The conflict: the same order exported again with a different amount.
    b = base[conflict]
    second = dict(raw[conflict])
    new_value = round(b["value"] * 1.1, 2) if b["currency"] == "USD" else b["value"] + 1000
    second["amount"] = render_amount(rng, b["currency"], new_value)
    pos = rng.randint(conflict + 1, len(raw))
    raw.insert(pos, second)
    tags.insert(pos, ("conflict", conflict))

    # 6 duplicates of clean rows: 3 exact copies, 3 that differ only in spacing or date format.
    clean_idx = [i for i in range(100) if i not in problem]
    for n, idx in enumerate(rng.sample(clean_idx, 6)):
        src = tags.index(("ok", idx))
        dup = dict(raw[src])
        if n == 3:
            dup["customer"] = "  " + dup["customer"].strip() + " "
        if n in (4, 5):
            iso = base[idx]["date"].strftime("%Y-%m-%d")
            other = base[idx]["date"].strftime("%d/%m/%Y")
            dup["order_date"] = other if dup["order_date"] == iso else iso
        pos = rng.randint(src + 1, len(raw))
        raw.insert(pos, dup)
        tags.insert(pos, ("duplicate", idx))
    return raw, tags, base


def build(seed=DEFAULT_SEED):
    """The raw export for this seed: {"orders_raw": list of dicts, every value a string}."""
    raw, _, _ = _generate(seed)
    return {"orders_raw": raw}


def expected(seed=DEFAULT_SEED):
    """What a correct cleaner returns for build(seed), from the generator's own records, not from any cleaner.

    rows_in: raw row count. clean: the clean rows in file order. dropped: reason -> count.
    """
    raw, tags, base = _generate(seed)
    clean, dropped = [], {}
    for (tag, idx), row in zip(tags, raw):
        if tag != "ok":
            dropped[tag] = dropped.get(tag, 0) + 1
            continue
        b = base[idx]
        clean.append({"order_id": b["order_id"], "order_date": b["date"].isoformat(),
                      "customer": b["customer"], "city": b["city"] if row["city"] else "Unknown",
                      "amount": b["value"], "currency": b["currency"]})
    return {"rows_in": len(raw), "clean": clean, "dropped": dropped}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    raw = build()["orders_raw"]
    with open(os.path.join(data, "orders_raw.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(raw)
    print("wrote", len(raw), "rows to", os.path.join(data, "orders_raw.csv"))


if __name__ == "__main__":
    main()
