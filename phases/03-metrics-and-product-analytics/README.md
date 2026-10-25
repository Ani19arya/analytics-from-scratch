# Metrics and product analytics

This phase is about the numbers a product team runs on: how to break a top-line metric into parts that explain a change, how to count a funnel and active users from raw events without inflating them, and how to pick a north star metric with guardrails and a launch rule written before the results arrive. Every lesson builds the metric from raw rows with the Python standard library or SQLite, on a small synthetic dataset, and follows the course format in [LESSON_TEMPLATE.md](../../LESSON_TEMPLATE.md).

1. [Metric trees](01-metric-trees/): split revenue into visitors x conversion x average order value and find which branch explains a week over week drop.
2. [Funnel conversion](02-funnel-conversion/): build a step by step funnel from raw events in SQL, and avoid counting events instead of users.
3. [Active users and stickiness](03-active-users-and-stickiness/): compute DAU, WAU, MAU and DAU/MAU, and see how the definition of active changes the number.
4. [North star and guardrails](04-north-star-and-guardrails/): compute a north star and two guardrails from a test, and apply a launch rule when they disagree.

Previous phase: [02 Statistics and experiments](../02-statistics-and-experiments/). Next phase: [04 Dashboards](../04-dashboards/).
