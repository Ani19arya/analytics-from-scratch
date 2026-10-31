"""Draw the honest chart and the truncated-axis chart for this lesson.

python3 draw_charts.py                   uses your exercise.py and writes
                                         my_chart.svg and my_chart_truncated_axis.svg
CHECK_SOLUTION=1 python3 draw_charts.py  uses solution/solution.py and writes
                                         chart.svg and chart_truncated_axis.svg,
                                         the two images in the README

The truncated chart is the mistake the lesson warns about. It is drawn here,
on purpose, so you can see it next to the honest one.
"""
import csv
import importlib.util
import os
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
USE_SOLUTION = os.environ.get("CHECK_SOLUTION") == "1"
PY_FILE = os.path.join(HERE, "solution", "solution.py") if USE_SOLUTION else os.path.join(HERE, "exercise.py")
PREFIX = "chart" if USE_SOLUTION else "my_chart"

spec = importlib.util.spec_from_file_location("chart", PY_FILE)
chart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chart)


def read_rows():
    with open(os.path.join(HERE, "data", "product_line_revenue.csv"), newline="") as f:
        return [(r["product_line"], int(r["revenue"])) for r in csv.DictReader(f)]


def truncated_bar_chart_svg(rows, title, axis_min, axis_max, step):
    """The WRONG chart: the same bars on an axis that starts at axis_min.
    A bar below axis_min has nothing left to draw and disappears."""
    c = chart
    rows = c.sort_rows(rows)
    span = axis_max - axis_min
    slot = c.PLOT_WIDTH / len(rows)
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
        'font-family="Helvetica, Arial, sans-serif">' % (c.WIDTH, c.HEIGHT, c.WIDTH, c.HEIGHT),
        '<rect width="%d" height="%d" fill="#ffffff"/>' % (c.WIDTH, c.HEIGHT),
        '<text class="title" x="%d" y="24" font-size="16">%s</text>' % (c.LEFT, escape(title)),
    ]
    tick = axis_min
    while tick <= axis_max:
        y = c.BASELINE - (tick - axis_min) / span * c.PLOT_HEIGHT
        out.append('<line class="gridline" x1="%d" x2="%d" y1="%.2f" y2="%.2f" stroke="#ddd"/>' % (c.LEFT, c.LEFT + c.PLOT_WIDTH, y, y))
        out.append('<text class="tick" x="%d" y="%.2f" text-anchor="end" font-size="11">%s</text>' % (c.LEFT - 6, y + 4, c.fmt(tick)))
        tick += step
    for i, (label, value) in enumerate(rows):
        h = max(0.0, (value - axis_min) / span * c.PLOT_HEIGHT)
        cx = c.LEFT + i * slot + slot / 2
        out.append('<rect class="bar" x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#b5523b"/>'
                   % (c.LEFT + i * slot + slot * 0.15, c.BASELINE - h, slot * 0.7, h))
        out.append('<text class="value-label" x="%.2f" y="%.2f" text-anchor="middle" font-size="11">%s</text>' % (cx, c.BASELINE - h - 5, c.fmt(value)))
        out.append('<text class="bar-label" x="%.2f" y="%d" text-anchor="middle" font-size="11">%s</text>' % (cx, c.BASELINE + 16, escape(label)))
    out.append('<line class="baseline" x1="%d" x2="%d" y1="%d" y2="%d" stroke="#333"/>' % (c.LEFT, c.LEFT + c.PLOT_WIDTH, c.BASELINE, c.BASELINE))
    out.append("</svg>")
    return "\n".join(out)


def main():
    rows = read_rows()
    honest = chart.bar_chart_svg(rows, "Revenue by product line")
    wrong = truncated_bar_chart_svg(rows, "Same data, axis starting at 28,000", 28000, 40000, 2000)
    for name, svg in ((PREFIX + ".svg", honest), (PREFIX + "_truncated_axis.svg", wrong)):
        with open(os.path.join(HERE, name), "w") as f:
            f.write(svg + "\n")
        print("wrote", name)


if __name__ == "__main__":
    main()
