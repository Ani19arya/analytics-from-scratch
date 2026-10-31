"""Build the metrics glossary, the questions, and SIMULATED bot answers with citations.

- data/glossary.csv: Tiffinbell's metric definitions, one entry per row. Four metrics have an
  old, deprecated definition still sitting in the glossary next to the current one.
- data/questions.csv: questions analysts asked, each with the id of the glossary entry that
  answers it (the current definition).
- data/bot_answers.csv: what a glossary chatbot answered, with the entry ids it cited.
  No model was called. The answers are simulated: each one is built from a glossary entry,
  and some are damaged on purpose (a deprecated entry cited, the wrong metric cited, a number
  changed, no citation, a citation that does not exist). data/fixture.json says so.

build(seed) shuffles the entry ids, picks a wording for each question, and picks which
answers are damaged, so a second seed gives a different but comparable dataset. The answer
key (what was planted in each answer) is returned by build() and not written to the CSVs.

Run: python3 make_data.py
"""
import csv
import json
import os
import random
import re

DEFAULT_SEED = 667

# (metric, status, effective, text)
ENTRIES = [
    ("active_user", "current", "2026-04-01",
     "Active user: a customer with at least one completed order in the last 28 days. Opening the app without ordering does not count. This replaced the app-open definition on 1 April 2026."),
    ("active_user", "deprecated", "2023-01-01",
     "Active user: any user who opened the app at least once in the last 30 days counts as an active user, whether or not the user ordered."),
    ("daily_active_users", "current", "2026-04-01",
     "Daily active users (DAU): the number of distinct customers with a completed order on a given day."),
    ("average_order_value", "current", "2025-07-01",
     "Average order value (AOV): food subtotal of completed orders divided by the number of completed orders. Delivery fees and tips are excluded."),
    ("average_order_value", "deprecated", "2022-01-01",
     "Average order value (AOV): total paid for an order, including the delivery fee, averaged over all orders placed."),
    ("churned_customer", "current", "2025-10-01",
     "Churned customer: a customer whose last completed order was more than 90 days ago."),
    ("churned_customer", "deprecated", "2023-06-01",
     "Churned customer: a customer who has not ordered for 60 days or more."),
    ("late_delivery", "current", "2026-01-15",
     "Late delivery: an order delivered more than 10 minutes after the time promised in the app."),
    ("late_delivery", "deprecated", "2024-02-01",
     "Late delivery: an order delivered more than 15 minutes after the promised time."),
    ("gross_merchandise_value", "current", "2024-01-01",
     "Gross merchandise value (GMV): the total customers paid for completed orders, including delivery fees and tips, before refunds."),
    ("net_revenue", "current", "2024-01-01",
     "Net revenue: Tiffinbell's commission plus delivery fees on completed orders, minus refunds and the discounts Tiffinbell funds."),
    ("refund_rate", "current", "2024-01-01",
     "Refund rate: refunded orders divided by completed orders in the same period, counted by orders, not by money."),
    ("repeat_rate", "current", "2025-03-01",
     "Repeat rate: the share of customers whose first order was in a month who placed a second completed order within 30 days."),
    ("order_conversion_rate", "current", "2024-01-01",
     "Order conversion rate: app sessions that end with a completed order divided by all app sessions, per day."),
    ("customer_acquisition_cost", "current", "2024-01-01",
     "Customer acquisition cost (CAC): marketing spend in a month divided by the new customers whose first completed order was in that month."),
    ("retention_30_day", "current", "2025-03-01",
     "30-day retention: the share of a cohort of new customers with another completed order between day 1 and day 30 after their first."),
    ("delivery_time", "current", "2024-01-01",
     "Delivery time: minutes from the restaurant accepting the order to the courier marking it delivered. Reports show the median, not the mean."),
    ("cancellation_rate", "current", "2024-01-01",
     "Cancellation rate: orders cancelled before delivery divided by all orders placed."),
    ("new_customer", "current", "2024-01-01",
     "New customer: a customer whose first ever completed order falls in the period."),
    ("basket_size", "current", "2024-01-01",
     "Basket size: the average number of items in a completed order."),
    ("promo_share", "current", "2024-01-01",
     "Promo share: the share of completed orders that used a discount code."),
    ("courier_utilisation", "current", "2024-01-01",
     "Courier utilisation: minutes a courier spends on deliveries divided by the minutes the courier is logged in."),
    ("prep_time", "current", "2024-01-01",
     "Prep time: minutes from the restaurant accepting an order to the order being ready for pickup."),
    ("contact_rate", "current", "2024-01-01",
     "Contact rate: support tickets opened divided by completed orders."),
]

# Ways analysts asked about each current metric. build() picks one per metric.
QUESTION_WORDINGS = {
    "active_user": ["What counts as an active user?", "How do we define an active user?", "Who is an active user?"],
    "daily_active_users": ["How is DAU calculated?", "What are daily active users?"],
    "average_order_value": ["What is average order value?", "How do we calculate AOV?"],
    "churned_customer": ["When is a customer churned?", "What is a churned customer?"],
    "late_delivery": ["When is a delivery late?", "What counts as a late delivery?"],
    "gross_merchandise_value": ["What is GMV?", "How is gross merchandise value defined?"],
    "net_revenue": ["What is net revenue?", "How do we calculate net revenue?"],
    "refund_rate": ["How is refund rate calculated?", "What is the refund rate?"],
    "repeat_rate": ["What is repeat rate?", "How do we measure repeat customers?"],
    "order_conversion_rate": ["What is order conversion rate?", "How do we measure conversion from sessions to orders?"],
    "customer_acquisition_cost": ["How is CAC calculated?", "What is customer acquisition cost?"],
    "retention_30_day": ["What is 30-day retention?", "How do we measure retention of new customers?"],
    "delivery_time": ["How is delivery time measured?", "What does delivery time mean?"],
    "cancellation_rate": ["What is the cancellation rate?", "How do we count cancelled orders as a rate?"],
    "new_customer": ["Who counts as a new customer?", "What is a new customer?"],
    "basket_size": ["What is basket size?", "How many items is basket size?"],
    "promo_share": ["What is promo share?", "How much of our orders use discount codes?"],
    "courier_utilisation": ["What is courier utilisation?", "How busy are couriers, as a metric?"],
    "prep_time": ["What is prep time?", "How long do restaurants take to prepare food, as a metric?"],
    "contact_rate": ["What is contact rate?", "How do we measure support tickets per order?"],
}

KINDS = [("ok", 0.62), ("deprecated", 0.12), ("wrong_metric", 0.08), ("changed_number", 0.10),
         ("no_citation", 0.04), ("unknown_id", 0.04)]


def pick(options, rng):
    r = rng.random()
    total = 0.0
    for value, chance in options:
        total += chance
        if r < total:
            return value
    return options[-1][0]


def first_sentence(text):
    return text.split(". ")[0].rstrip(".") + "."


def change_number(text, rng):
    """Replace the first number in text with a different one."""
    m = re.search(r"\d+", text)
    if not m:
        return None
    old = int(m.group())
    new = old + rng.choice([-7, -5, 2, 5, 14])
    return text[:m.start()] + str(new) + text[m.end():]


def build(seed=DEFAULT_SEED):
    """Return {"glossary", "questions", "answers", "planted"} for this seed. Nothing is written."""
    rng = random.Random(seed)
    order = list(range(len(ENTRIES)))
    rng.shuffle(order)
    ids = rng.sample(range(100, 1000), len(ENTRIES))
    glossary = []
    for pos, idx in enumerate(order):
        metric, status, effective, text = ENTRIES[idx]
        glossary.append({"doc_id": "G%d" % ids[pos], "metric": metric, "status": status,
                         "effective_from": effective, "text": text})
    by_metric = {}
    for g in glossary:
        by_metric.setdefault(g["metric"], {})[g["status"]] = g
    questions, answers, planted = [], [], {}
    metrics = list(QUESTION_WORDINGS)
    for i, metric in enumerate(metrics, start=1):
        qid = "Q%02d" % i
        questions.append({"question_id": qid, "question": rng.choice(QUESTION_WORDINGS[metric]),
                          "answer_doc_id": by_metric[metric]["current"]["doc_id"]})
        current = by_metric[metric]["current"]
        has_old = "deprecated" in by_metric[metric]
        if metric == "active_user":
            kind = "deprecated"  # the case the stakeholder asked about
        else:
            kind = pick(KINDS, rng)
            if kind == "deprecated" and not has_old:
                kind = "ok"
            if kind == "changed_number" and not re.search(r"\d", current["text"]):
                kind = "ok"
        cited, text = [current["doc_id"]], first_sentence(current["text"])
        if kind == "deprecated":
            old = by_metric[metric]["deprecated"]
            cited, text = [old["doc_id"]], first_sentence(old["text"])
        elif kind == "wrong_metric":
            other = rng.choice([g for g in glossary if g["metric"] != metric and g["status"] == "current"])
            cited, text = [other["doc_id"]], first_sentence(other["text"])
        elif kind == "changed_number":
            text = change_number(first_sentence(current["text"]), rng)
        elif kind == "no_citation":
            cited = []
        elif kind == "unknown_id":
            cited = ["G%d" % rng.choice([x for x in range(1000, 1100)])]
        answers.append({"question_id": qid, "answer": text, "cited_doc_ids": ";".join(cited)})
        planted[qid] = kind
    return {"glossary": glossary, "questions": questions, "answers": answers, "planted": planted}


FIXTURE_INFO = {
    "file": "bot_answers.csv",
    "answer_source": "simulated",
    "model": "none: no model was called",
    "prompt": "Answer the analyst's question using only the glossary entries below. Cite the doc_id of every entry you use.",
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "Each answer is the first sentence of a glossary entry. Some were damaged on purpose: a deprecated "
           "entry cited, another metric cited, a number changed, the citation left out, or an id that does not exist.",
    "glossary_source": "synthetic, written for this lesson",
    "seed": DEFAULT_SEED,
}

COLUMNS = {
    "glossary": ["doc_id", "metric", "status", "effective_from", "text"],
    "questions": ["question_id", "question", "answer_doc_id"],
    "bot_answers": ["question_id", "answer", "cited_doc_ids"],
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    built = build()
    built["bot_answers"] = built["answers"]
    for name, cols in COLUMNS.items():
        with open(os.path.join(data, name + ".csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(built[name])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", data)


if __name__ == "__main__":
    main()
