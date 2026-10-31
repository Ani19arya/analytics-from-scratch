"""Build data/experiment.csv and data/coupons.csv for the statistics interview round.

The story: Harbor Mealkits, a fictional meal kit delivery startup, hands interview candidates
two small tables and asks about p-values, power and Simpson's paradox.

experiment.csv: user_id, group, converted.
    A two-week test of a new checkout page. Each visitor was assigned at random to
    control (old page) or treatment (new page). converted is 1 if they ordered.
coupons.csv: customer_id, customer_type, coupon, reordered.
    Customers from one month. customer_type is new or returning. coupon is yes when the
    customer got a 20%-off coupon for their next box; the team sent most coupons to new
    customers. reordered is 1 if they ordered again within 30 days.

Each seed draws its own true effects, so the p-value, the power and whether the coupon
table reverses can differ between seeds.
The data is synthetic and deterministic (fixed seed). Harbor Mealkits is invented.
Run from the lesson folder: python3 make_data.py
In code: build(seed) returns {"experiment": rows, "coupons": rows} without writing files.
"""
import csv
import os
import random

SEED = 8
HERE = os.path.dirname(os.path.abspath(__file__))
EXPERIMENT_HEADER = ["user_id", "group", "converted"]
COUPONS_HEADER = ["customer_id", "customer_type", "coupon", "reordered"]


def build_experiment(rng):
    base = rng.uniform(0.09, 0.11)
    lift = rng.uniform(0.0, 0.03)  # this seed's true lift, in proportion (0.015 = 1.5 points)
    rows = []
    for uid in range(1, 1601):
        group = "treatment" if rng.random() < 0.5 else "control"
        p = base + (lift if group == "treatment" else 0.0)
        rows.append(["U%04d" % uid, group, int(rng.random() < p)])
    return rows


def build_coupons(rng):
    # (customer type, number of customers, share given a coupon, reorder rate without a coupon)
    plan = [
        ("new", rng.randint(380, 420), rng.uniform(0.70, 0.85), rng.uniform(0.18, 0.26)),
        ("returning", rng.randint(230, 270), rng.uniform(0.15, 0.30), rng.uniform(0.52, 0.62)),
    ]
    uplift = rng.uniform(0.02, 0.09)  # what a coupon really adds, the same in both types
    rows, cid = [], 0
    for ctype, n, coupon_share, base in plan:
        for _ in range(n):
            cid += 1
            coupon = rng.random() < coupon_share
            p = base + (uplift if coupon else 0.0)
            rows.append(["C%04d" % cid, ctype, "yes" if coupon else "no", int(rng.random() < p)])
    return rows


def build(seed=SEED):
    rng = random.Random(seed)
    return {"experiment": build_experiment(rng), "coupons": build_coupons(rng)}


def write(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    data = build(SEED)
    out = os.path.join(HERE, "data")
    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, "experiment.csv"), EXPERIMENT_HEADER, data["experiment"])
    write(os.path.join(out, "coupons.csv"), COUPONS_HEADER, data["coupons"])
    print("wrote %d experiment rows and %d coupon rows (synthetic, seed %d)"
          % (len(data["experiment"]), len(data["coupons"]), SEED))


if __name__ == "__main__":
    main()
