"""Exercise: read the orders, compute 4 KPIs with week-over-week change, write a Markdown report.

load_orders, fmt_money, fmt_rate, write_report and main are done for you.
Fill in the functions marked TODO. Then run: python3 test_lesson.py


Run the report: python3 exercise.py [--week YYYY-MM-DD] [--out DIR]
"""
import argparse
import csv
import os
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")


def load_orders(path=os.path.join(DATA, "orders.csv")):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["order_date"] = date.fromisoformat(r["order_date"])
        r["amount"] = float(r["amount"])
    return rows


def fmt_money(x):
    return "n/a" if x is None else "$" + format(x, ",.2f")


def fmt_rate(x):
    return "n/a" if x is None else "%.1f%%" % x


def latest_complete_week(rows):
    """The Monday of the last Monday-to-Sunday week fully covered by the data."""
    # TODO: find the last Sunday on or before the last date, then go back 6 days.
    raise NotImplementedError

def rows_in_week(rows, monday):
    """Rows dated from monday up to and including the Sunday after it."""
    # TODO
    raise NotImplementedError

def compute_kpis(rows):
    """revenue and orders count paid orders; aov = revenue / paid orders;
    refund_rate = refunded / all orders * 100. Undefined values are None."""
    # TODO: return a dict with keys revenue, orders, aov, refund_rate.
    raise NotImplementedError

def pct_change(cur, prev):
    """Percent change, or None when it is undefined."""
    # TODO
    raise NotImplementedError

def format_change(kpi, cur, prev):
    """'+12.2%' for amounts and counts. A rate changes in points: '-0.8 pts'."""
    # TODO
    raise NotImplementedError

def build_report(monday, cur, prev):
    # TODO: build the Markdown shown in the README, line for line.
    raise NotImplementedError

def write_report(text, out_dir, monday):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "report-%s.md" % monday.isoformat())
    with open(path, "w") as f:
        f.write(text)
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Write the weekly KPI report.")
    parser.add_argument("--week", help="Monday of the week, YYYY-MM-DD. Default: last complete week.")
    parser.add_argument("--out", default=os.path.join(HERE, "reports"), help="Folder for the report.")
    parser.add_argument("--data", default=os.path.join(DATA, "orders.csv"))
    args = parser.parse_args(argv)

    rows = load_orders(args.data)
    monday = date.fromisoformat(args.week) if args.week else latest_complete_week(rows)
    if monday.weekday() != 0:
        raise SystemExit("--week must be a Monday, got %s" % monday)
    cur = compute_kpis(rows_in_week(rows, monday))
    prev = compute_kpis(rows_in_week(rows, monday - timedelta(days=7)))
    path = write_report(build_report(monday, cur, prev), args.out, monday)
    print("wrote", path)
    return path


if __name__ == "__main__":
    main()
