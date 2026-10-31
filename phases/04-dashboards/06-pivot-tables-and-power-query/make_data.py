"""Build two synthetic monthly sales exports for Tidewater Outdoor.

Run from the lesson folder: python3 make_data.py
Writes data/sales_2026-09.csv and data/sales_2026-10.csv, one row per receipt.
The data is synthetic and deterministic (fixed seed).

Each month is a clean list of receipts that is then exported in a messy STYLE, the way
a point of sale system and a tired colleague might write it: title lines above the
header, a renamed column, a different date or money format, store names in mixed case
with stray spaces, blank lines, a repeated line and a Total row at the bottom.

    build(seed)   -> {"sales_2026-09": raw rows, "sales_2026-10": raw rows}
                     (raw rows are lists of text cells, as csv.reader gives them)
    truth(seed)   -> {"sales_2026-09": clean rows, ...}, the receipts before the mess
    styles(seed)  -> the export style used for each month
    month_raw(seed, year, month), month_truth(...), month_style(...): any single month,
                     for example next month's file

The default seed gives September and October different styles. Another seed picks
other styles, so cleaning steps that only fit the committed files fail on it.
"""
import csv
import os
import random
from datetime import date, timedelta

DEFAULT_SEED = 406
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
MONTHS = [(2026, 9), (2026, 10)]
STORES = ["Harbor Point", "North Mall", "Old Town", "Riverside"]
PRODUCTS = {"Tents": (120, 480), "Sleeping Bags": (45, 190), "Boots": (60, 210), "Jackets": (55, 260),
            "Stoves": (30, 140)}
HEADERS = {"units": ["Units", "Qty"], "revenue": ["Revenue", "Sales"], "store": ["Store", "Store name"]}
DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y"]


def key(year, month):
    return "sales_%04d-%02d" % (year, month)


def month_style(seed, year, month):
    """The export style of one month. The default seed forces September and October apart."""
    rng = random.Random(seed * 7919 + year * 12 + month)
    st = {"title_lines": rng.randint(0, 2), "units": rng.choice(HEADERS["units"]),
          "revenue": rng.choice(HEADERS["revenue"]), "store": rng.choice(HEADERS["store"]),
          "date_format": rng.choice(DATE_FORMATS), "dollar": rng.random() < 0.5, "total_row": rng.random() < 0.8}
    if seed == DEFAULT_SEED and (year, month) == (2026, 9):
        st.update(title_lines=0, units="Units", revenue="Revenue", store="Store", date_format="%Y-%m-%d",
                  dollar=True, total_row=True)
    if seed == DEFAULT_SEED and (year, month) == (2026, 10):
        st.update(title_lines=2, units="Qty", revenue="Sales", store="Store name", date_format="%d/%m/%Y",
                  dollar=False, total_row=True)
    return st


def month_truth(seed, year, month):
    """The receipts of one month as they really happened, before any export mess."""
    rng = random.Random(seed * 104729 + year * 12 + month)
    first = date(year, month, 1)
    days = (date(year + (month == 12), month % 12 + 1, 1) - first).days
    rows = []
    for i in range(rng.randint(110, 150)):
        product = rng.choice(sorted(PRODUCTS))
        low, high = PRODUCTS[product]
        units = rng.choice([1, 1, 1, 2, 2, 3])
        price = rng.randint(low, high) - 0.01
        if rng.random() < 0.03:
            price = 0.0  # a warranty swap: a real receipt with zero revenue
        d = first + timedelta(days=rng.randrange(days))
        rows.append({"Receipt": "R%02d%02d-%04d" % (year % 100, month, i + 1), "Date": d.isoformat(),
                     "Month": d.isoformat()[:7], "Store": rng.choice(STORES), "Product": product,
                     "Units": units, "Revenue": round(units * price, 2)})
    return rows


def money(value, dollar):
    return "${:,.2f}".format(value) if dollar else "%.2f" % value


def messy_store(rng, name):
    return rng.choice([name, name, name.lower(), name.upper(), " " + name, name + "  ",
                       name.replace(" ", "  ")])


def month_raw(seed, year, month):
    """One month's export: the true receipts written in that month's messy style."""
    rng = random.Random(seed * 1299709 + year * 12 + month)
    rows, st = month_truth(seed, year, month), month_style(seed, year, month)
    raw = []
    if st["title_lines"] >= 1:
        raw.append(["Tidewater Outdoor point of sale export"])
    if st["title_lines"] >= 2:
        raw.append(["Generated automatically, do not edit"])
    raw.append(["Receipt", "Date", st["store"], "Product", st["units"], st["revenue"]])
    lines = []
    for r in rows:
        d = date.fromisoformat(r["Date"])
        lines.append([r["Receipt"], d.strftime(st["date_format"]), messy_store(rng, r["Store"]),
                      r["Product"] if rng.random() < 0.9 else " " + r["Product"] + " ",
                      str(r["Units"]), money(r["Revenue"], st["dollar"])])
    for _ in range(rng.randint(1, 3)):          # the export repeats a few lines, right after themselves
        i = rng.randrange(len(lines))
        lines.insert(i + 1, list(lines[i]))
    for _ in range(rng.randint(1, 2)):          # and leaves blank lines
        lines.insert(rng.randrange(len(lines)), ["", "", "", "", "", ""])
    raw.extend(lines)
    if st["total_row"]:
        total_units = sum(r["Units"] for r in rows)
        total = round(sum(r["Revenue"] for r in rows), 2)
        raw.append(["Total", "", "", "", str(total_units), money(total, st["dollar"])])
    return raw


def styles(seed=DEFAULT_SEED):
    return {key(y, m): month_style(seed, y, m) for y, m in MONTHS}


def truth(seed=DEFAULT_SEED):
    return {key(y, m): month_truth(seed, y, m) for y, m in MONTHS}


def build(seed=DEFAULT_SEED):
    return {key(y, m): month_raw(seed, y, m) for y, m in MONTHS}


def main():
    os.makedirs(DATA, exist_ok=True)
    for name, raw in build().items():
        with open(os.path.join(DATA, name + ".csv"), "w", newline="") as f:
            csv.writer(f).writerows(raw)
        print("wrote %d lines to data/%s.csv" % (len(raw), name))


if __name__ == "__main__":
    main()
