"""Lesson 04: draw a chart from scratch. Your turn.

Fill in every function that raises NotImplementedError.
Run from this folder: python3 test_lesson.py"""
from xml.sax.saxutils import escape, quoteattr

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
    """Smallest number >= value of the form m * 10**k with m in 1, 2, 2.5, 5.
    nice_max(42) == 50, nice_max(1234) == 2000, nice_max(200) == 200,
    nice_max(0.3) == 0.5. Return 1 when value <= 0."""
    # TODO
    raise NotImplementedError


def axis_ticks(axis_max, n=N_TICKS):
    """n + 1 evenly spaced tick values from 0 to axis_max.
    axis_ticks(50000) == [0, 10000, 20000, 30000, 40000, 50000]."""
    # TODO
    raise NotImplementedError


def sort_rows(rows):
    """rows is a list of (label, value). Largest value first, ties broken by label A to Z."""
    # TODO
    raise NotImplementedError


TASKS = ("compare", "rank", "trend", "distribution", "part_to_whole", "relationship")


def choose_chart(task, n_items=None):
    """A first-pass chart choice from the question being asked.
    task is one of TASKS (exact lowercase strings):
      'compare'       categories side by side            -> 'bar'
      'rank'          which is biggest                    -> 'bar'
      'distribution'  how values spread out               -> 'histogram'
      'relationship'  does one number move with another   -> 'scatter'
      'trend'         change over time, n_items periods:  fewer than 5 -> 'bar', else 'line'
      'part_to_whole' shares of a total, n_items parts:   fewer than 5 -> 'stacked bar', else 'bar'
    Raise ValueError for any other task, and when 'trend' or 'part_to_whole'
    gets an n_items that is not a whole number of at least 2."""
    # TODO
    raise NotImplementedError


def bar_chart_svg(rows, title):
    """rows is a list of (label, value). Return an SVG string (see README for the contract):
    - raise ValueError if rows is empty or any value is negative
    - sort with sort_rows, axis_max = nice_max(largest value)
    - <text class="title"> with the title
    - for each tick from axis_ticks(axis_max): a <line class="gridline"> and a
      <text class="tick"> whose text is fmt(tick)
    - for each row, in sorted order, slot = PLOT_WIDTH / len(rows):
        <rect class="bar" data-label=label data-value=value (the number, as given)
              x = LEFT + i * slot + slot * 0.15, width = slot * 0.7,
              height = value / axis_max * PLOT_HEIGHT, y = BASELINE - height>
        <text class="value-label"> with fmt(value), above the bar
        <text class="bar-label"> with the label, under the baseline
    - a <line class="baseline"> at y = BASELINE
    Escape text with xml.sax.saxutils.escape so 'Parts & Accessories' is valid XML, and
    write attribute values with quoteattr, which adds the quotes and also escapes a " in a label.
    """
    # TODO
    raise NotImplementedError
