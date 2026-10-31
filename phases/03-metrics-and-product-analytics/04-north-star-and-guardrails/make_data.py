"""Build data/experiment.csv: one row per job seeker in a synthetic two-week test
of a "quick apply" button on a fictional job marketplace.

Columns: user_id, variant (control or quick_apply), applications (sent in the test),
replies (employer replies received to those applications), unsubscribed (1 if the
user turned off all emails during the test).
The data is synthetic and deterministic (fixed seed). The true rates used to
generate it are in ARMS below: note the true unsubscribe chance is slightly
higher with quick apply (2.2% against 2.0%).

    python3 make_data.py          writes data/experiment.csv (seed 4004)
    import make_data; make_data.build(seed=9)   returns the rows for another seed
"""
import csv
import os
import random

SEED = 4004
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "experiment.csv")
FIELDS = ["user_id", "variant", "applications", "replies", "unsubscribed"]
# variant: (chance to apply at all, max applications per applier, reply chance per application, unsubscribe chance)
ARMS = {"control": (0.30, 4, 0.22, 0.020), "quick_apply": (0.38, 6, 0.14, 0.022)}


def build(seed=SEED, users=1800):
    """Return {"experiment": [row, ...]}, one dict of ints and text per job seeker."""
    rng = random.Random(seed)
    rows = []
    for user_id in range(1, users + 1):
        variant = "control" if rng.random() < 0.5 else "quick_apply"
        p_apply, max_apps, p_reply, p_unsub = ARMS[variant]
        applications = rng.randint(1, max_apps) if rng.random() < p_apply else 0
        replies = sum(1 for _ in range(applications) if rng.random() < p_reply)
        unsubscribed = 1 if rng.random() < p_unsub else 0
        rows.append({"user_id": user_id, "variant": variant, "applications": applications,
                     "replies": replies, "unsubscribed": unsubscribed})
    return {"experiment": rows}


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["experiment"]
    write_csv(rows, OUT)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
