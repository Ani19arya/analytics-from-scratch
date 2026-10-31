"""Build three files for a synthetic two-sided marketplace: cafes, shops and
delivery firms post short-term jobs, and local workers search and apply.

posts.csv:        post_id, city, category, posted_at, closed_at
                  (closed_at is blank when the post was still open at the export)
applications.csv: application_id, post_id, worker_id, applied_at
searches.csv:     search_id, worker_id, city, category, searched_at

Times are local, 'YYYY-MM-DD HH:MM'. Posts run from 24 September to 31 October
2026, searches cover October only, and the export was taken at 2026-11-01 00:00.

The data is synthetic and deterministic (fixed seed). Pune has plenty of both
sides. Jaipur has many posts and few workers. Kochi has many workers and few
posts. A few application rows carry a clock error and are stamped a few minutes
before their post was created.

    python3 make_data.py          writes the three files (seed 13)
    import make_data; make_data.build(seed=8)   returns the rows for another seed
"""
import csv
import datetime
import math
import os
import random

SEED = 13
HERE = os.path.dirname(os.path.abspath(__file__))
FIELDS = {"posts": ["post_id", "city", "category", "posted_at", "closed_at"],
          "applications": ["application_id", "post_id", "worker_id", "applied_at"],
          "searches": ["search_id", "worker_id", "city", "category", "searched_at"]}
FMT = "%Y-%m-%d %H:%M"
FIRST_POST_DAY = datetime.date(2026, 9, 24)
FIRST_SEARCH_DAY = datetime.date(2026, 10, 1)
LAST_DAY = datetime.date(2026, 10, 31)
AS_OF = datetime.datetime(2026, 11, 1, 0, 0)
CATEGORIES = ("delivery", "kitchen", "retail")
EXPIRY_DAYS = 7
# city: (posts per day, mean applicants per post, mean hours to apply, searches per day, worker pool)
CITIES = {"Pune": (6, 3.0, 18.0, 16, 140),
          "Jaipur": (7, 1.1, 40.0, 7, 45),
          "Kochi": (2, 6.0, 7.0, 20, 160)}


def poisson(rng, lam):
    """Knuth's method; fine for small means."""
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def stamp(t):
    return t.strftime(FMT)


def random_time(rng, day):
    return datetime.datetime(day.year, day.month, day.day, rng.randint(6, 21), rng.randint(0, 59))


def build(seed=SEED):
    """Return {"posts": [...], "applications": [...], "searches": [...]}, rows of text values."""
    rng = random.Random(seed)
    posts, applications, searches = [], [], []
    for city in sorted(CITIES):
        per_day, mean_apps, mean_hours, searches_per_day, pool = CITIES[city]
        workers = ["%s-w%03d" % (city[:3].lower(), i) for i in range(1, pool + 1)]
        day = FIRST_POST_DAY
        while day <= LAST_DAY:
            for _ in range(max(0, per_day + rng.randint(-2, 2))):
                posted = random_time(rng, day)
                post_id = "p%04d" % (len(posts) + 1)
                delays = sorted(rng.expovariate(1.0 / mean_hours) for _ in range(poisson(rng, mean_apps)))
                if delays and rng.random() < 0.85:
                    closed = posted + datetime.timedelta(hours=delays[0] + rng.uniform(4, 36))
                else:
                    closed = posted + datetime.timedelta(days=EXPIRY_DAYS)
                for d in delays:
                    applied = posted + datetime.timedelta(hours=d)
                    if applied >= closed or applied >= AS_OF:
                        continue
                    applications.append([post_id, rng.choice(workers), applied])
                posts.append({"post_id": post_id, "city": city, "category": rng.choice(CATEGORIES),
                              "posted_at": stamp(posted), "closed_at": stamp(closed) if closed <= AS_OF else ""})
                if rng.random() < 0.01:   # a clock error: stamped before the post existed
                    applications.append([post_id, rng.choice(workers), posted - datetime.timedelta(minutes=rng.randint(2, 9))])
            if day >= FIRST_SEARCH_DAY:
                for _ in range(max(0, searches_per_day + rng.randint(-3, 3))):
                    searches.append({"worker_id": rng.choice(workers), "city": city,
                                     "category": rng.choice(CATEGORIES), "searched_at": stamp(random_time(rng, day))})
            day += datetime.timedelta(days=1)
    applications.sort(key=lambda a: (a[2], a[0]))
    apps = [{"application_id": "a%04d" % i, "post_id": p, "worker_id": w, "applied_at": stamp(t)}
            for i, (p, w, t) in enumerate(applications, 1)]
    searches.sort(key=lambda s: (s["searched_at"], s["city"]))
    for i, s in enumerate(searches, 1):
        s["search_id"] = "s%04d" % i
    return {"posts": posts, "applications": apps, "searches": searches}


def write_csv(rows, path, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def write_all(tables, folder):
    for name in ("posts", "applications", "searches"):
        write_csv(tables[name], os.path.join(folder, name + ".csv"), FIELDS[name])


def main():
    tables = build()
    write_all(tables, os.path.join(HERE, "data"))
    print("wrote", ", ".join("%d %s" % (len(tables[k]), k) for k in ("posts", "applications", "searches")))


if __name__ == "__main__":
    main()
