"""Lesson 13: marketplace metrics and liquidity. Worked answer.

post liquidity  = posts with an application within 48 hours of posting (0 <= wait <= 48:00)
                  / posts old enough to have had the full 48 hours by the export time
search success  = worker searches that found at least one open post in the same city and
                  category (posted_at <= search time < closed_at, blank closed_at = still open)
                  / all searches
diagnosis       = which side is short, from the two rates against one target
"""
import csv
import datetime
import os

FMT = "%Y-%m-%d %H:%M"
AS_OF = datetime.datetime(2026, 11, 1, 0, 0)
ALL = "all"


def parse_time(text):
    """'2026-10-01 14:05' -> datetime; '' -> None."""
    return datetime.datetime.strptime(text, FMT) if text else None


def load(folder):
    """(posts, applications, searches) as lists of dicts with times parsed."""
    def read(name):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            return list(csv.DictReader(f))
    posts = read("posts")
    for p in posts:
        p["posted_at"], p["closed_at"] = parse_time(p["posted_at"]), parse_time(p["closed_at"])
    apps = read("applications")
    for a in apps:
        a["applied_at"] = parse_time(a["applied_at"])
    searches = read("searches")
    for s in searches:
        s["searched_at"] = parse_time(s["searched_at"])
    return posts, apps, searches


def rate(pair):
    """(hits, total) -> hits / total, or None when total is 0."""
    return pair[0] / pair[1] if pair and pair[1] else None


def post_liquidity(posts, applications, as_of=AS_OF, window_hours=48):
    """{city: (filled, eligible)} plus ALL. A post is eligible when posted_at + window <= as_of;
    filled when some application has 0 <= applied_at - posted_at <= window."""
    window = datetime.timedelta(hours=window_hours)
    first = {}
    by_id = {p["post_id"]: p for p in posts}
    for a in applications:
        p = by_id.get(a["post_id"])
        if p is None or a["applied_at"] < p["posted_at"]:
            continue
        wait = a["applied_at"] - p["posted_at"]
        if p["post_id"] not in first or wait < first[p["post_id"]]:
            first[p["post_id"]] = wait
    out = {}
    for p in posts:
        if p["posted_at"] + window > as_of:
            continue
        hit = int(p["post_id"] in first and first[p["post_id"]] <= window)
        for key in (p["city"], ALL):
            f, e = out.get(key, (0, 0))
            out[key] = (f + hit, e + 1)
    return out


def search_success(searches, posts):
    """{city: (searches that found an open post, searches)} plus ALL."""
    open_posts = {}
    for p in posts:
        open_posts.setdefault((p["city"], p["category"]), []).append((p["posted_at"], p["closed_at"]))
    out = {}
    for s in searches:
        t = s["searched_at"]
        hit = int(any(start <= t and (end is None or t < end)
                      for start, end in open_posts.get((s["city"], s["category"]), [])))
        for key in (s["city"], ALL):
            f, n = out.get(key, (0, 0))
            out[key] = (f + hit, n + 1)
    return out


def diagnose(liquidity, success, target=0.8):
    """{city: "workers" | "employers" | "both" | "neither" | None} for every key in either input.
    "workers" means posts wait for workers (posts below target, searches fine);
    "employers" means workers wait for posts. None when either rate is missing."""
    out = {}
    for key in sorted(set(liquidity) | set(success)):
        p, s = rate(liquidity.get(key)), rate(success.get(key))
        if p is None or s is None:
            out[key] = None
        elif p < target and s < target:
            out[key] = "both"
        elif p < target:
            out[key] = "workers"
        elif s < target:
            out[key] = "employers"
        else:
            out[key] = "neither"
    return out


if __name__ == "__main__":
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    posts, apps, searches = load(os.path.join(here, "data"))
    liq, suc = post_liquidity(posts, apps), search_success(searches, posts)
    verdict = diagnose(liq, suc)
    print("%-7s %18s %20s  short of" % ("city", "posts filled 48h", "searches found post"))
    for key in sorted(liq, key=lambda k: (k == ALL, k)):
        print("%-7s %4d/%3d = %5.1f%%  %4d/%3d = %5.1f%%  %s" % (key, liq[key][0], liq[key][1], 100 * rate(liq[key]),
                                                             suc[key][0], suc[key][1], 100 * rate(suc[key]), verdict[key]))
