"""Lesson 08 solution: histogram, scatter and line charts as SVG, from scratch."""
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
    """Edges start, start+width, ... until the last edge is above max(values).
    start defaults to the largest multiple of width at or below min(values)."""
    if width <= 0:
        raise ValueError("bin width must be positive")
    if not values:
        return []
    if start is None:
        start = math.floor(min(values) / width) * width
    n = int(math.floor((max(values) - start) / width)) + 1
    return [start + i * width for i in range(n + 1)]


def histogram(values, width, start=None):
    """(edges, counts). Bin i holds edges[i] <= v < edges[i+1]."""
    edges = bin_edges(values, width, start)
    counts = [0] * max(len(edges) - 1, 0)
    for v in values:
        i = int(math.floor((v - edges[0]) / width))
        if 0 <= i < len(counts):
            counts[i] += 1
        else:
            raise ValueError("value %s is outside the bins" % v)
    return edges, counts


def count_peaks(counts):
    """Runs of equal counts that are higher than the run on each side (0 beyond the ends)."""
    runs = []
    for c in counts:
        if not runs or runs[-1] != c:
            runs.append(c)
    padded = [0] + runs + [0]
    return sum(1 for i in range(1, len(padded) - 1) if padded[i] > padded[i - 1] and padded[i] > padded[i + 1])


def linear_scale(d0, d1, r0, r1):
    """A function mapping d0 -> r0 and d1 -> r1 in a straight line."""
    if d0 == d1:
        raise ValueError("the domain is a single value; widen it first")
    return lambda v: r0 + (v - d0) * (r1 - r0) / (d1 - d0)


def value_domain(values, kind):
    """The axis range. Bars and histograms show length, so they start at 0 and end at
    nice_max(max). Lines and scatters show position, so they may zoom: from min rounded
    down to max rounded up, to a multiple of tick_step(min, max)."""
    lo, hi = min(values), max(values)
    if kind in ("bar", "histogram"):
        return (0, nice_max(hi))
    if kind in ("line", "scatter"):
        step = tick_step(lo, hi)
        a, b = math.floor(lo / step) * step, math.ceil(hi / step) * step
        return (a, b) if b > a else (a - step, b + step)
    raise ValueError("kind must be bar, histogram, line or scatter")


def histogram_svg(edges, counts, title, x_label="minutes"):
    """One <rect class="bar"> per bin, touching, standing on BASELINE."""
    y_lo, y_hi = value_domain(counts, "histogram")
    x = linear_scale(edges[0], edges[-1], LEFT, LEFT + PLOT_WIDTH)
    y = linear_scale(y_lo, y_hi, BASELINE, TOP)
    body = []
    for i, c in enumerate(counts):
        x0, x1 = x(edges[i]), x(edges[i + 1])
        body.append('<rect class="bar" x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#4a7ab5" stroke="#ffffff"/>'
                    % (x0, y(c), x1 - x0, BASELINE - y(c)))
    for e in edges:
        body.append('<text class="xtick" x="%.2f" y="%d" text-anchor="middle">%s</text>' % (x(e), BASELINE + 16, fmt(e)))
    return frame(title, x_label, "deliveries", y_lo, y_hi, body)


def scatter_svg(xs, ys, title, x_label="distance (km)", y_label="minutes"):
    """One <circle class="point"> per (x, y) pair."""
    if len(xs) != len(ys):
        raise ValueError("xs and ys must be the same length")
    (x_lo, x_hi), (y_lo, y_hi) = value_domain(xs, "scatter"), value_domain(ys, "scatter")
    x = linear_scale(x_lo, x_hi, LEFT, LEFT + PLOT_WIDTH)
    y = linear_scale(y_lo, y_hi, BASELINE, TOP)
    body = ['<circle class="point" cx="%.2f" cy="%.2f" r="2.5" fill="#4a7ab5" fill-opacity="0.5"/>' % (x(a), y(b))
            for a, b in zip(xs, ys)]
    step = tick_step(x_lo, x_hi)
    for k in range(int(round((x_hi - x_lo) / step)) + 1):
        v = x_lo + k * step
        body.append('<text class="xtick" x="%.2f" y="%d" text-anchor="middle">%s</text>' % (x(v), BASELINE + 16, fmt(v)))
    return frame(title, x_label, y_label, y_lo, y_hi, body)


def line_svg(values, title, x_label="day", y_label="deliveries"):
    """One <polyline class="line">: point i at x for index i, y for values[i]."""
    y_lo, y_hi = value_domain(values, "line")
    y = linear_scale(y_lo, y_hi, BASELINE, TOP)
    if len(values) == 1:
        xs = [LEFT + PLOT_WIDTH / 2]
    else:
        x = linear_scale(0, len(values) - 1, LEFT, LEFT + PLOT_WIDTH)
        xs = [x(i) for i in range(len(values))]
    points = " ".join("%.2f,%.2f" % (a, y(v)) for a, v in zip(xs, values))
    body = ['<polyline class="line" points="%s" fill="none" stroke="#4a7ab5" stroke-width="2"/>' % points]
    return frame(title, x_label, y_label, y_lo, y_hi, body)


def daily_counts(rows):
    """Deliveries per day, oldest first, with 0 for a day in the range that has none."""
    if not rows:
        return []
    days = sorted({r["order_date"] for r in rows})
    first, last = days[0], days[-1]
    counts = {}
    for r in rows:
        counts[r["order_date"]] = counts.get(r["order_date"], 0) + 1
    return [counts.get(date.fromordinal(o), 0) for o in range(first.toordinal(), last.toordinal() + 1)]


if __name__ == "__main__":
    rows = load_deliveries()
    minutes = [r["minutes"] for r in rows]
    for w in (20, 10, 5):
        edges, counts = histogram(minutes, w)
        print("width %2d: %d bins, %d peak(s), counts %s" % (w, len(counts), count_peaks(counts), counts))
