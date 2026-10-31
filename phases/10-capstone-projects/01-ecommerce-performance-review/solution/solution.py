"""Capstone 10-01: Pottlemere quarterly business review. Worked solution.

Read solution/WRITEUP.md for the reasoning and the one-page write-up. Run this
file from the capstone folder to print the QBR numbers and redraw the chart:

    python3 solution/solution.py
"""
import csv
import math
import os

TAX = 0.12
PLATFORM_SWITCH = "2026-08-01"


def load(folder):
    """Read the three raw CSVs from `folder`: {"orders", "refunds", "customers"}, rows as dicts of text."""
    out = {}
    for name in ("orders", "refunds", "customers"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def quarter_of(date_text):
    """'2026-08-14' -> '2026-Q3'."""
    return "%s-Q%d" % (date_text[:4], (int(date_text[5:7]) - 1) // 3 + 1)


def latest_load(rows, key, as_of=None):
    """Keep one row per `key`: the one with the latest loaded_at, ignoring rows loaded after `as_of`."""
    best = {}
    for r in rows:
        if as_of is not None and r["loaded_at"] > as_of:
            continue
        k = r[key]
        if k not in best or r["loaded_at"] > best[k]["loaded_at"]:
            best[k] = r
    return best


def clean_orders(raw_orders, as_of=None):
    """One row per order as the warehouse knew it on `as_of` (a 'YYYY-MM-DD' load date, None = everything).
    The latest load of each order wins; cancelled orders are dropped; amount is converted to
    excluding tax (legacy rows include 12% tax). Returns dicts with order_id, customer_id,
    order_date and net_amount (a float, not rounded), sorted by order_id."""
    out = []
    for oid, r in sorted(latest_load(raw_orders, "order_id", as_of).items()):
        if r["status"] != "completed":
            continue
        amount = float(r["amount"])
        if r["platform"] == "legacy":
            amount = amount / (1 + TAX)
        out.append({"order_id": oid, "customer_id": r["customer_id"], "order_date": r["order_date"],
                    "net_amount": amount})
    return out


def clean_refunds(raw_refunds, as_of=None):
    """One row per refund_id (the latest load), as known on `as_of`. Returns dicts with refund_id,
    order_id, refund_date and refund_amount (float), sorted by refund_id."""
    return [{"refund_id": rid, "order_id": r["order_id"], "refund_date": r["refund_date"],
             "refund_amount": float(r["refund_amount"])}
            for rid, r in sorted(latest_load(raw_refunds, "refund_id", as_of).items())]


def quarter_summary(orders, refunds, quarter):
    """The QBR numbers for one quarter, from CLEAN orders and refunds.
    orders, customers (distinct buyers), new_customers (first order ever, among the orders
    given, is in this quarter), returning_customers, net_sales, refunds (by refund date),
    net_revenue = net_sales - refunds, aov = net_sales / orders (None when there are no orders)."""
    first = {}
    for o in orders:
        if o["customer_id"] not in first or o["order_date"] < first[o["customer_id"]]:
            first[o["customer_id"]] = o["order_date"]
    in_q = [o for o in orders if quarter_of(o["order_date"]) == quarter]
    buyers = {o["customer_id"] for o in in_q}
    new = {c for c in buyers if quarter_of(first[c]) == quarter}
    net_sales = sum(o["net_amount"] for o in in_q)
    refunded = sum(r["refund_amount"] for r in refunds if quarter_of(r["refund_date"]) == quarter)
    return {"quarter": quarter, "orders": len(in_q), "customers": len(buyers), "new_customers": len(new),
            "returning_customers": len(buyers) - len(new), "net_sales": net_sales, "refunds": refunded,
            "net_revenue": net_sales - refunded, "aov": net_sales / len(in_q) if in_q else None}


def restate(raw_orders, raw_refunds, quarter, reported_as_of):
    """Net revenue for `quarter` as reported on `reported_as_of` and as known now (all rows).
    Returns {"reported", "restated", "change"} with change = restated - reported."""
    rep = quarter_summary(clean_orders(raw_orders, reported_as_of), clean_refunds(raw_refunds, reported_as_of),
                          quarter)["net_revenue"]
    now = quarter_summary(clean_orders(raw_orders), clean_refunds(raw_refunds), quarter)["net_revenue"]
    return {"reported": rep, "restated": now, "change": now - rep}


def new_customers_by_channel(orders, customers, quarter):
    """{acquisition_channel: number of new customers in `quarter`}. Customers rows may repeat;
    a customer missing from the customers table counts under "unknown"."""
    channel = {}
    for c in customers:
        channel[c["customer_id"]] = c["acquisition_channel"]
    first = {}
    for o in orders:
        if o["customer_id"] not in first or o["order_date"] < first[o["customer_id"]]:
            first[o["customer_id"]] = o["order_date"]
    out = {}
    for cid, d in first.items():
        if quarter_of(d) == quarter:
            ch = channel.get(cid, "unknown")
            out[ch] = out.get(ch, 0) + 1
    return dict(sorted(out.items()))


def mean_diff_ci(a, b, z=1.96):
    """Difference in means, mean(b) - mean(a), with a Welch (unequal variance) normal interval.
    Returns {"diff", "se", "low", "high"}; None when either list has fewer than 2 values."""
    if len(a) < 2 or len(b) < 2:
        return None
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va = sum((x - ma) ** 2 for x in a) / (len(a) - 1)
    vb = sum((x - mb) ** 2 for x in b) / (len(b) - 1)
    se = math.sqrt(va / len(a) + vb / len(b))
    d = mb - ma
    return {"diff": d, "se": se, "low": d - z * se, "high": d + z * se}


def monthly_net_sales(orders):
    """{'YYYY-MM': net sales} for clean orders, months in order."""
    out = {}
    for o in orders:
        out[o["order_date"][:7]] = out.get(o["order_date"][:7], 0.0) + o["net_amount"]
    return dict(sorted(out.items()))


# ---- the deliverable: numbers and a chart ---------------------------------

def bar_chart_svg(series, title, width=560, height=260):
    """A plain SVG bar chart of {label: value}, with the y axis starting at 0."""
    labels = list(series)
    top = max(series.values()) * 1.1
    left, bottom, plot_h = 70, height - 40, height - 80
    bw = (width - left - 20) / len(labels)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif" font-size="11">'
             % (width, height), '<rect width="100%" height="100%" fill="white"/>',
             '<text x="%d" y="20" font-size="13">%s</text>' % (left, title)]
    for i in range(5):
        v = top * i / 4
        y = bottom - plot_h * i / 4
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#ddd"/>' % (left, width - 20, y, y))
        parts.append('<text x="%d" y="%.1f" text-anchor="end">%s</text>' % (left - 6, y + 4, "{:,.0f}".format(v)))
    for i, lab in enumerate(labels):
        h = plot_h * series[lab] / top
        x = left + i * bw + bw * 0.15
        parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#3b6ea5"/>'
                     % (x, bottom - h, bw * 0.7, h))
        parts.append('<text x="%.1f" y="%d" text-anchor="middle">%s</text>' % (x + bw * 0.35, bottom + 16, lab))
    parts.append('<line x1="%d" x2="%d" y1="%d" y2="%d" stroke="#333"/>' % (left, width - 20, bottom, bottom))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw = load(os.path.join(here, "data"))
    orders, refunds = clean_orders(raw["orders"]), clean_refunds(raw["refunds"])
    print("rows: %d order loads -> %d clean orders; %d refund loads -> %d refunds"
          % (len(raw["orders"]), len(orders), len(raw["refunds"]), len(refunds)))
    for q in ("2026-Q2", "2026-Q3"):
        s = quarter_summary(orders, refunds, q)
        print("%s orders %d customers %d new %d returning %d net_sales %.0f refunds %.0f net_revenue %.0f aov %.0f"
              % (q, s["orders"], s["customers"], s["new_customers"], s["returning_customers"], s["net_sales"],
                 s["refunds"], s["net_revenue"], s["aov"]))
    r = restate(raw["orders"], raw["refunds"], "2026-Q2", "2026-07-03")
    print("Q2 net revenue reported %.0f, restated %.0f, change %+.0f" % (r["reported"], r["restated"], r["change"]))
    for q in ("2026-Q2", "2026-Q3"):
        print(q, "new customers by channel", new_customers_by_channel(orders, raw["customers"], q))
    a = [o["net_amount"] for o in orders if quarter_of(o["order_date"]) == "2026-Q2"]
    b = [o["net_amount"] for o in orders if quarter_of(o["order_date"]) == "2026-Q3"]
    ci = mean_diff_ci(a, b)
    print("AOV Q3 - Q2: %+.0f (95%% CI %+.0f to %+.0f)" % (ci["diff"], ci["low"], ci["high"]))
    months = monthly_net_sales(orders)
    print("monthly net sales", {k: round(v) for k, v in months.items()})
    names = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "May", "06": "Jun", "07": "Jul",
             "08": "Aug", "09": "Sep"}
    svg = bar_chart_svg({names[k[5:]]: v for k, v in months.items()},
                        "Pottlemere net sales by month, Rs, excluding tax (synthetic data)")
    with open(os.path.join(here, "solution", "monthly_net_sales.svg"), "w") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
