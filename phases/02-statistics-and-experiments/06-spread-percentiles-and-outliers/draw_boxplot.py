"""Draw diagram.svg: a box plot of base_pay with the 1.5 x IQR fences, and every
point beyond the fences drawn and labelled by what it turned out to be.
Standard library only. Run: python3 draw_boxplot.py

The drawing code does its own arithmetic so that it does not depend on your exercise.
Quartiles use the inclusive method, rank = p / 100 * (n - 1).
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "salaries.csv")
OUT = os.path.join(HERE, "diagram.svg")

W, H = 760, 300
LEFT, RIGHT = 40, 30
AXIS_MAX = 250000
BOX_Y, BOX_H = 120, 50


def pct(sorted_values, p):
    rank = p / 100 * (len(sorted_values) - 1)
    lo, hi = math.floor(rank), math.ceil(rank)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (rank - lo)


def money(v):
    return format(int(round(v)), ",")


def main():
    with open(DATA, newline="") as f:
        rows = [(float(r["base_pay"]), r["title"]) for r in csv.DictReader(f)]
    pay = sorted(v for v, _ in rows)
    q1, med, q3 = pct(pay, 25), pct(pay, 50), pct(pay, 75)
    iqr = q3 - q1
    low_f, high_f = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inside = [v for v in pay if low_f <= v <= high_f]
    typos = sorted(v for v, _ in rows if v < 1000)
    high = sorted((v, t) for v, t in rows if v > high_f)
    leads = [v for v, t in high if t == "Lead Analyst"]
    others = [(v, t) for v, t in high if t != "Lead Analyst"]

    plot_w = W - LEFT - RIGHT

    def x(v):
        return LEFT + v / AXIS_MAX * plot_w

    mid = BOX_Y + BOX_H / 2
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'font-family="Helvetica, Arial, sans-serif" font-size="12">' % (W, H, W, H),
        '<title>Box plot of base pay with outliers labelled</title>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="%d" y="24" font-size="15" fill="#111111">Base pay of %d surveyed analysts (synthetic), '
        'box plot with 1.5 x IQR fences</text>' % (LEFT, len(pay)),
    ]
    for fence, label in ((low_f, "lower fence %s" % money(low_f)), (high_f, "upper fence %s" % money(high_f))):
        parts.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#999999" stroke-dasharray="4 3"/>'
                     % (x(fence), x(fence), BOX_Y - 40, BOX_Y + BOX_H + 30))
        parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#666666">%s</text>'
                     % (x(fence), BOX_Y - 46, label))
    parts.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="#333333"/>' % (x(inside[0]), x(q1), mid, mid))
    parts.append('<line x1="%.1f" x2="%.1f" y1="%.1f" y2="%.1f" stroke="#333333"/>' % (x(q3), x(inside[-1]), mid, mid))
    for v in (inside[0], inside[-1]):
        parts.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#333333"/>' % (x(v), x(v), BOX_Y + 12, BOX_Y + BOX_H - 12))
    parts.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="#c9d8ec" stroke="#333333"/>'
                 % (x(q1), BOX_Y, x(q3) - x(q1), BOX_H))
    parts.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#b8510d" stroke-width="3"/>'
                 % (x(med), x(med), BOX_Y, BOX_Y + BOX_H))
    parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#333333">Q1 %s, median %s, Q3 %s</text>'
                 % ((x(q1) + x(q3)) / 2, BOX_Y + BOX_H + 18, money(q1), money(med), money(q3)))
    parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#333333">whiskers %s to %s</text>'
                 % ((x(q1) + x(q3)) / 2, BOX_Y + BOX_H + 34, money(inside[0]), money(inside[-1])))
    for v in typos:
        parts.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#c0392b"/>' % (x(v), mid))
    parts.append('<text x="%.1f" y="%d" fill="#c0392b">%d typed in thousands: %s</text>'
                 % (x(0) + 2, BOX_Y + BOX_H + 66, len(typos), ", ".join(money(v) for v in typos)))
    parts.append('<text x="%.1f" y="%d" fill="#c0392b">(entry errors)</text>' % (x(0) + 2, BOX_Y + BOX_H + 82))
    for v in leads:
        parts.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#1f6f3f" opacity="0.8"/>' % (x(v), mid))
    parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#1f6f3f">%d lead analysts, %s to %s</text>'
                 % ((x(leads[0]) + x(leads[-1])) / 2, BOX_Y + BOX_H + 66, len(leads), money(leads[0]), money(leads[-1])))
    parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#1f6f3f">(real, keep)</text>'
                 % ((x(leads[0]) + x(leads[-1])) / 2, BOX_Y + BOX_H + 82))
    for v, t in others:
        parts.append('<circle cx="%.1f" cy="%.1f" r="4" fill="#1f6f3f" opacity="0.8"/>' % (x(v), mid))
        parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#1f6f3f">%s %s</text>'
                     % (x(v), BOX_Y - 12, t.lower(), money(v)))
    axis_y = H - 30
    parts.append('<line x1="%d" x2="%d" y1="%d" y2="%d" stroke="#111111"/>' % (LEFT, W - RIGHT, axis_y, axis_y))
    for tick in range(0, AXIS_MAX + 1, 50000):
        parts.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%d" stroke="#111111"/>' % (x(tick), x(tick), axis_y, axis_y + 5))
        parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#444444">%dk</text>' % (x(tick), axis_y + 18, tick // 1000))
    parts.append('</svg>')
    with open(OUT, "w", newline="\n") as f:
        f.write("\n".join(parts) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
