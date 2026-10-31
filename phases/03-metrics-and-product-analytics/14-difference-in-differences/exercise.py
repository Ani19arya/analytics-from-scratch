"""Lesson 14: difference in differences. Your turn.

Goal: estimate what the lunch plan did to Pune's orders per zone-week, two ways
that must agree (four cell means, and a regression with an interaction term),
and check whether the control cities moved in parallel with Pune before launch.
Definitions are in "The idea" in the README. Standard library only.
Fill in every TODO, then run: python3 test_lesson.py
"""
import csv


def load(path):
    """[{"city", "zone", "week" (int), "orders" (float)}, ...]. Given."""
    with open(path, newline="") as f:
        return [{"city": r["city"], "zone": r["zone"], "week": int(r["week"]), "orders": float(r["orders"])}
                for r in csv.DictReader(f)]


def cell_means(rows, treated, controls, launch_week):
    """{(1, 1), (1, 0), (0, 1), (0, 0)} -> mean orders, keyed (is treated city, is from launch week).
    Rows from cities in neither group are ignored. An empty cell maps to None."""
    # TODO
    raise NotImplementedError


def did_from_means(means):
    """The difference in differences from the four cell means, or None if any cell is None."""
    # TODO
    raise NotImplementedError


def ols(X, y):
    """Least-squares coefficients b for y = X b (X is a list of rows). ValueError when there
    are no rows or the columns are not independent."""
    # TODO
    raise NotImplementedError


def did_regression(rows, treated, controls, launch_week):
    """{"intercept", "treated", "post", "did"} for orders = a + b T + c P + d T x P."""
    # TODO
    raise NotImplementedError


def slope(xs, ys):
    """Least-squares slope of ys on xs, or None when it cannot be computed."""
    # TODO
    raise NotImplementedError


def pre_gaps(rows, treated, controls, launch_week):
    """{week: treated mean - control mean} for each week before launch that has both sides."""
    # TODO
    raise NotImplementedError


def pre_trend_slope(rows, treated, controls, launch_week):
    """Slope per week of the pre-launch gaps, or None."""
    # TODO
    raise NotImplementedError
