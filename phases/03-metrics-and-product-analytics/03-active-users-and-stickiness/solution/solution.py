"""Lesson 03: active users and stickiness. Worked answer."""
import csv
import datetime


def active_by_day(path, actions=None):
    """Return {date_text: set of user_ids active that day}.
    actions is a set of event names that count as active; None means any event."""
    days = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if actions is not None and row["event_name"] not in actions:
                continue
            days.setdefault(row["event_date"], set()).add(int(row["user_id"]))
    return days


def window(end_date, days):
    """The list of date texts in the window of `days` days that ends on end_date (inclusive)."""
    end = datetime.date.fromisoformat(end_date)
    return [(end - datetime.timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def dau(by_day, date):
    """Distinct active users on one date."""
    return len(by_day.get(date, set()))


def active_in_window(by_day, end_date, days):
    """Distinct users active at least once in the `days` days ending on end_date.
    days=7 gives WAU, days=30 gives MAU."""
    users = set()
    for d in window(end_date, days):
        users |= by_day.get(d, set())
    return len(users)


def stickiness(by_day, end_date, days=30):
    """Average DAU over the window divided by the distinct active users in the window (DAU/MAU)."""
    mau = active_in_window(by_day, end_date, days)
    if mau == 0:
        return 0.0
    avg_dau = sum(dau(by_day, d) for d in window(end_date, days)) / days
    return avg_dau / mau


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "events.csv")
    end = "2026-09-30"
    for label, actions in (("any event", None), ("logged a workout", {"log_workout"})):
        by_day = active_by_day(data, actions)
        avg = sum(dau(by_day, d) for d in window(end, 30)) / 30
        print("%-17s DAU on %s: %3d  avg DAU: %5.1f  WAU: %3d  MAU: %3d  DAU/MAU: %.3f" % (
            label, end, dau(by_day, end), avg, active_in_window(by_day, end, 7),
            active_in_window(by_day, end, 30), stickiness(by_day, end)))
