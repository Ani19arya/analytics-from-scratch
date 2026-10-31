"""Lesson 07: dashboard design and KPI cards. Worked answer.

Run from the lesson folder: python3 solution/solution.py"""
import calendar
import csv
import os
from datetime import date
from xml.sax.saxutils import escape

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MIN_N = 30          # below this many orders in the period, every card is flagged as small n
KPIS = [            # key, label, kind (amount or rate), higher is better?
    ("revenue", "Revenue", "amount", True),
    ("orders", "Orders", "amount", True),
    ("aov", "Average order value", "amount", True),
    ("refund_rate", "Refund rate", "rate", False),
]


def load_orders(data_dir=DATA):
    with open(os.path.join(data_dir, "orders.csv"), newline="") as f:
        return [{"order_id": r["order_id"], "order_date": date.fromisoformat(r["order_date"]), "city": r["city"],
                 "amount": float(r["amount"]), "refunded": r["refunded"] == "1"} for r in csv.DictReader(f)]


def load_targets(data_dir=DATA):
    """{"2026-10": {"revenue": 360000.0, "orders": 960.0, "refund_rate": 4.0}, ...}"""
    out = {}
    with open(os.path.join(data_dir, "targets.csv"), newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault(r["month"], {})[r["kpi"]] = float(r["target"])
    return out


def days_in_month(year, month):
    return calendar.monthrange(year, month)[1]


def period_bounds(as_of):
    """(current start, current end, prior start, prior end), all dates, ends included.

    Current: the 1st of as_of's month to as_of. Prior: the same days of the month before,
    capped at that month's length. If as_of is the last day of its month, the current month
    is complete and the prior period is the whole previous month."""
    start = as_of.replace(day=1)
    py, pm = (as_of.year - 1, 12) if as_of.month == 1 else (as_of.year, as_of.month - 1)
    prior_len = days_in_month(py, pm)
    if as_of.day == days_in_month(as_of.year, as_of.month):
        last = prior_len
    else:
        last = min(as_of.day, prior_len)
    return start, as_of, date(py, pm, 1), date(py, pm, last)


def kpis(rows, start, end, city=None):
    """The four KPIs for orders placed from start to end (both included).

    revenue      = sum of amount over orders that were not refunded
    orders       = count of all orders
    aov          = revenue / orders not refunded (None if there are none)
    refund_rate  = refunded orders / all orders * 100 (None if there are no orders)"""
    sel = [r for r in rows if start <= r["order_date"] <= end and (city is None or r["city"] == city)]
    paid = [r for r in sel if not r["refunded"]]
    revenue = round(sum(r["amount"] for r in paid), 2)
    return {"revenue": revenue, "orders": len(sel), "paid_orders": len(paid),
            "aov": round(revenue / len(paid), 2) if paid else None,
            "refund_rate": round(100.0 * (len(sel) - len(paid)) / len(sel), 2) if sel else None}


def change(kind, current, prior):
    """Amounts: percent change, None when either side is missing or prior is 0.
    Rates: the difference in percentage points, None when either side is missing."""
    if current is None or prior is None:
        return None
    if kind == "rate":
        return round(current - prior, 2)
    if prior == 0:
        return None
    return round((current - prior) / prior * 100, 1)


def paced_target(monthly_target, as_of):
    """Where an amount should be by as_of if the month's target accrues evenly by day."""
    return monthly_target * as_of.day / days_in_month(as_of.year, as_of.month)


def kpi_cards(rows, as_of, targets, city=None, min_n=MIN_N):
    """One card per KPI, in KPIS order. Each card is a dict:
      kpi, label, kind, value, prior, change, change_unit ('%' or 'pts'),
      target (paced for amounts, the limit for refund_rate, None for aov), vs_target
      (value as % of the paced target for amounts, points above (+) or below (-) the limit
      for refund_rate), status ('on track', 'behind' or None), n (orders in the current
      period), small_n (True when n < min_n), period, prior_period.
    Targets are company-wide, so a card for one city has no target."""
    cs, ce, ps, pe = period_bounds(as_of)
    cur, pri = kpis(rows, cs, ce, city), kpis(rows, ps, pe, city)
    month_targets = targets.get(as_of.strftime("%Y-%m"), {}) if city is None else {}
    cards = []
    for key, label, kind, higher_is_better in KPIS:
        value = cur[key]
        target = vs_target = status = None
        if key in month_targets and value is not None:
            if kind == "amount":
                target = round(paced_target(month_targets[key], as_of), 2)
                vs_target = round(value / target * 100, 1) if target else None
                on_track = value >= target
            else:
                target = month_targets[key]
                vs_target = round(value - target, 2)
                on_track = value <= target if not higher_is_better else value >= target
            status = "on track" if on_track else "behind"
        cards.append({"kpi": key, "label": label, "kind": kind, "value": value, "prior": pri[key],
                      "change": change("rate" if kind == "rate" else "amount", value, pri[key]),
                      "change_unit": "pts" if kind == "rate" else "%",
                      "target": target, "vs_target": vs_target, "status": status,
                      "n": cur["orders"], "small_n": cur["orders"] < min_n,
                      "period": span_label(cs, ce), "prior_period": span_label(ps, pe)})
    return cards


# ---- words and pictures

def span_label(start, end):
    """date(2026,10,1), date(2026,10,20) -> '1-20 Oct 2026'."""
    return "%d-%d %s %d" % (start.day, end.day, start.strftime("%b"), start.year)


def fmt_value(card):
    v = card["value"]
    if v is None:
        return "n/a"
    if card["kpi"] in ("revenue", "aov"):
        return "Rs {:,.0f}".format(v)
    if card["kpi"] == "orders":
        return "{:,}".format(v)
    return "%.1f%%" % v


def change_text(card):
    if card["change"] is None:
        return "no comparison for %s" % card["prior_period"]
    unit = " pts" if card["change_unit"] == "pts" else "%"
    return "%+.1f%s vs %s" % (card["change"], unit, card["prior_period"])


def target_text(card):
    if card["vs_target"] is None:
        return "no target"
    if card["kind"] == "rate":
        side = "over" if card["vs_target"] > 0 else "under"
        return "%.1f pts %s the %.1f%% limit" % (abs(card["vs_target"]), side, card["target"])
    return "%.0f%% of target pace" % card["vs_target"]


CARD_W, CARD_H, GAP, LEFT, TOP = 220, 150, 16, 16, 64
COLOURS = {"on track": "#1b7f4b", "behind": "#b3261e", None: "#5f6368"}


def render_svg(cards, title, subtitle=""):
    """A row of KPI cards as SVG. Every card has, with these classes:
    card (a rect with data-kpi), card-label, card-value, card-change, card-target,
    and card-small-n only when the card is flagged. Status is a word, not only a colour."""
    width = LEFT * 2 + len(cards) * CARD_W + (len(cards) - 1) * GAP
    height = TOP + CARD_H + 24
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="Helvetica, Arial, sans-serif">' % (width, height, width, height),
           '<rect width="%d" height="%d" fill="#ffffff"/>' % (width, height),
           '<text class="title" x="%d" y="28" font-size="18" font-weight="bold">%s</text>' % (LEFT, escape(title)),
           '<text class="subtitle" x="%d" y="48" font-size="12" fill="#5f6368">%s</text>' % (LEFT, escape(subtitle))]
    for i, card in enumerate(cards):
        x = LEFT + i * (CARD_W + GAP)
        colour = COLOURS[card["status"]]
        out.append('<rect class="card" data-kpi="%s" x="%d" y="%d" width="%d" height="%d" rx="8" fill="#f8f9fa" '
                   'stroke="#dadce0"/>' % (escape(card["kpi"]), x, TOP, CARD_W, CARD_H))
        out.append('<rect x="%d" y="%d" width="6" height="%d" fill="%s"/>' % (x, TOP, CARD_H, colour))
        out.append('<text class="card-label" x="%d" y="%d" font-size="13" fill="#3c4043">%s</text>'
                   % (x + 18, TOP + 26, escape(card["label"])))
        out.append('<text class="card-value" x="%d" y="%d" font-size="28" font-weight="bold">%s</text>'
                   % (x + 18, TOP + 64, escape(fmt_value(card))))
        out.append('<text class="card-change" x="%d" y="%d" font-size="12">%s</text>'
                   % (x + 18, TOP + 90, escape(change_text(card))))
        status = (" (%s)" % card["status"]) if card["status"] else ""
        out.append('<text class="card-target" x="%d" y="%d" font-size="12" fill="%s">%s</text>'
                   % (x + 18, TOP + 110, colour, escape(target_text(card) + status)))
        if card["small_n"]:
            out.append('<text class="card-small-n" x="%d" y="%d" font-size="11" fill="#b06000">%s</text>'
                       % (x + 18, TOP + 134, escape("only %d orders: read with care" % card["n"])))
    out.append("</svg>")
    return "\n".join(out)


def main():
    rows, targets = load_orders(), load_targets()
    as_of = max(r["order_date"] for r in rows)
    for city in (None, "Nashik"):
        print("All cities" if city is None else city)
        for card in kpi_cards(rows, as_of, targets, city):
            print("  %-20s %-12s %-28s %s%s" % (card["label"], fmt_value(card), change_text(card), target_text(card),
                                              "  [small n]" if card["small_n"] else ""))


if __name__ == "__main__":
    main()
