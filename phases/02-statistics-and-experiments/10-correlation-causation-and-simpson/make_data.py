"""Build data/users.csv for lesson 10 (synthetic).

Kettlebrook Fitness, a fictional workout app. One row per active user over the
last 28 days:

user_id            a made-up id
tenure             "new" (under 3 months), "regular" (3 to 12 months) or
                   "veteran" (over a year) on the app
notifications_28d  push notifications the app sent the user in 28 days
workouts_28d       workouts the user logged in 28 days; blank when the user
                   turned workout tracking off, so the count is unknown

How the data is made (the learner cannot see this, the analyst in the lesson
cannot either): longer-tenured users opt in to more reminder types, so they get
more notifications, and they also work out more because they are the committed
ones. Within a tenure band, each extra notification LOWERS workouts a little
(notification fatigue). Pooled together, notifications and workouts still rise
together: Simpson's paradox.

Run: python3 make_data.py          (writes data/users.csv for the default seed)
Use: build(seed) returns {"users": rows} without writing anything.
"""
import csv
import os
import random

DEFAULT_SEED = 1010
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "users.csv")
FIELDS = ["user_id", "tenure", "notifications_28d", "workouts_28d"]
# tenure: (users, mean notifications, mean workouts)
BANDS = [("new", 220, 12, 5), ("regular", 200, 24, 11), ("veteran", 180, 38, 17)]
FATIGUE = -0.15      # workouts lost per extra notification, within a band
TRACKING_OFF = 0.02


def build(seed=DEFAULT_SEED):
    """Return {"users": rows}. The same seed always gives the same rows."""
    rng = random.Random(seed)
    people = []
    for tenure, count, notif_mean, workout_mean in BANDS:
        for _ in range(count):
            notifications = max(0, round(rng.gauss(notif_mean, 6)))
            workouts = workout_mean + FATIGUE * (notifications - notif_mean) + rng.gauss(0, 3)
            workouts = max(0, round(workouts))
            if rng.random() < TRACKING_OFF:
                workouts = ""
            people.append([tenure, notifications, workouts])
    rng.shuffle(people)
    rows = []
    for i, (tenure, notifications, workouts) in enumerate(people, 1):
        rows.append({"user_id": 5000 + i, "tenure": tenure,
                     "notifications_28d": notifications, "workouts_28d": workouts})
    return {"users": rows}


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def main():
    rows = build()["users"]
    write_csv(OUT, rows)
    print("wrote", len(rows), "rows to", OUT)


if __name__ == "__main__":
    main()
