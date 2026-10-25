"""Lesson 04: draw a chart from scratch. Worked answer."""
from xml.sax.saxutils import escape

WIDTH, HEIGHT = 600, 400
LEFT, RIGHT, TOP, BOTTOM = 60, 20, 40, 60
PLOT_WIDTH = WIDTH - LEFT - RIGHT      # 520
PLOT_HEIGHT = HEIGHT - TOP - BOTTOM    # 300
BASELINE = TOP + PLOT_HEIGHT           # 340, the y of the zero line
N_TICKS = 5


def fmt(value):
    """12000 -> '12,000', 0.5 -> '0.5'."""
    if float(value).is_integer():
        return "{:,}".format(int(value))
    return ("%.4f" % value).rstrip("0").rstrip(".")


def nice_max(value):
    """Smallest number >= value of the form m * 10**k with m in 1, 2, 2.5, 5."""
    if value <= 0:
        return 1
    power = 1.0
    while power * 10 <= value:
        power *= 10
    while power > value:
        power /= 10
    for m in (1, 2, 2.5, 5, 10):
        if m * power >= value:
            result = m * power
            return int(result) if float(result).is_integer() else result
    return 10 * power


def axis_ticks(axis_max, n=N_TICKS):
    """n + 1 evenly spaced tick values from 0 to axis_max."""
    step = axis_max / n
    return [round(step * i, 10) for i in range(n + 1)]


def sort_rows(rows):
    """Largest value first, ties broken by label A to Z."""
    return sorted(rows, key=lambda r: (-r[1], r[0]))


def choose_chart(x_kind):
    """'time' -> 'line', 'category' -> 'bar'."""
    if x_kind == "time":
        return "line"
    if x_kind == "category":
        return "bar"
    raise ValueError("x_kind must be 'time' or 'category'")


def bar_chart_svg(rows, title):
    """rows is a list of (label, value). Returns an SVG string."""
    if not rows:
        raise ValueError("no rows to chart")
    if any(v < 0 for _, v in rows):
        raise ValueError("bar charts of negative values need a different design")
    rows = sort_rows(rows)
    axis_max = nice_max(max(v for _, v in rows))
    slot = PLOT_WIDTH / len(rows)
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">' % (WIDTH, HEIGHT, WIDTH, HEIGHT),
        '<text class="title" x="%d" y="24" font-size="16">%s</text>' % (LEFT, escape(title)),
    ]
    for t in axis_ticks(axis_max):
        y = BASELINE - t / axis_max * PLOT_HEIGHT
        out.append('<line class="gridline" x1="%d" x2="%d" y1="%.2f" y2="%.2f" stroke="#ddd"/>' % (LEFT, LEFT + PLOT_WIDTH, y, y))
        out.append('<text class="tick" x="%d" y="%.2f" text-anchor="end" font-size="11">%s</text>' % (LEFT - 6, y + 4, fmt(t)))
    for i, (label, value) in enumerate(rows):
        h = value / axis_max * PLOT_HEIGHT
        x = LEFT + i * slot + slot * 0.15
        cx = LEFT + i * slot + slot / 2
        out.append('<rect class="bar" data-label="%s" data-value="%s" x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#3b6ea5"/>'
                   % (escape(label, {'"': "&quot;"}), value, x, BASELINE - h, slot * 0.7, h))
        out.append('<text class="value-label" x="%.2f" y="%.2f" text-anchor="middle" font-size="11">%s</text>' % (cx, BASELINE - h - 5, fmt(value)))
        out.append('<text class="bar-label" x="%.2f" y="%d" text-anchor="middle" font-size="11">%s</text>' % (cx, BASELINE + 16, escape(label)))
    out.append('<line class="baseline" x1="%d" x2="%d" y1="%d" y2="%d" stroke="#333"/>' % (LEFT, LEFT + PLOT_WIDTH, BASELINE, BASELINE))
    out.append("</svg>")
    return "\n".join(out)
