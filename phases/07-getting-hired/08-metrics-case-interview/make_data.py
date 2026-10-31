"""Build data/funnel_daily.csv and data/accounts_daily.csv for the metrics case interview.

The story: Lanternway Courses, a fictional online course platform, saw sign-up events fall
about 20% from the week of 12 October 2026 to the week of 19 October 2026. The interviewer
hands the candidate two tables and asks "walk me through it".

funnel_daily.csv: date, platform, app_version, channel, visits, signup_starts, signups.
    One row per day, app version and traffic channel, from the product event tracker.
    platform is web, ios or android. app_version is "web" for the website, or the app
    release ("ios-4.8", "ios-4.9", "android-5.1", "android-5.2"). The new app releases
    (ios-4.9 and android-5.2) ship on 19 October, so they have no rows before that day.
    channel is organic, paid_search or referral. signups counts the "signup completed" event.
    Rows with no visits are left out.
accounts_daily.csv: date, app_version, accounts. Accounts created per day in the production
    database, by the app version they were created from. It does not depend on the tracker.

Each seed plants one cause behind the drop:
  traffic     one channel lost visits (for example a paused ad budget)
  conversion  one step of the web sign-up got worse (the start page or the form)
  tracking    the new release of one app stopped sending the "signup completed" event,
              so events fall while accounts do not
build(seed)["truth"] says which; the files do not.

The data is synthetic and deterministic (fixed seed). Lanternway Courses is invented.
Run from the lesson folder: python3 make_data.py
In code: build(seed) returns {"funnel": rows, "accounts": rows, "truth": dict} without writing files.
"""
import csv
import datetime
import os
import random

SEED = 9
HERE = os.path.dirname(os.path.abspath(__file__))
START = datetime.date(2026, 10, 12)
SPLIT = "2026-10-19"
DAYS = 14
FUNNEL_HEADER = ["date", "platform", "app_version", "channel", "visits", "signup_starts", "signups"]
ACCOUNTS_HEADER = ["date", "app_version", "accounts"]

CHANNELS = ("organic", "paid_search", "referral")
# Visits per day by platform and channel, before day-of-week and noise.
BASE_VISITS = {
    "web": {"organic": 900, "paid_search": 700, "referral": 250},
    "ios": {"organic": 300, "paid_search": 250, "referral": 120},
    "android": {"organic": 350, "paid_search": 300, "referral": 100},
}
START_RATE = {"web": 0.12, "ios": 0.16, "android": 0.15}
FINISH_RATE = {"web": 0.55, "ios": 0.62, "android": 0.60}
VERSIONS = {"web": ("web", None), "ios": ("ios-4.8", "ios-4.9"), "android": ("android-5.1", "android-5.2")}
# Share of an app's visits on the new release, day 0 to 6 of the second week.
ROLLOUT = (0.40, 0.55, 0.65, 0.72, 0.76, 0.78, 0.80)
EVENT_LOSS = 0.02  # a few completed sign-ups never reach the tracker (blockers, closed tabs)


def binomial(rng, n, p):
    return sum(1 for _ in range(n) if rng.random() < p)


def expected_signups():
    """Expected sign-ups per day by (platform, channel), used to size the planted cause."""
    return {(p, c): BASE_VISITS[p][c] * START_RATE[p] * FINISH_RATE[p] for p in BASE_VISITS for c in CHANNELS}


def plant(rng):
    """Pick this seed's cause and size it so sign-ups fall by about 15% to 24%."""
    exp = expected_signups()
    total = sum(exp.values())
    target = rng.uniform(0.15, 0.24)
    cause = rng.choice(["traffic", "conversion", "tracking"])
    if cause == "traffic":
        channel = rng.choice(["organic", "paid_search"])
        share = sum(v for (p, c), v in exp.items() if c == channel) / total
        return {"cause": cause, "dimension": "channel", "segment": channel, "step": "visits",
                "factor": 1 - target / share}
    if cause == "conversion":
        share = sum(v for (p, c), v in exp.items() if p == "web") / total
        step = rng.choice(["start_rate", "finish_rate"])
        return {"cause": cause, "dimension": "platform", "segment": "web", "step": step,
                "factor": 1 - target / share}
    version = rng.choice(["ios-4.9", "android-5.2"])
    return {"cause": cause, "dimension": "app_version", "segment": version, "step": None, "factor": 0.03}


def build(seed=SEED):
    rng = random.Random(seed)
    truth = plant(rng)
    funnel, accounts = [], {}
    for d in range(DAYS):
        day = START + datetime.timedelta(days=d)
        date = day.isoformat()
        second = date >= SPLIT
        weekday = 0.8 if day.weekday() >= 5 else 1.0
        for platform in ("web", "ios", "android"):
            old, new = VERSIONS[platform]
            for channel in CHANNELS:
                visits = int(round(BASE_VISITS[platform][channel] * weekday * rng.uniform(0.92, 1.08)))
                start_rate, finish_rate = START_RATE[platform], FINISH_RATE[platform]
                if second and truth["cause"] == "traffic" and channel == truth["segment"]:
                    visits = int(round(visits * truth["factor"]))
                if second and truth["cause"] == "conversion" and platform == truth["segment"]:
                    if truth["step"] == "start_rate":
                        start_rate *= truth["factor"]
                    else:
                        finish_rate *= truth["factor"]
                on_new = binomial(rng, visits, ROLLOUT[d - 7]) if (second and new) else 0
                for version, v in ((old, visits - on_new), (new, on_new)):
                    if not v:
                        continue
                    starts = binomial(rng, v, start_rate)
                    real = binomial(rng, starts, finish_rate)
                    keep = 1 - EVENT_LOSS
                    if truth["cause"] == "tracking" and version == truth["segment"]:
                        keep = truth["factor"]
                    events = binomial(rng, real, keep)
                    funnel.append([date, platform, version, channel, v, starts, events])
                    accounts[(date, version)] = accounts.get((date, version), 0) + real
    account_rows = [[date, version, n] for (date, version), n in sorted(accounts.items())]
    truth = {k: v for k, v in truth.items() if k != "factor"}
    return {"funnel": funnel, "accounts": account_rows, "truth": truth}


def write(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    data = build(SEED)
    out = os.path.join(HERE, "data")
    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, "funnel_daily.csv"), FUNNEL_HEADER, data["funnel"])
    write(os.path.join(out, "accounts_daily.csv"), ACCOUNTS_HEADER, data["accounts"])
    print("wrote %d funnel rows and %d account rows (synthetic, seed %d)" % (len(data["funnel"]), len(data["accounts"]), SEED))


if __name__ == "__main__":
    main()
