"""Build data/tickets.csv: synthetic support tickets with a human label and a SIMULATED LLM label.

No model was called. The llm_label column is made up by this file, so the lesson
runs offline and gives the same numbers every time. It is simulated so that it
behaves the way a real model at temperature 0 does:

- It depends on the ticket text. The same text always gets the same label.
- Clear wording is almost always labelled right. Ambiguous wording (a charge the
  customer wants reversed: billing or refund?) is where most mistakes happen.

How: every ticket comes from a wording template, and every template has its own
error rates. For each distinct text the label is drawn once, with a random
generator seeded by (seed, text). That is "a deterministic function of the text
plus controlled noise". The provenance is written to data/fixture.json.

Run: python3 make_data.py
"""
import csv
import json
import os
import random

DEFAULT_SEED = 601
LABELS = ["billing", "bug", "refund", "other"]
CLASS_MIX = {"billing": 0.30, "bug": 0.25, "refund": 0.20, "other": 0.25}

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October"]
PLANS = ["annual plan", "team plan", "pro plan", "starter plan"]
PAGES = ["reports", "settings", "billing", "exports", "dashboard", "inbox"]
CITIES = ["Pune", "Leeds", "Austin", "Lyon", "Perth"]
OPENINGS = ["", "Hi, ", "Hello, ", "Hi team, ", "Urgent: "]
CLOSINGS = ["", ". Thanks", ". Thank you", "?", ", account {acct}"]

# (human label, wording, how the simulated LLM labels it).
# The last field is the chance of each LLM label for that wording. Clear wording
# is right about 97% of the time. Ambiguous wording is where the errors live.
TEMPLATES = [
    ("billing", "Please update the card on my account before the {month} renewal",
     {"billing": 0.97, "other": 0.03}),
    ("billing", "Why did my invoice go up in {month}",
     {"billing": 0.96, "refund": 0.02, "other": 0.02}),
    ("billing", "I need a copy of the {month} invoice for invoice {inv}",
     {"billing": 0.97, "other": 0.03}),
    ("billing", "Can I pay for the {plan} by bank transfer",
     {"billing": 0.95, "other": 0.05}),
    ("billing", "My card was declined when I renewed the {plan}",
     {"billing": 0.96, "bug": 0.02, "other": 0.02}),
    # ambiguous: a wrong charge that should be corrected, not refunded
    ("billing", "I was charged twice in {month}, please reverse one of them",
     {"billing": 0.25, "refund": 0.75}),
    ("billing", "You charged me ${amount} instead of ${amount2} for the {plan}",
     {"billing": 0.35, "refund": 0.65}),
    ("refund", "Please refund the {plan} I bought by mistake",
     {"refund": 0.97, "billing": 0.03}),
    ("refund", "Order {order} never arrived and I want a refund",
     {"refund": 0.96, "other": 0.04}),
    ("refund", "I want my money back for order {order}",
     {"refund": 0.95, "billing": 0.05}),
    ("refund", "Cancel the {plan} and refund the ${amount}",
     {"refund": 0.93, "billing": 0.07}),
    # ambiguous: the customer wants money back but talks about a charge
    ("refund", "I cancelled in {month} but you still charged me ${amount}, I want it back",
     {"refund": 0.45, "billing": 0.55}),
    ("refund", "Please return the ${amount} you took after I cancelled the {plan}",
     {"refund": 0.60, "billing": 0.40}),
    ("bug", "The export button does nothing on the {page} page",
     {"bug": 0.97, "other": 0.03}),
    ("bug", "The app crashes when I open {page}",
     {"bug": 0.98, "other": 0.02}),
    ("bug", "The {page} page is blank since the {month} update",
     {"bug": 0.97, "other": 0.03}),
    ("bug", "Login loops back to the start when I open {page}",
     {"bug": 0.96, "other": 0.04}),
    ("bug", "The {page} page takes a minute to load, is that normal",
     {"bug": 0.70, "other": 0.30}),
    ("other", "Do you have a student discount on the {plan}",
     {"other": 0.93, "billing": 0.07}),
    ("other", "How do I invite a teammate to {page}",
     {"other": 0.95, "bug": 0.05}),
    ("other", "Can I change my username before {month}",
     {"other": 0.98, "bug": 0.02}),
    ("other", "Do you have an office in {city}",
     {"other": 0.99, "billing": 0.01}),
    ("other", "Where can I download all my invoices from {month}",
     {"other": 0.55, "billing": 0.45}),
]


def draw(weights, rng):
    """Pick a key from a dict of chances, in LABELS order, with one random draw."""
    r = rng.random()
    total = 0.0
    for key in LABELS:
        total += weights.get(key, 0.0)
        if r < total:
            return key
    return max(weights, key=weights.get)


def fill(template, rng):
    amount = rng.choice([19, 29, 49, 79, 99, 149, 199, 249])
    opening = rng.choice(OPENINGS)
    if opening and not template.startswith("I "):
        template = template[0].lower() + template[1:]
    template = opening + template + rng.choice(CLOSINGS)
    return template.format(
        month=rng.choice(MONTHS),
        plan=rng.choice(PLANS),
        page=rng.choice(PAGES),
        city=rng.choice(CITIES),
        inv="INV-%05d" % rng.randint(10000, 99999),
        order="%d" % rng.randint(10000, 99999),
        acct="A%04d" % rng.randint(1000, 9999),
        amount=amount,
        amount2=amount - rng.choice([10, 20, 30]) if amount > 29 else amount + 10,
    )


def simulated_llm_label(text, chances, seed):
    """The same text always gets the same label: the noise is seeded by the text."""
    return draw(chances, random.Random("%d|%s" % (seed, text)))


def build(seed=DEFAULT_SEED, n=400):
    """Return {"tickets": [dict, ...]} for this seed. Nothing is written."""
    rng = random.Random(seed)
    by_class = {label: [t for t in TEMPLATES if t[0] == label] for label in LABELS}
    rows = []
    for i in range(1, n + 1):
        human = draw(CLASS_MIX, rng)
        _, template, chances = rng.choice(by_class[human])
        text = fill(template, rng)
        rows.append({
            "ticket_id": "T%04d" % i,
            "text": text,
            "human_label": human,
            "llm_label": simulated_llm_label(text, chances, seed),
        })
    return {"tickets": rows}


FIXTURE_INFO = {
    "file": "tickets.csv",
    "llm_label_source": "simulated",
    "model": "none: no model was called",
    "prompt_version": "none",
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "make_data.py draws each distinct text's label once, seeded by (seed, text), "
           "from error rates set per wording template. Ambiguous wording carries most errors.",
    "human_label_source": "simulated single human labeller, treated as the truth",
    "seed": DEFAULT_SEED,
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    path = os.path.join(data, "tickets.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticket_id", "text", "human_label", "llm_label"])
        w.writeheader()
        w.writerows(build()["tickets"])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
