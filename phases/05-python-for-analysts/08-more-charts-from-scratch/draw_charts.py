"""Draw the four charts in this lesson's README.

python3 draw_charts.py                   uses your exercise.py and writes my_chart_*.svg
CHECK_SOLUTION=1 python3 draw_charts.py  uses solution/solution.py and writes chart_*.svg,
                                         the images in the README
"""
import importlib.util
import os
from datetime import timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
USE_SOLUTION = os.environ.get("CHECK_SOLUTION") == "1"
PY_FILE = os.path.join(HERE, "solution", "solution.py") if USE_SOLUTION else os.path.join(HERE, "exercise.py")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PREFIX = "chart_" if USE_SOLUTION else "my_chart_"

spec = importlib.util.spec_from_file_location("charts", PY_FILE)
charts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(charts)


def main():
    rows = charts.load_deliveries(os.path.join(HERE, "data", "deliveries.csv"))
    minutes = [r["minutes"] for r in rows]
    out = {}
    for w in (20, 5):
        edges, counts = charts.histogram(minutes, w)
        out["hist_%d" % w] = charts.histogram_svg(edges, counts, "Delivery time, %d-minute bins" % w)
    out["scatter"] = charts.scatter_svg([r["distance_km"] for r in rows], minutes, "Distance and delivery time")
    first = min(r["order_date"] for r in rows)
    counts = charts.daily_counts(rows)
    days = [first + timedelta(days=i) for i in range(len(counts))]
    labels = ["%d %s" % (d.day, MONTHS[d.month - 1]) if d.weekday() == 0 else "" for d in days]
    out["line"] = charts.line_svg(counts, "Deliveries per day, 28 Sep to 25 Oct 2026", labels,
                                  x_label="day (labels on Mondays)")
    for name, svg in out.items():
        path = os.path.join(HERE, PREFIX + name + ".svg")
        with open(path, "w", newline="\n") as f:
            f.write(svg + "\n")
        print("wrote", os.path.basename(path))


if __name__ == "__main__":
    main()
