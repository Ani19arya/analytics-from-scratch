# Statistics and experiments

This phase teaches the statistics an analyst uses every week: how to summarise a skewed number honestly, how sure you can be about an average or a rate from a sample, whether an A/B test result is real or luck, and how big a test must be before it starts. Every method is built by hand with the Python standard library (no `statistics` module, no scipy), on a small synthetic dataset, and checked by a test that computes the answer independently. Each lesson follows the course format in [LESSON_TEMPLATE.md](../../LESSON_TEMPLATE.md): a business problem, the idea in plain words, a diagram, a walk through, common mistakes, an exercise and what to tell the stakeholder.

You need Python 3.9 or later. No SQL is required, though [GROUP BY from raw rows](../01-sql/01-group-by-from-raw-rows/) helps with lesson 01.

## Lessons, in learning order

Folder numbers stay fixed because they are live links; the list below is the order to take them in.

**Level 1: beginner**

1. [05 Probability and distributions by simulation](05-probability-by-simulation/): if 10% of visitors buy, how many of 200 should buy, and how unusual is 30?
2. [01 Mean, median and skew](01-mean-median-and-skew/): what is the typical posted pay for an analyst role, and which number goes on the slide? Adds spread (SD, P25 and P75) and a histogram.
3. [06 Spread, percentiles and outliers](06-spread-percentiles-and-outliers/): most analyst roles pay between what and what?
4. [07 Sampling and the central limit theorem](07-sampling-and-the-clt/): why does the average of 18 orders wobble, and by how much?
5. [02 Confidence interval by hand](02-confidence-interval-by-hand/): how sure are we about an average or a rate measured on a sample?

**Level 2: intermediate**

6. [08 Hypothesis testing by permutation](08-hypothesis-test-by-permutation/): could this gap appear just by shuffling the labels?
7. [03 A/B test from scratch](03-ab-test-from-scratch/): did the new checkout page really convert better, or did we get lucky? Includes a sample ratio mismatch check and a confidence interval on the lift.
8. [04 Sample size before you test](04-sample-size-before-you-test/): how many users, and how many weeks, before a test can answer the question?
9. [09 Comparing categories: the chi-square test](09-chi-square-test/): do the three signup flows differ in completion rate?
10. [10 Correlation, causation and Simpson's paradox](10-correlation-causation-and-simpson/): users who get more notifications work out more. Should we send more?
11. [11 Linear regression from scratch](11-linear-regression-from-scratch/): how much does each extra visit add to monthly spend, and what does R squared really say?
12. [12 Bootstrap confidence intervals](12-bootstrap-intervals/): how sure are we about a median or a ratio when no simple formula exists?

**Level 3: advanced**

13. [13 A/B test pitfalls](13-ab-test-pitfalls/): we tested five variants on three metrics. Which wins are real?
14. [14 Ratio metrics and the delta method](14-ratio-metrics-and-the-delta-method/): is the drop in replies per application real when one user sends many?
15. [15 Variance reduction with CUPED](15-variance-reduction-with-cuped/): can pre-test behaviour make the test finish in half the time?

**About prerequisites for the interval lesson.** Lessons 05 (probability by simulation) and 07 (sampling and the central limit theorem) are the intended prerequisites for [02 Confidence interval by hand](02-confidence-interval-by-hand/). Until they exist, lesson 02 includes a short version of both: the normal bell curve, where 1.96 comes from, and a simulation of 1,000 surveys that you can run.

## How to run a lesson

```
cd phases/02-statistics-and-experiments/01-mean-median-and-skew
python3 test_lesson.py                      # fails until your exercise.py is right
CHECK_SOLUTION=1 python3 test_lesson.py     # shows the worked solution passing
python3 make_data.py                        # rebuilds data/ exactly as committed
```

Every test checks your code on the committed data and on a second dataset built with another seed, so an answer typed in by hand will not pass.

Previous phase: [01 SQL from raw tables](../01-sql/). Next phase: [03 Metrics and product analytics](../03-metrics-and-product-analytics/).
