"""Build the synthetic purchases table for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/purchases.csv: the October 2026 purchase log of a Tiffinbell
kitchen, typed in by hand. The data is synthetic and deterministic: the same
seed always gives the same rows. Tests call build(seed) for a second dataset.

The amount and category cells are messy on purpose, the way hand-typed sheets
are: thousands commas, spaces, an "Rs" prefix, blanks, "n/a", a refund written
as a negative number, a typo, and categories in mixed case.
"""
import csv
import datetime
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEED = 6
ITEMS = {
    "vegetables": ["onions", "tomatoes", "potatoes", "spinach", "green chillies"],
    "rice and grains": ["basmati rice", "toor dal", "wheat flour"],
    "dairy": ["milk", "paneer", "curd"],
    "gas": ["gas cylinder"],
    "packaging": ["food boxes", "paper bags"],
}
# How often each category comes up: vegetables are bought most days, gas rarely.
WEIGHTED = ["vegetables"] * 4 + ["rice and grains"] * 2 + ["dairy"] * 2 + ["packaging"] * 2 + ["gas"]
MESSY = ["comma", "spaces", "rs", "blank", "na", "refund", "typo"]


def money(value):
    return "%.2f" % value


def messy_amount(kind, value, rng):
    if kind == "comma":
        value = rng.uniform(1000, 2400)  # a bulk purchase
        return "{:,.2f}".format(value)
    if kind == "spaces":
        return " %d " % round(value)
    if kind == "rs":
        return "Rs %d" % round(value)
    if kind == "blank":
        return ""
    if kind == "na":
        return rng.choice(["n/a", "N/A"])
    if kind == "refund":
        return "-" + money(rng.uniform(50, 200))
    if kind == "typo":
        return "%dO" % rng.randint(10, 99)  # the letter O typed instead of a zero
    return money(value)


def messy_category(category, rng):
    r = rng.random()
    if r < 0.15:
        return category.capitalize()
    if r < 0.22:
        return category.upper()
    if r < 0.30:
        return category + " "
    return category


def build(seed=DEFAULT_SEED):
    """Return {"purchases": [rows]} where every value is text, exactly as in the CSV."""
    rng = random.Random(seed)
    n = rng.randint(70, 90)
    kinds = ["clean"] * n
    # Every kind of mess appears at least once, a few appear more often.
    spots = rng.sample(range(n), len(MESSY) + 8)
    for i, spot in enumerate(spots):
        kinds[spot] = MESSY[i] if i < len(MESSY) else rng.choice(["comma", "spaces", "rs", "blank"])
    rows = []
    for i in range(n):
        category = rng.choice(WEIGHTED)
        value = rng.uniform(1800, 2600) if category == "gas" else rng.uniform(60, 900)
        rows.append(
            {
                "date": (datetime.date(2026, 10, 1) + datetime.timedelta(days=i * 31 // n)).isoformat(),
                "item": rng.choice(ITEMS[category]),
                "category": messy_category(category, rng),
                "amount": messy_amount(kinds[i], value, rng),
            }
        )
    return {"purchases": rows}


def main():
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    for name, rows in build().items():
        with open(os.path.join(HERE, "data", name + ".csv"), "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print("wrote %d rows to data/%s.csv" % (len(rows), name))


if __name__ == "__main__":
    main()
