"""Build the synthetic app events for this lesson.

Run from the lesson folder: python3 make_data.py
Writes data/events.csv.
The data is synthetic and deterministic (fixed seed). One week of events,
Monday 12 to Sunday 18 October 2026, times to the second, in one time zone.

The story built into the data: Lanternway Courses learners open the app,
watch videos and answer quizzes. Inside a visit, events are seconds or minutes
apart; between visits there is a break of more than 30 minutes. Some visits
have a pause of exactly 30 minutes (1800 seconds) or exactly 30 minutes and
1 second, some visits run past midnight, some events share the same second,
and a few events arrived with no timestamp at all (a tracking glitch).

build(seed) returns the rows without writing anything. The test calls it with
a second seed to check your queries on data you have not seen.
"""
import csv
import datetime
import os
import random

SEED = 1010
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
WEEK_START = datetime.datetime(2026, 10, 12, 0, 0, 0)
WEEK_END = datetime.datetime(2026, 10, 19, 0, 0, 0)
NAMES = ["open_app", "play_video", "play_video", "play_video", "pause_video", "quiz_answer", "quiz_answer",
         "open_lesson", "bookmark"]


def in_visit_gap(rng):
    """Seconds between two events of one visit."""
    x = rng.random()
    if x < 0.03:
        return 1800                      # a pause of exactly 30 minutes: still the same visit
    if x < 0.05:
        return 0                         # two events logged in the same second
    if x < 0.12:
        return rng.randint(900, 1790)    # a long pause, under 30 minutes
    return rng.randint(5, 600)


def build(seed=SEED):
    """Return {"events": [...]}, rows as dicts."""
    rng = random.Random(seed)
    raw = []
    for u in range(1, 41):
        uid = "L%03d" % u
        visits_per_day = rng.choice([0.3, 0.5, 0.8, 1.2, 2.0])
        t = WEEK_START + datetime.timedelta(seconds=rng.randint(0, 2 * 86400))
        while True:
            # a break between visits: more than 30 minutes, usually hours
            x = rng.random()
            if x < 0.05:
                gap = 1801                       # exactly 30 minutes and 1 second: a new visit
            elif x < 0.25:
                gap = rng.randint(1900, 7200)    # back within two hours
            else:
                gap = int(rng.expovariate(visits_per_day / 86400.0)) + 1801
            t += datetime.timedelta(seconds=gap)
            if rng.random() < 0.06:
                # a late-night visit that runs past midnight
                t = t.replace(hour=23, minute=rng.randint(40, 55), second=rng.randint(0, 59))
            if t >= WEEK_END - datetime.timedelta(hours=1):
                break
            for i in range(rng.choice([1, 1, 2, 3, 4, 5, 6, 8, 12])):
                if i > 0:
                    t += datetime.timedelta(seconds=in_visit_gap(rng))
                raw.append((t, uid, "open_app" if i == 0 else rng.choice(NAMES[1:])))
    raw.sort()
    events = []
    for n, (t, uid, name) in enumerate(raw, 1):
        stamp = t.strftime("%Y-%m-%d %H:%M:%S")
        if rng.random() < 0.004:
            stamp = None                 # tracking glitch: the event has no time
        events.append({"event_id": n, "user_id": uid, "event_time": stamp, "event_name": name})
    return {"events": events}


def write(name, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote %d rows to data/%s" % (len(rows), name))


def main():
    os.makedirs(DATA, exist_ok=True)
    write("events.csv", build()["events"])


if __name__ == "__main__":
    main()
