# Draw a chart from scratch

What does a dashboard tool do when it turns a table into a bar chart, and which chart should you pick in the first place?

## The problem

You are the analyst at Juniper Bikes, a bike shop with six product lines. Leo, the owner, wants revenue by product line on one slide for the bank meeting on Wednesday, and he has asked for it "in 3D, with the axis zoomed in so the differences pop". Power BI and Tableau draw bars for you, but they also let you make every one of those mistakes. You will write the chart yourself in plain Python, as an SVG file, so you know what every pixel means: the axis scale, the bar order, the labels and the zero line. Then you will explain to Leo why the chart is flat and starts at zero.

## What you will build from scratch

- `nice_max`: round the largest value up to a readable axis maximum (50,000, not 38,900).
- `axis_ticks`: evenly spaced ticks from zero to that maximum.
- `sort_rows`: largest bar first, with a stable tie breaker.
- `bar_chart_svg`: an SVG bar chart with a title, gridlines, tick labels, bars that start at zero, value labels and category labels.
- `choose_chart`: the first rule of chart choice, as code.

The data in `data/` is synthetic. `make_data.py` builds it with a fixed random seed: revenue for six product lines.

## The idea

### Choosing the chart

Pick the chart from the question, before the tool:

- **Comparing categories** (which product line sells most): bars. Length is the visual property people compare most accurately, and sorted bars make the ranking readable at a glance.
- **Change over time** (how revenue moved by month): a line. The x axis is ordered and continuous, and the slope shows the change.
- **No 3D.** Perspective makes the front bars look bigger than the back ones and hides values behind other bars. The extra dimension carries no data.
- **No dual axes without a reason.** Two y axes with different scales let you make any two lines look related by stretching one of them. Use two charts side by side, or index both series to 100, unless the two measures are tightly linked and the reader knows both scales.
- **Bars start at zero.** A bar's length is the value. If the axis starts at 28,000, a bar for 38,900 looks four times as long as a bar for 30,500, when it is about 1.3 times as large. A line chart may zoom in, because a line encodes position and slope, not length.

### Drawing it

An SVG is text. A bar is a rectangle: `<rect x y width height>`. SVG's y axis points down, so y = 0 is the top of the image. That gives the three formulas the whole chart rests on:

```
axis_max   = nice_max(largest value)
bar height = value / axis_max * PLOT_HEIGHT
bar y      = BASELINE - bar height          (BASELINE is the y of the zero line)
```

`nice_max` picks the smallest number at least as big as the largest value of the form m x 10^k with m in 1, 2, 2.5 or 5. For 38,900 that is 50,000. Five equal steps then put ticks on 0, 10,000, 20,000, 30,000, 40,000 and 50,000.

The contract the test checks, with the image 600 by 400:

| Constant | Value | Meaning |
|---|---|---|
| `LEFT`, `TOP` | 60, 40 | margins for tick labels and the title |
| `PLOT_WIDTH`, `PLOT_HEIGHT` | 520, 300 | the area the bars live in |
| `BASELINE` | 340 | `TOP + PLOT_HEIGHT`, the zero line |

Each bar gets a slot of `PLOT_WIDTH / number of bars`, and fills the middle 70% of it.

## Walk through

Step 1. Load the table and sort it. Sorting is a design decision: unsorted bars make the reader do the ranking.

```python
import csv

with open("data/product_line_revenue.csv", newline="") as f:
    rows = [(r["product_line"], int(r["revenue"])) for r in csv.DictReader(f)]

rows = sorted(rows, key=lambda r: (-r[1], r[0]))
print(rows)
```

Service leads at 38,900, then Kids at 30,500 and Mountain at 24,700. The tie breaker on the label keeps the order the same on every run when two values are equal.

Step 2. A nice axis maximum. Find the power of ten just below the value, then try 1, 2, 2.5, 5 and 10 times it.

```python
def nice_max(value):
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

print(nice_max(38900), nice_max(42), nice_max(1234), nice_max(0.3))
```

That prints 50000.0, 50.0, 2000.0 and 0.5. The second loop matters for values below 1.

Step 3. Scale a bar, and see what a truncated axis does.

```python
PLOT_HEIGHT, BASELINE = 300, 340
axis_max = nice_max(38900)
for label, value in rows[:2]:
    h = value / axis_max * PLOT_HEIGHT
    print(label, "height", round(h, 2), "y", round(BASELINE - h, 2))

honest = 38900 / 30500
truncated = (38900 - 28000) / (30500 - 28000)
print("Service vs Kids, true ratio", round(honest, 2), "ratio of bar lengths from 28,000:", round(truncated, 2))
```

Service is 233.4 pixels tall and Kids is 183.0. With the axis starting at 28,000, Service's bar would be 4.36 times as long as Kids', for a real gap of 1.28 times.

Step 4. Write one bar as SVG. `escape` turns `&` into `&amp;`. Without it, the label `Parts & Accessories` makes the file invalid XML and the browser refuses to draw it.

```python
from xml.sax.saxutils import escape

label, value = "Parts & Accessories", 8700
h = value / axis_max * PLOT_HEIGHT
bar = '<rect class="bar" data-label="%s" x="%.2f" y="%.2f" width="%.2f" height="%.2f"/>' % (escape(label), 100, BASELINE - h, 60.67, h)
print(bar)
```

Step 5. Put it together. Wrap the pieces in an `<svg>` element, draw the gridlines and ticks first so the bars sit on top, then each bar with its value above and its label below, then the zero line. Check that the result parses as XML. Save the string to a `.svg` file and any browser will draw it.

```python
import xml.etree.ElementTree as ET

parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400">', bar,
         '<line class="baseline" x1="60" x2="580" y1="340" y2="340" stroke="#333"/>', "</svg>"]
svg = "\n".join(parts)
ET.fromstring(svg)  # raises an error if the SVG is not valid XML
print(len(svg), "characters of valid SVG")
```

`bar_chart_svg` in the exercise does this for every row, with the exact class names listed in its docstring.

### The same chart in Power BI and Tableau (reference only, not run in this course)

```text
Power BI: Clustered column chart. X axis = product_line, Y axis = Sum of revenue.
  More options (...) > Sort axis > Sum of revenue, Sort descending.
  Format > Y axis > Range > Minimum = 0. Data labels = On.

Tableau: product_line on Columns, SUM(revenue) on Rows, mark type Bar.
  Sort descending by SUM(revenue). Edit Axis > Include zero (on by default).
  Label marks with SUM(revenue).
```

Both tools start a bar axis at zero by default. Both let you override it, which is the change to refuse.

## Your turn

Open `exercise.py` and fill in `nice_max`, `axis_ticks`, `sort_rows`, `choose_chart` and `bar_chart_svg`. The constants and the `fmt` number formatter are already there.

```
python3 test_lesson.py
```

Run it from this folder. The test parses your SVG as XML and checks the bar order, every bar's height against the axis, that every bar starts at the zero line, the tick labels, the value and category labels, and that negative values are refused.

## Check yourself

1. When is it fine for an axis not to start at zero?
2. A stakeholder wants revenue and conversion rate on one chart with two y axes. What do you suggest?
3. Why sort a bar chart by value instead of alphabetically?
4. Your chart has twelve months on the x axis. Bars or a line?

<details>
<summary>Answers</summary>

1. On a line chart or a dot plot, which encode values by position, not length. Small changes in a large number, such as a temperature or a stock price, are readable there. Bars must start at zero because their length is the value.
2. Two charts aligned on the same x axis, or one chart with both series indexed to 100. A dual axis lets the scale choice invent a correlation, so use it only when the reader already knows both measures and the link between them.
3. The question is usually which is biggest and by how much. Sorted bars answer it without the reader scanning back and forth. Sort alphabetically only when people look up a known category, and keep a natural order (sizes, age bands, months) when the categories have one.
4. A line, because time is ordered and the question is about the trend. Bars for time are acceptable for a few periods where each is a separate total, such as four quarters.

</details>

## In real job postings

On 25 October 2026 the Real Analyst Jobs live feed had 2,848 US analyst postings. Of the 2,102 that list tools, 36% ask for Tableau, 24% for Power BI and 48% for Python. In India, Power BI leads Tableau, 39% to 34%. See the [Power BI vs Tableau study](https://realanalystjobs.com/research/power-bi-vs-tableau-job-postings-2026) and the [Python skills page](https://realanalystjobs.com/skills/python).

## Next

[05 Python for analysts](../../05-python-for-analysts/)
