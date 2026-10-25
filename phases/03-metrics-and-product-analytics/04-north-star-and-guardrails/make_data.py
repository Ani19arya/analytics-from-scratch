"""Build data/experiment.csv: one row per job seeker in a synthetic two-week test
of a "quick apply" button on a fictional job marketplace.

Columns: user_id, variant (control or quick_apply), applications (sent in the test),
replies (employer replies received to those applications), unsubscribed (1 if the
user turned off all emails during the test).
The data is synthetic and deterministic (fixed seed).
Run from the lesson folder: python3 make_data.py
"""
import csv
import os
import random

random.seed(4004)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "experiment.csv")
# variant: (chance to apply at all, max applications per applier, reply chance per application, unsubscribe chance)
ARMS = {"control": (0.30, 4, 0.22, 0.020), "quick_apply": (0.38, 6, 0.14, 0.022)}


def main():
    rows = []
    for user_id in range(1, 1801):
        variant = "control" if random.random() < 0.5 else "quick_apply"
        p_apply, max_apps, p_reply, p_unsub = ARMS[variant]
        applications = random.randint(1, max_apps) if random.random() < p_apply else 0
        replies = sum(1 for _ in range(applications) if random.random() < p_reply)
        unsubscribed = 1 if random.random() < p_unsub else 0
        rows.append({"user_id": user_id, "variant": variant, "applications": applications,
                     "replies": replies, "unsubscribed": unsubscribed})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["user_id", "variant", "applications", "replies", "unsubscribed"])
        w.writeheader()
        w.writerows(rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
