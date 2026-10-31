"""Trial against paid churn within 90 days. Python 3.9+, standard library only."""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(HERE, "data", "customers.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    for start in ("trial", "paid"):
        group = [r for r in rows if r["start_type"] == start]
        churned = sum(r["churned"] == "1" for r in group)
        print("%s: %d of %d churned (%.1f%%)" % (start, churned, len(group), 100.0 * churned / len(group)))


if __name__ == "__main__":
    main()
