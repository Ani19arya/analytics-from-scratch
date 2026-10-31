"""Build data/orders.csv and data/ai_summary.csv.

The summary is a saved fixture standing in for text an LLM wrote. No model was
called. It is written the way LLM prose usually is: half-year and quarter labels,
a year, amounts like $77.9k and changes like -0.5%. Most numbers are true. Three
are deliberately wrong, the way an LLM can state a number that is close but not
in the data. Run: python3 make_data.py
"""
import csv
import os
import random

DEFAULT_SEED = 603
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
REGIONS = ["North", "South", "West"]


def pct_change(new, old):
    return (new - old) / old * 100


def build(seed=DEFAULT_SEED):
    """Return {"orders": [...], "summary": [...], "fabricated": [(sentence_id, metric), ...]}.

    "fabricated" is the answer key: the numbers made wrong on purpose. It is never
    written to a CSV, so the checker has to find them from the data.
    """
    rng = random.Random(seed)
    rows = []
    for i in range(1, 241):
        m = rng.randint(0, 5)
        region = rng.choice(REGIONS)
        # gentle growth over the half year
        revenue = rng.randint(200, 900) + 40 * m
        rows.append({"order_id": i, "month": MONTHS[m], "region": region, "revenue": revenue})

    total = sum(r["revenue"] for r in rows)
    by_region = {g: sum(r["revenue"] for r in rows if r["region"] == g) for g in REGIONS}
    by_month = {m: sum(r["revenue"] for r in rows if r["month"] == m) for m in MONTHS}
    growth = pct_change(by_month["Jun"], by_month["Jan"])
    q1 = sum(by_month[m] for m in MONTHS[:3])
    q2 = sum(by_month[m] for m in MONTHS[3:])
    aov = total / len(rows)
    north_share = by_region["North"] / total * 100
    fake_growth = 25.0 if abs(growth - 25.0) > 1 else 20.0

    def k(x, places):
        return "%.*fk" % (places, x / 1000)

    # (sentence_id, metrics in order, sentence). Fabricated values are marked below.
    summary = [
        {"sentence_id": "S1", "metrics": "total_revenue;order_count",
         "sentence": "In H1 2026 the team booked $%s of revenue from %d orders." % (format(total, ","), len(rows))},
        {"sentence_id": "S2", "metrics": "avg_order_value",
         "sentence": "The average order was worth $%.2f." % aov},
        {"sentence_id": "S3", "metrics": "north_revenue;north_share_pct",
         # fabricated share: true share plus 6 points
         "sentence": "North was the largest region at $%s, or %.1f%% of revenue." % (format(by_region["North"], ","), north_share + 6)},
        {"sentence_id": "S4", "metrics": "south_revenue;west_revenue",
         # fabricated West: rounded up to a tidy number
         "sentence": "South brought in $%s and West $%s." % (k(by_region["South"], 0), format((by_region["West"] // 1000 + 1) * 1000, ","))},
        {"sentence_id": "S5", "metrics": "jan_revenue;jun_revenue;growth_pct",
         # fabricated growth: a plausible round figure
         "sentence": "Monthly revenue grew from $%s in January to $%s in June, a %.1f%% increase." % (format(by_month["Jan"], ","), format(by_month["Jun"], ","), fake_growth)},
        {"sentence_id": "S6", "metrics": "q2_revenue;q2_vs_q1_pct",
         "sentence": "Q2 revenue was $%s, a change of %+.1f%% on Q1." % (k(q2, 1), pct_change(q2, q1))},
        {"sentence_id": "S7", "metrics": "apr_revenue;apr_vs_mar_pct",
         "sentence": "April revenue was $%s, %+.1f%% on March." % (k(by_month["Apr"], 1), pct_change(by_month["Apr"], by_month["Mar"]))},
        {"sentence_id": "S8", "metrics": "region_count",
         "sentence": "All %d regions grew over the period." % len(REGIONS)},
    ]
    fabricated = [("S3", "north_share_pct"), ("S4", "west_revenue"), ("S5", "growth_pct")]
    return {"orders": rows, "summary": summary, "fabricated": fabricated}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    built = build()
    with open(os.path.join(data, "orders.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["order_id", "month", "region", "revenue"])
        w.writeheader()
        w.writerows(built["orders"])
    with open(os.path.join(data, "ai_summary.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sentence_id", "metrics", "sentence"])
        w.writeheader()
        w.writerows(built["summary"])
    print("wrote", data)


if __name__ == "__main__":
    main()
