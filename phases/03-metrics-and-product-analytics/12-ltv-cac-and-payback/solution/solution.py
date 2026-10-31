"""Lesson 12: unit economics, LTV, CAC and payback. Worked answer.

CAC          = marketing spend of a channel / new customers from that channel
ARPU         = revenue / paid customer-months (average revenue per paying month)
churn        = customers who did not renew after a paid month / paid months that could renew
               (a month equal to the as-of month cannot renew yet: it is left out)
margin LTV   = ARPU x gross margin / churn
curve[n]     = margin from the first n months / customers old enough to have had n months
payback      = the smallest n with curve[n] >= CAC
"""
import csv

MARGIN = 0.70        # gross margin from finance: after app store fees, hosting and support
AS_OF = "2026-10"    # the last month with payments


def next_month(month):
    y, m = int(month[:4]), int(month[5:])
    return "%04d-%02d" % (y + (m == 12), m % 12 + 1)


def months_between(first, last):
    """Whole months from first to last: ('2026-01', '2026-03') -> 2."""
    return (int(last[:4]) - int(first[:4])) * 12 + int(last[5:]) - int(first[5:])


def load(folder):
    """Return (customers, payments, spend):
    customers {customer_id: (signup_month, channel)},
    payments {customer_id: {month: amount}},
    spend {channel: total spend}."""
    customers, payments, spend = {}, {}, {}
    with open(folder + "/customers.csv", newline="") as f:
        for r in csv.DictReader(f):
            customers[r["customer_id"]] = (r["signup_month"], r["channel"])
    with open(folder + "/payments.csv", newline="") as f:
        for r in csv.DictReader(f):
            cell = payments.setdefault(r["customer_id"], {})
            cell[r["month"]] = cell.get(r["month"], 0.0) + float(r["amount"])
    with open(folder + "/spend.csv", newline="") as f:
        for r in csv.DictReader(f):
            spend[r["channel"]] = spend.get(r["channel"], 0.0) + float(r["spend"])
    return customers, payments, spend


def members(customers, channel):
    return [c for c, (_, ch) in customers.items() if ch == channel]


def cac(spend, customers, channel):
    """Spend / new customers for the channel, or None with no customers."""
    n = len(members(customers, channel))
    return spend.get(channel, 0.0) / n if n else None


def arpu_and_churn(customers, payments, channel, as_of=AS_OF):
    """(ARPU, monthly churn) for the channel. Either is None when its denominator is 0."""
    revenue = paid_months = at_risk = churned = 0
    for c in members(customers, channel):
        months = payments.get(c, {})
        for month, amount in months.items():
            revenue += amount
            paid_months += 1
            if month < as_of:
                at_risk += 1
                if next_month(month) not in months:
                    churned += 1
    arpu = revenue / paid_months if paid_months else None
    churn = churned / at_risk if at_risk else None
    return arpu, churn


def margin_ltv(arpu, churn, margin=MARGIN):
    """ARPU x margin / churn, or None when either input is missing or churn is 0."""
    if arpu is None or not churn:
        return None
    return arpu * margin / churn


def margin_curve(customers, payments, channel, margin=MARGIN, as_of=AS_OF):
    """{n: average margin per customer from their first n months}, n = 1, 2, ...,
    over customers old enough to have had n months by as_of. Customers who cancelled
    count with what they paid. Stops at the largest n anyone is old enough for."""
    group = [(c, customers[c][0]) for c in members(customers, channel)]
    curve = {}
    n = 1
    while True:
        eligible = [(c, s) for c, s in group if months_between(s, as_of) + 1 >= n]
        if not eligible:
            return curve
        total = 0.0
        for c, s in eligible:
            for month, amount in payments.get(c, {}).items():
                if months_between(s, month) < n:
                    total += amount * margin
        curve[n] = total / len(eligible)
        n += 1


def payback_months(curve, cac_value):
    """The smallest n with curve[n] >= cac_value, or None if the curve never gets there."""
    if cac_value is None:
        return None
    for n in sorted(curve):
        if curve[n] >= cac_value:
            return n
    return None


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
    customers, payments, spend = load(data)
    print("channel      customers    CAC   ARPU  churn  margin LTV  LTV/CAC  payback")
    for ch in ("paid_social", "search", "referral"):
        k = cac(spend, customers, ch)
        arpu, churn = arpu_and_churn(customers, payments, ch)
        ltv = margin_ltv(arpu, churn)
        pb = payback_months(margin_curve(customers, payments, ch), k)
        print("%-12s %9d  %5.2f  %5.2f  %5.3f  %10.2f  %7.2f  %s" % (
            ch, len(members(customers, ch)), k, arpu, churn, ltv, ltv / k, "never" if pb is None else "%d months" % pb))
    curve = margin_curve(customers, payments, "paid_social")
    print("paid_social margin per customer by month n: " + "  ".join("%d:%.1f" % (n, v) for n, v in curve.items()))
