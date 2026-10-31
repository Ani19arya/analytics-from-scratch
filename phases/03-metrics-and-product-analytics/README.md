# Metrics and product analytics

This phase is about the numbers a product team runs on: how to break a top-line metric into parts that explain a change, how to count a funnel and active users from raw events without inflating them, and how to pick a north star metric with guardrails and a launch rule, written before the results arrive, that allows for noise. Every lesson builds the metric from raw rows with the Python standard library or SQLite, on a small synthetic dataset, and follows the course format in [LESSON_TEMPLATE.md](../../LESSON_TEMPLATE.md).

**Before you start:** the SQL lessons in [phase 01](../01-sql/) and the statistics lessons in [phase 02](../02-statistics-and-experiments/). Each lesson lists its own prerequisites, level (1 beginner, 2 intermediate, 3 advanced) and time.

**How to run a lesson:** open its folder in a terminal and run `python3 test_lesson.py`. It fails until you fill in the exercise. `CHECK_SOLUTION=1 python3 test_lesson.py` runs the tests on the worked answer. Python 3.9 or later, nothing to install.

## Lessons, in order

1. [Metric trees](01-metric-trees/) (level 2): split revenue into visitors x conversion x average order value with the logarithmic mean (LMDI), and find which branch explains a week over week drop.
2. [Funnel conversion](02-funnel-conversion/) (level 1): build a step by step funnel from raw events in SQL, count users not events, and choose which step to work on.
3. [Active users and stickiness](03-active-users-and-stickiness/) (level 1): compute DAU, WAU, MAU and DAU/MAU, and see how the definition of active changes the number.
4. [North star and guardrails](04-north-star-and-guardrails/) (level 2): compute a north star and two guardrails from a test, and apply a pre-registered, noise-aware launch rule with a guardrail veto.
5. Define a metric precisely (planned): what exactly counts as an active customer, and what goes in the metric spec?
6. Percent vs points, ratio of sums vs average of ratios (planned): did conversion rise 2% or 2 points, and why do two dashboards disagree?
7. Growth accounting (planned): where did this month's MAU change come from: new, retained, resurrected or churned users?
8. Retention curves and churn (planned): what share of users are still here on day 7 and day 30, and which retention definition fits?
9. Segmentation and mix effects (planned): did conversion fall, or did the traffic mix change?
10. Diagnose a metric drop (planned): DAU fell 20% overnight. Tracking bug, holiday, segment, or real?
11. Attribution: first touch, last touch, linear (planned): which channel gets credit for the sale, and how much does the answer depend on the model?
12. Unit economics: LTV, CAC and payback (planned): is paid social acquisition profitable once churn is included?
13. Marketplace metrics and liquidity (planned): what share of job posts get an application within 48 hours, and which side is the constraint?
14. Causal impact without an experiment: difference in differences (planned): we launched in one city and not the others. Did it work?

Previous phase: [02 Statistics and experiments](../02-statistics-and-experiments/). Next phase: [04 Dashboards](../04-dashboards/).
