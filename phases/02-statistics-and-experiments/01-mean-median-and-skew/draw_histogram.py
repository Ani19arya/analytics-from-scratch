"""Draw diagram.svg: a histogram of pay_mid in 10,000 bins, with the mean, the
median and the middle half (P25 to P75) marked.
Standard library only. Run: python3 draw_histogram.py

The drawing code does its own counting so that it does not depend on your exercise.
"""
import csv
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "postings.csv")
OUT = os.path.join(HERE, "diagram.svg")
WIDTH_BIN = 10000

W, H = 760, 400
LEFT, RIGHT, TOP, BOTTOM = 60, 20, 50, 80


def main():
    with open(DATA, newline="") as f:
        pay = sorted(float(r["pay_mid"]) for r in csv.DictReader(f))
    n = len(pay)
    mean = sum(pay) / n
    median = (pay[n // 2 - 1] + pay[n // 2]) / 2 if n % 2 == 0 else pay[n // 2]
    counts = {}
    for v in pay:
        start = math.floor(v / WIDTH_BIN) * WIDTH_BIN
        counts[start] = counts.get(start, 0) + 1
    lo = math.floor(pay[0] / WIDTH_BIN) * WIDTH_BIN
    hi = math.floor(pay[-1] / WIDTH_BIN) * WIDTH_BIN + WIDTH_BIN

    def pct(q):
        rank = q / 100 * (n - 1)
        i = math.floor(rank)
        j = math.ceil(rank)
        return pay[i] + (pay[j] - pay[i]) * (rank - i)

    p25, p75 = pct(25), pct(75)
    tail = sum(1 for v in pay if v >= 200000)
    top_count = max(counts.values())
    y_max = math.ceil(top_count / 10) * 10

    plot_w = W - LEFT - RIGHT
    plot_h = H - TOP - BOTTOM

    def x(v):
        return LEFT + (v - lo) / (hi - lo) * plot_w

    def y(c):
        return TOP + plot_h - c / y_max * plot_h

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'font-family="Helvetica, Arial, sans-serif" font-size="12">' % (W, H, W, H),
        '<title>Histogram of posted pay with the mean and median marked</title>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="%d" y="24" font-size="15" fill="#111111">Posted pay (pay_mid) for %d synthetic postings, '
        '10,000 wide bins</text>' % (LEFT, n),
    ]
    for c in range(0, y_max + 1, 10):
        parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#e5e5e5"/>' % (LEFT, W - RIGHT, y(c), y(c)))
        parts.append('<text x="%d" y="%.1f" text-anchor="end" fill="#444444">%d</text>' % (LEFT - 6, y(c) + 4, c))
    parts.append('<rect x="%.1f" y="%d" width="%.1f" height="%.1f" fill="#f2e6b8" opacity="0.7"/>'
                 % (x(p25), TOP, x(p75) - x(p25), y(0) - TOP))
    parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="#6b5a1e">middle half: %sk to %sk</text>'
                 % ((x(p25) + x(p75)) / 2, y(0) + 34, format(int(p25 // 1000), ","), format(int(p75 // 1000), ",")))
    start = lo
    while start < hi:
        c = counts.get(start, 0)
        if c:
            parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#7a9cc6"/>'
                         % (x(start) + 1, y(c), x(start + WIDTH_BIN) - x(start) - 2, y(0) - y(c)))
        start += WIDTH_BIN
    parts.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#111111"/>' % (LEFT, W - RIGHT, y(0), y(0)))
    tick = 50000 * math.ceil(lo / 50000)
    while tick <= hi:
        parts.append('<text x="%.1f" y="%.1f" text-anchor="middle" fill="#444444">%dk</text>'
                     % (x(tick), y(0) + 18, tick // 1000))
        tick += 50000
    parts.append('<text x="%.1f" y="%d" text-anchor="middle" fill="#444444">posted pay, midpoint of the range</text>'
                 % (LEFT + plot_w / 2, H - 12))
    parts.append('<text x="16" y="%.1f" fill="#444444" transform="rotate(-90 16 %.1f)" text-anchor="middle">'
                 'postings</text>' % (TOP + plot_h / 2, TOP + plot_h / 2))
    for value, label, color, dy, anchor, dx in ((median, "median %s" % format(int(median), ","), "#b8510d", 0, "end", -4),
                                                (mean, "mean %s" % format(int(round(mean)), ","), "#1f6f3f", 16, "start", 4)):
        parts.append('<line x1="%.1f" x2="%.1f" y1="%d" y2="%.1f" stroke="%s" stroke-width="2" stroke-dasharray="6 3"/>'
                     % (x(value), x(value), TOP, y(0), color))
        parts.append('<text x="%.1f" y="%d" text-anchor="%s" fill="%s">%s</text>'
                     % (x(value) + dx, TOP + 10 + dy, anchor, color, label))
    parts.append('<text x="%.1f" y="%.1f" fill="#444444">%d postings at 200k or more: the long right tail</text>'
                 % (x(200000), y(10), tail))
    parts.append('</svg>')
    with open(OUT, "w", newline="\n") as f:
        f.write("\n".join(parts) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
