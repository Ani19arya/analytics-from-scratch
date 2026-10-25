# Grade an LLM classifier

Is the LLM good enough at spotting refund tickets that we can route them automatically?

## The problem

Northwind Desk, a fictional software company, tried an LLM to label incoming support tickets as billing, bug, refund or other. Priya, the support lead, wants refund tickets to skip the queue and go straight to the refunds team, but only if it rarely sends the wrong ticket there and rarely misses a real refund. Her rule: precision for refund at least 0.90 and recall at least 0.80. A human already labelled 400 recent tickets, and the LLM's labels for the same tickets are saved next to them. She needs a yes or no by Friday's ops review.

The dataset in `data/tickets.csv` is synthetic, built by `make_data.py` with a fixed random seed. No API is called: the LLM labels are a saved fixture.

## What you will build from scratch

- A confusion matrix from two label columns, as a dict of dicts.
- Accuracy, and precision, recall and F1 for any one label.
- A check of the metrics against a stated business rule, with a yes or no answer.

## The idea

Treat the human label as the truth. For each ticket you know the actual label and the predicted label. Count every pair: `cm[actual][predicted]`. The diagonal is where the LLM agreed with the human.

For one label, say refund:

- True positives (TP): actual refund, predicted refund. That is `cm["refund"]["refund"]`.
- False positives (FP): predicted refund, actually something else. Sum down the refund column, minus the diagonal.
- False negatives (FN): actual refund, predicted something else. Sum across the refund row, minus the diagonal.

Then:

```
precision = TP / (TP + FP)    of the tickets we would route to refunds, how many belong there
recall    = TP / (TP + FN)    of the real refund tickets, how many we would catch
F1        = 2 * precision * recall / (precision + recall)
accuracy  = sum of the diagonal / all tickets
```

If a denominator is zero, return 0.0 instead of crashing.

Accuracy alone can hide the problem. A model can score well overall because it is great at the big classes, while the one class the business cares about is weak. Precision answers "how often is the automatic action wrong", recall answers "how much do we still miss". The business rule says which one matters more.

## Walk through

Load the rows and count pairs:

```python
import csv
rows = list(csv.DictReader(open("data/tickets.csv")))
labels = ["billing", "bug", "refund", "other"]
cm = {a: {p: 0 for p in labels} for a in labels}
for r in rows:
    cm[r["human_label"]][r["llm_label"]] += 1
print(cm["refund"])
```

Precision and recall for refund:

```python
tp = cm["refund"]["refund"]
fp = sum(cm[a]["refund"] for a in labels if a != "refund")
fn = sum(cm["refund"][p] for p in labels if p != "refund")
print(tp / (tp + fp), tp / (tp + fn))
```

Run the full worked answer to see the whole report:

```
python3 solution/solution.py
```

On this data, accuracy is 0.868, which sounds fine. Refund recall is 0.847, which passes. Refund precision is 0.813 (61 of 75 predicted refunds), which fails the 0.90 bar. Most of the wrong ones are billing tickets: 13 billing tickets would have gone to the refunds team. The answer for Priya is no, and the fix to try next is the billing versus refund boundary.

## Your turn

Open `exercise.py` and fill in `confusion_matrix`, `accuracy`, `precision_recall_f1` and `meets_rule`. Then run, from this folder:

```
python3 test_lesson.py
```

## Check yourself

1. Why is accuracy a poor single number for this decision?
2. The refunds team says a wrong ticket costs them far more than a missed one. Which metric do you push up, and what usually happens to the other?
3. Where in the confusion matrix do you look to find out what the LLM confuses refunds with?

<details>
<summary>Answers</summary>

1. It averages over all classes. Strong results on billing and bug can cover a weak refund class, and the rule is about refund only.
2. Precision. Making the model stricter about saying refund usually lowers recall, so you trade misses for fewer wrong routings.
3. The refund column (false positives come from other rows) and the refund row (false negatives go to other columns). Here the billing row, refund column cell is the biggest error.

</details>

## In real job postings

This lesson is evaluation work: checking a model's output against a trusted answer, in Python. On the Real Analyst Jobs live feed read on 25 October 2026, 48% of the 2,102 US analyst postings that list tools ask for Python. See [how to become an AI analyst](https://realanalystjobs.com/tools/how-to-become-an-ai-analyst).

## Next

[Check LLM-written SQL](../02-check-llm-written-sql/)
