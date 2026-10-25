"""Solution: read the orders, compute 4 KPIs with week-over-week change, write a Markdown report.

Run: python3 solution/solution.py [--week YYYY-MM-DD] [--out DIR]
"""
import argparse
import csv
import os
from datetime import date, timedelta

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    last = max(r["order_date"] for r in rows)
    sunday = last - timedelta(days=(last.weekday() + 1) % 7)
    return sunday - timedelta(days=6)


def rows_in_week(rows, monday):
    """Rows dated from monday up to and including the Sunday after it."""
    end = monday + timedelta(days=7)
    return [r for r in rows if monday <= r["order_date"] < end]


def compute_kpis(rows):
    """revenue and orders count paid orders; aov = revenue / paid orders;
    refund_rate = refunded / all orders * 100. Undefined values are None."""
    paid = [r for r in rows if r["status"] == "paid"]
    refunded = sum(1 for r in rows if r["status"] == "refunded")
    revenue = round(sum(r["amount"] for r in paid), 2)
    return {
        "revenue": revenue,
        "orders": len(paid),
        "aov": revenue / len(paid) if paid else None,
        "refund_rate": refunded / len(rows) * 100 if rows else None,
    }


def pct_change(cur, prev):
    """Percent change, or None when it is undefined."""
    if cur is None or not prev:
        return None
    return (cur - prev) / prev * 100


def format_change(kpi, cur, prev):
    """'+12.2%' for amounts and counts. A rate changes in points: '-0.8 pts'."""
    if kpi == "refund_rate":
        if cur is None or prev is None:
            return "n/a"
        return "%+.1f pts" % (cur - prev)
    change = pct_change(cur, prev)
    return "n/a" if change is None else "%+.1f%%" % change


def build_report(monday, cur, prev):
    sunday = monday + timedelta(days=6)
    lines = [
        "# Weekly report: week of %s" % monday.isoformat(),
        "",
        "Orders from Monday %s to Sunday %s, compared with the week before." % (monday.isoformat(), sunday.isoformat()),
        "",
        "| KPI | This week | Last week | Change |",
        "|---|---|---|---|",
        "| Revenue | %s | %s | %s |" % (fmt_money(cur["revenue"]), fmt_money(prev["revenue"]), format_change("revenue", cur["revenue"], prev["revenue"])),
        "| Paid orders | %d | %d | %s |" % (cur["orders"], prev["orders"], format_change("orders", cur["orders"], prev["orders"])),
        "| Average order value | %s | %s | %s |" % (fmt_money(cur["aov"]), fmt_money(prev["aov"]), format_change("aov", cur["aov"], prev["aov"])),
        "| Refund rate | %s | %s | %s |" % (fmt_rate(cur["refund_rate"]), fmt_rate(prev["refund_rate"]), format_change("refund_rate", cur["refund_rate"], prev["refund_rate"])),
        "",
        "Revenue and average order value count paid orders only. Refund rate is refunded orders as a share of all orders placed in the week.",
        "",
    ]
    return "\n".join(lines)


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
