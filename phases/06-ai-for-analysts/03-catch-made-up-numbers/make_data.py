"""Build data/orders.csv and data/ai_summary.csv.

The summary is a saved fixture standing in for text an LLM wrote. No API is called.
Most sentences use the true numbers. A few numbers are deliberately wrong, the way
an LLM can state a number that is close but not in the data. Run: python3 make_data.py
"""
import csv
import os
import random

random.seed(603)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
REGIONS = ["North", "South", "West"]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    rows = []
    for i in range(1, 241):
        m = random.randint(0, 5)
        region = random.choice(REGIONS)
        # gentle growth over the half year
        revenue = random.randint(200, 900) + 40 * m
        rows.append({"order_id": i, "month": MONTHS[m], "region": region, "revenue": revenue})
    with open(os.path.join(data, "orders.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["order_id", "month", "region", "revenue"])
        w.writeheader()
        w.writerows(rows)

    total = sum(r["revenue"] for r in rows)
    by_region = {g: sum(r["revenue"] for r in rows if r["region"] == g) for g in REGIONS}
    by_month = {m: sum(r["revenue"] for r in rows if r["month"] == m) for m in MONTHS}
    growth = (by_month["Jun"] - by_month["Jan"]) / by_month["Jan"] * 100
    aov = total / len(rows)
    north_share = by_region["North"] / total * 100

    # (sentence_id, metrics in order, sentence). Fabricated values are marked below.
    summary = [
        ("S1", "total_revenue;order_count",
         "Across the half year the team booked $%s of revenue from %d orders." % (format(total, ","), len(rows))),
        ("S2", "avg_order_value",
         "The average order was worth $%.2f." % aov),
        ("S3", "north_revenue;north_share_pct",
         # fabricated share: true share plus 6 points
         "North was the largest region at $%s, or %.1f%% of revenue." % (format(by_region["North"], ","), north_share + 6)),
        ("S4", "south_revenue;west_revenue",
         # fabricated West: rounded up to a tidy number
         "South brought in $%s and West $%s." % (format(by_region["South"], ","), format((by_region["West"] // 1000 + 1) * 1000, ","))),
        ("S5", "jan_revenue;jun_revenue;growth_pct",
         # fabricated growth: a plausible round figure
         "Monthly revenue grew from $%s in January to $%s in June, a %.1f%% increase." % (format(by_month["Jan"], ","), format(by_month["Jun"], ","), 25.0)),
        ("S6", "region_count",
         "All %d regions grew over the period." % len(REGIONS)),
    ]
    with open(os.path.join(data, "ai_summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sentence_id", "metrics", "sentence"])
        w.writerows(summary)
    print("wrote", data, "true growth %.1f%%" % growth, "north share %.1f%%" % north_share)


if __name__ == "__main__":
    main()
