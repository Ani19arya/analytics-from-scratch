# Catch made-up numbers

Every number in the AI-written summary: is it actually in the data?

## The problem

Fenwick Supply, a fictional wholesaler, asked an LLM to write the half-year sales summary for the board pack. Dana, the finance director, likes the prose but does not trust the numbers, because LLMs can state a figure that sounds right and is not in the data. She wants every number in the summary checked against the order table before the pack goes out on Monday, with the wrong ones listed so they can be fixed.

The data in `data/orders.csv` (240 orders) and the summary in `data/ai_summary.csv` are synthetic, built by `make_data.py` with a fixed random seed. No API is called: the summary is a saved fixture, and a few of its numbers were made wrong on purpose.

## What you will build from scratch

- A regex that pulls every number out of a sentence, including `156,142` and `650.59`.
- A record of how precisely each number was stated (its decimal places).
- A checker that recomputes each claimed metric from the raw rows and flags every number that does not match.

## The idea

Checking a summary is three steps.

**1. Extract.** A number in prose can have thousands commas and decimals. The pattern:

```
\d{1,3}(?:,\d{3})+(?:\.\d+)?   digits in groups of three with commas, optional decimals
|\d+(?:\.\d+)?                 or plain digits, optional decimals
```

The comma branch comes first so `156,142` is read as one number, not as `156` and `142`. A full stop at the end of a sentence is not swallowed, because `\.\d+` needs a digit after the point.

**2. Link each number to a metric.** A regex cannot tell what a number means. In `ai_summary.csv` each sentence has a `metrics` column, written by the reviewer, that lists which metric each number claims, in order. If the counts differ, stop with an error rather than guess.

**3. Compare at the stated precision.** A summary that says 30.6% is not wrong because the true value is 30.5859. The rule: a stated number with `d` decimal places matches if

```
|actual - claimed| <= 0.5 * 10^(-d)
```

So `650.59` must be within 0.005, `41.1` within 0.05, and `52,000` within 0.5. That last case matters: rounding 51,319 up to a tidy 52,000 is a change of 681, and with no decimals stated the reader takes it as exact.

## Walk through

Pull the numbers out of one sentence:

```python
import re
NUMBER = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
s = "North was the largest region at $54,809, or 41.1% of revenue."
print(NUMBER.findall(s))
```

This prints `['54,809', '41.1']`. Strip the commas and convert to float.

Recompute the truth from the rows:

```python
import csv
rows = list(csv.DictReader(open("data/orders.csv")))
total = sum(int(r["revenue"]) for r in rows)
north = sum(int(r["revenue"]) for r in rows if r["region"] == "North")
print(total, north, round(north / total * 100, 1))
```

North revenue is right at 54,809, but the share is 35.1%, not 41.1%.

Run the worked answer to check all 11 numbers:

```
python3 solution/solution.py
```

Eight numbers match. Three are flagged: North's share (41.1% stated, 35.1% true), West revenue (52,000 stated, 51,319 true) and the January to June growth (25.0% stated, 30.6% true). Notice that the growth sentence gets both monthly figures right and still states the wrong percentage. Correct inputs do not prove a correct result.

Also notice what this check cannot do. Sentence S6 says all 3 regions grew. The 3 is right, but the claim that each region grew is a statement without a number, and the regex passes it. A number check catches made-up figures, not made-up claims.

## Your turn

Open `exercise.py`. Write the `NUMBER` pattern, then fill in `extract_numbers` and `check_summary`. `compute_metrics` and `matches` are already written. Then run, from this folder:

```
python3 test_lesson.py
```

## Check yourself

1. Why is the comma branch of the regex listed before the plain digits branch?
2. The true value is 30.5859 and the summary says 30.6%. Is that a match? What about 31%?
3. Why does the checker stop with an error when a sentence has more numbers than listed metrics?
4. Name one kind of wrong statement this checker will never flag.

<details>
<summary>Answers</summary>

1. Regex alternation tries branches left to right. With plain digits first, `156,142` would match as `156`, then `142`, two wrong numbers.
2. 30.6 with one decimal allows 0.05, and 30.5859 is 0.0141 away, so yes. 31 with no decimals allows 0.5, and 30.5859 is 0.4141 away, so it also matches. Precision as written sets the tolerance.
3. Pairing by position would then compare a number with the wrong metric and give a false pass or a false flag. A loud error is safer than a silent guess.
4. A claim with no number, such as "all regions grew", or a right number attached to the wrong label, if the reviewer tagged the metric wrong.

</details>

## In real job postings

Checking AI output against the data is a Python and SQL job. On the Real Analyst Jobs live feed read on 25 October 2026, 49% of the 914 India analyst postings that list tools ask for Python, and 48% of the 2,102 such US postings do. See [how to become an AI analyst](https://realanalystjobs.com/tools/how-to-become-an-ai-analyst) and the [Python skills page](https://realanalystjobs.com/skills/python).

## Next

That ends phase 06. Phase 07 (getting hired) is planned and not written yet. The [phase list](../../README.md) shows what is ready.
