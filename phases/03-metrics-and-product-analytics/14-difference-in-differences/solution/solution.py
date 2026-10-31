"""Lesson 14: difference in differences. Worked answer.

cell mean      = average orders per zone-week in one of four cells:
                 (treated city or control, before or from the launch week)
DiD            = (treated after - treated before) - (control after - control before)
regression     = orders = a + b x treated + c x post + d x treated x post, by least squares;
                 d is the DiD estimate
pre-trend      = gap (treated mean - control mean) in each week before launch;
                 its least-squares slope per week should be close to 0
"""
import csv


def load(path):
    """[{"city", "zone", "week" (int), "orders" (float)}, ...]."""
    with open(path, newline="") as f:
        return [{"city": r["city"], "zone": r["zone"], "week": int(r["week"]), "orders": float(r["orders"])}
                for r in csv.DictReader(f)]


def _cells(rows, treated, controls, launch_week):
    """Yield (is_treated, is_post, orders) for rows in the treated city or a control city."""
    controls = set(controls)
    for r in rows:
        if r["city"] == treated:
            t = 1
        elif r["city"] in controls:
            t = 0
        else:
            continue
        yield t, int(r["week"] >= launch_week), r["orders"]


def cell_means(rows, treated, controls, launch_week):
    """{(treated, post): mean orders per zone-week}; a cell with no rows is None."""
    sums, counts = {}, {}
    for t, p, y in _cells(rows, treated, controls, launch_week):
        sums[(t, p)] = sums.get((t, p), 0.0) + y
        counts[(t, p)] = counts.get((t, p), 0) + 1
    return {k: (sums[k] / counts[k] if counts.get(k) else None) for k in ((1, 1), (1, 0), (0, 1), (0, 0))}


def did_from_means(means):
    """(treated after - treated before) - (control after - control before), or None if a cell is empty."""
    if any(means.get(k) is None for k in ((1, 1), (1, 0), (0, 1), (0, 0))):
        return None
    return (means[(1, 1)] - means[(1, 0)]) - (means[(0, 1)] - means[(0, 0)])


def ols(X, y):
    """Least-squares coefficients for y = X b. Solves (X'X) b = X'y by Gaussian elimination.
    ValueError when the columns are not independent (X'X is singular) or there are no rows."""
    if not X:
        raise ValueError("no rows")
    k = len(X[0])
    a = [[sum(row[i] * row[j] for row in X) for j in range(k)] + [sum(row[i] * v for row, v in zip(X, y))]
         for i in range(k)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-9:
            raise ValueError("columns are not independent: one regressor is a mix of the others")
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(k):
            if r != col:
                f = a[r][col] / a[col][col]
                a[r] = [x - f * p for x, p in zip(a[r], a[col])]
    return [a[i][k] / a[i][i] for i in range(k)]


def did_regression(rows, treated, controls, launch_week):
    """{"intercept", "treated", "post", "did"} from orders = a + b T + c P + d T x P."""
    X, y = [], []
    for t, p, v in _cells(rows, treated, controls, launch_week):
        X.append([1.0, t, p, t * p])
        y.append(v)
    a, b, c, d = ols(X, y)
    return {"intercept": a, "treated": b, "post": c, "did": d}


def slope(xs, ys):
    """Least-squares slope of ys on xs, or None with fewer than two distinct xs."""
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None
    return sum((x - mx) * (v - my) for x, v in zip(xs, ys)) / sxx


def pre_gaps(rows, treated, controls, launch_week):
    """{week: treated mean - control mean} for every week before launch with both sides present."""
    sums = {}
    for r in rows:
        if r["week"] >= launch_week:
            continue
        side = 1 if r["city"] == treated else (0 if r["city"] in set(controls) else None)
        if side is None:
            continue
        s = sums.setdefault(r["week"], [0.0, 0, 0.0, 0])
        s[0 if side else 2] += r["orders"]
        s[1 if side else 3] += 1
    return {w: s[0] / s[1] - s[2] / s[3] for w, s in sorted(sums.items()) if s[1] and s[3]}


def pre_trend_slope(rows, treated, controls, launch_week):
    """Slope per week of the pre-launch gap; close to 0 when the trends were parallel."""
    gaps = pre_gaps(rows, treated, controls, launch_week)
    weeks = sorted(gaps)
    return slope(weeks, [gaps[w] for w in weeks])


if __name__ == "__main__":
    import os
    rows = load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "zone_weeks.csv"))
    for label, controls in (("all three controls", ["Nashik", "Indore", "Nagpur"]),
                            ("Nashik and Indore", ["Nashik", "Indore"])):
        means = cell_means(rows, "Pune", controls, 9)
        reg = did_regression(rows, "Pune", controls, 9)
        print("%-20s DiD by means %6.2f  by regression %6.2f  pre-trend slope %+.2f a week"
              % (label, did_from_means(means), reg["did"], pre_trend_slope(rows, "Pune", controls, 9)))
    for city in ("Nashik", "Indore", "Nagpur"):
        print("Pune vs %-7s pre-trend slope %+.2f a week" % (city, pre_trend_slope(rows, "Pune", [city], 9)))
