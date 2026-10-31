"""Draw the CEO's KPI cards for this lesson as SVG.

python3 draw_dashboard.py                   uses your exercise.py and writes my_chart_dashboard.svg
CHECK_SOLUTION=1 python3 draw_dashboard.py  uses solution/solution.py and writes dashboard.svg
                                            and dashboard_nashik.svg, the images in the README
"""
import importlib.util
import os

HERE = os.path.dirname(os.path.abspath(__file__))
USE_SOLUTION = os.environ.get("CHECK_SOLUTION") == "1"
PY_FILE = os.path.join(HERE, "solution", "solution.py") if USE_SOLUTION else os.path.join(HERE, "exercise.py")

spec = importlib.util.spec_from_file_location("kpi", PY_FILE)
kpi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kpi)


def main():
    rows, targets = kpi.load_orders(), kpi.load_targets()
    as_of = max(r["order_date"] for r in rows)
    jobs = [("Tiffinbell, October so far", None, "dashboard.svg" if USE_SOLUTION else "my_chart_dashboard.svg")]
    if USE_SOLUTION:
        jobs.append(("Nashik kitchen, October so far", "Nashik", "dashboard_nashik.svg"))
    for title, city, name in jobs:
        cards = kpi.kpi_cards(rows, as_of, targets, city)
        subtitle = "%s compared with %s. Data to the end of %s." % (cards[0]["period"], cards[0]["prior_period"],
                                                                      as_of.strftime("%d %B %Y").lstrip("0"))
        with open(os.path.join(HERE, name), "w") as f:
            f.write(kpi.render_svg(cards, title, subtitle) + "\n")
        print("wrote", name)


if __name__ == "__main__":
    main()
