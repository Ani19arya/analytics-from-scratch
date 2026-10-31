"""Lesson 08: more charts from scratch. Your turn.

load_deliveries, nice_max, tick_step, fmt and frame are done for you. Write every function
below "the lesson" that raises NotImplementedError. Run from this folder: python3 test_lesson.py
Then python3 draw_charts.py draws your four charts as my_chart_*.svg."""
import csv
import math
import os
from datetime import date
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

WIDTH, HEIGHT = 600, 400
LEFT, RIGHT, TOP, BOTTOM = 60, 20, 40, 60
PLOT_WIDTH = WIDTH - LEFT - RIGHT      # 520
PLOT_HEIGHT = HEIGHT - TOP - BOTTOM    # 300
BASELINE = TOP + PLOT_HEIGHT           # 340, the y of the bottom of the plot


# ---- done for you ---------------------------------------------------------------

def load_deliveries(path=os.path.join(DATA, "deliveries.csv")):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["order_date"] = date.fromisoformat(r["order_date"])
        r["distance_km"] = float(r["distance_km"])
        r["minutes"] = float(r["minutes"])
    return rows


def nice_max(value):
    """The smallest 1, 2, 2.5 or 5 times a power of ten that is >= value (lesson 04-04)."""
    if value <= 0:
        return 1
    power = 1.0
    while power * 10 <= value:
        power *= 10
    while power > value:
        power /= 10
    for m in (1, 2, 2.5, 5, 10):
        if m * power >= value:
            return m * power


def tick_step(lo, hi):
    """A round gap between gridlines: about 8 of them across lo..hi."""
    return nice_max((hi - lo) / 8) if hi > lo else nice_max(abs(hi)) or 1


def fmt(x):
    return ("%.2f" % x).rstrip("0").rstrip(".")


def frame(title, x_label, y_label, y_lo, y_hi, body):
    """Wrap chart marks in an SVG with a white background, axes, labels and y gridlines."""
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="sans-serif" font-size="12">' % (WIDTH, HEIGHT, WIDTH, HEIGHT),
           '<rect class="bg" x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (WIDTH, HEIGHT),
           '<text x="%d" y="24" font-size="15" font-weight="bold">%s</text>' % (LEFT, escape(title))]
    step = tick_step(y_lo, y_hi)
    for k in range(int(round((y_hi - y_lo) / step)) + 1):
        v = y_lo + k * step
        y = BASELINE - PLOT_HEIGHT * (v - y_lo) / (y_hi - y_lo)
        out.append('<line x1="%d" x2="%d" y1="%.2f" y2="%.2f" stroke="#e5e5e5"/>' % (LEFT, LEFT + PLOT_WIDTH, y, y))
        out.append('<text class="ytick" x="%d" y="%.2f" text-anchor="end">%s</text>' % (LEFT - 6, y + 4, fmt(v)))
    out.extend(body)
    out.append('<line class="axis" x1="%d" x2="%d" y1="%d" y2="%d" stroke="#333333"/>' % (LEFT, LEFT + PLOT_WIDTH, BASELINE, BASELINE))
    out.append('<line class="axis" x1="%d" x2="%d" y1="%d" y2="%d" stroke="#333333"/>' % (LEFT, LEFT, TOP, BASELINE))
    out.append('<text x="%d" y="%d" text-anchor="middle">%s</text>' % (LEFT + PLOT_WIDTH // 2, HEIGHT - 12, escape(x_label)))
    out.append('<text x="14" y="%d" transform="rotate(-90 14 %d)" text-anchor="middle">%s</text>'
               % (TOP + PLOT_HEIGHT // 2, TOP + PLOT_HEIGHT // 2, escape(y_label)))
    out.append("</svg>")
    return "\n".join(out)


# ---- the lesson -----------------------------------------------------------------

def bin_edges(values, width, start=None):
    """Edges start, start+width, ... until the last edge is ABOVE max(values), so the
    largest value sits inside a bin. start defaults to the largest multiple of width at or
    below min(values). [] for no values; ValueError for a width of 0 or less."""
    # TODO
    raise NotImplementedError


def histogram(values, width, start=None):
    """(edges, counts). Bin i holds edges[i] <= v < edges[i+1], so a value on an edge goes
    in the bin to its right. A value below start is an error, not a silent drop."""
    # TODO
    raise NotImplementedError


def count_peaks(counts):
    """How many humps: runs of equal counts higher than the run on each side (0 beyond the
    ends). [1, 3, 3, 1] has one peak, [5, 1, 5] has two, [] and [0, 0] have none."""
    # TODO
    raise NotImplementedError


def linear_scale(d0, d1, r0, r1):
    """A function that maps d0 to r0 and d1 to r1 in a straight line (r0 may be bigger than
    r1, as on an SVG y axis). ValueError if d0 == d1."""
    # TODO
    raise NotImplementedError


def value_domain(values, kind):
    """(lo, hi) for an axis. "bar" and "histogram" show length: (0, nice_max(max)).
    "line" and "scatter" show position and may zoom: min rounded down and max rounded up to
    a multiple of step = tick_step(min, max); if that gives lo == hi, use (lo - step, hi + step).
    Any other kind is a ValueError."""
    # TODO
    raise NotImplementedError


def histogram_svg(edges, counts, title, x_label="minutes"):
    """frame(...) around one <rect class="bar"> per bin: bars touch, stand on BASELINE, and
    have height count / y_hi * PLOT_HEIGHT on the value_domain(counts, "histogram") axis.
    Add a <text class="xtick"> under every edge."""
    # TODO
    raise NotImplementedError


def scatter_svg(xs, ys, title, x_label="distance (km)", y_label="minutes"):
    """frame(...) around one <circle class="point"> per (x, y) pair, both axes from
    value_domain(..., "scatter"). ValueError if xs and ys differ in length."""
    # TODO
    raise NotImplementedError


def line_svg(values, title, x_labels=None, x_label="day", y_label="deliveries"):
    """frame(...) around one <polyline class="line">: point i at the i-th of len(values)
    evenly spaced x positions from LEFT to LEFT + PLOT_WIDTH (one value: the middle), y on
    the value_domain(values, "line") axis. x_labels, if given, has one string per value and
    each non-empty one becomes a <text class="xtick"> at its point's x. ValueError for no
    values or a wrong number of labels."""
    # TODO
    raise NotImplementedError


def daily_counts(rows):
    """Rows per order_date, oldest first, from the first day to the last, with 0 for a day
    in between that has no rows. [] for no rows."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    rows = load_deliveries()
    minutes = [r["minutes"] for r in rows]
    for w in (20, 10, 5):
        edges, counts = histogram(minutes, w)
        print("width %2d: %d bins, %d peak(s), counts %s" % (w, len(counts), count_peaks(counts), counts))
