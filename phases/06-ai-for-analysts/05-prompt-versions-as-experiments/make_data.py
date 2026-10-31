"""Build the data for lesson 06-05: 200 SYNTHETIC support tickets with a gold label, and the
SIMULATED labels of two prompt versions, v1 and v2, run on the same tickets.

No model was called. The labels are made up by this file, so the lesson runs offline
and gives the same numbers every time. They are simulated to behave the way a real
model at temperature 0 does when you change its prompt:

- Each label depends on the ticket text. The same text always gets the same label.
- Both versions share one random number per text ("common random numbers"). Where the
  prompt change does not touch a wording, both versions give the same label, as a real
  model mostly does. Where v2 changes the chances, some labels flip, both ways.

Also written, for the Common mistakes section:
- other_week_v2.csv: v2 run by its author on a DIFFERENT week's tickets, which had
  fewer ambiguous wordings.
- dev_examples.csv: the 10 tickets the author looked at while writing v2.

Run: python3 make_data.py
"""
import csv
import json
import os
import random

DEFAULT_SEED = 610
LABELS = ["billing", "bug", "refund", "other"]
CLASS_MIX = {"billing": 0.30, "bug": 0.25, "refund": 0.20, "other": 0.25}

PROMPT_V1 = ("Label this support ticket as exactly one of: billing, bug, refund, other. "
             "Answer with the label only.")
PROMPT_V2 = (PROMPT_V1 + " A request to reverse, correct or explain a charge is billing. "
             "Use refund only when the customer asks for money back for something they "
             "bought or cancelled. Example: 'I was charged twice, please reverse one' is billing.")

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October"]
PLANS = ["annual plan", "team plan", "pro plan", "starter plan"]
PAGES = ["reports", "settings", "exports", "dashboard", "inbox"]
OPENINGS = ["", "Hi, ", "Hello, ", "Hi team, "]
CLOSINGS = ["", ". Thanks", "?", ", account {acct}"]

# (gold label, wording, ambiguous?, chances under v1, chances under v2).
# v2 adds a rule for charges, so it fixes the "reverse a charge" wordings and
# over-applies the rule to a few refund and other wordings.
TEMPLATES = [
    ("billing", "Please update the card on my account before the {month} renewal", False,
     {"billing": 0.97, "other": 0.03}, {"billing": 0.97, "other": 0.03}),
    ("billing", "Why did my invoice go up in {month}", False,
     {"billing": 0.95, "refund": 0.03, "other": 0.02}, {"billing": 0.97, "refund": 0.01, "other": 0.02}),
    ("billing", "Can I pay for the {plan} by bank transfer", False,
     {"billing": 0.95, "other": 0.05}, {"billing": 0.95, "other": 0.05}),
    ("billing", "I was charged twice in {month}, please reverse one of them", True,
     {"billing": 0.20, "refund": 0.80}, {"billing": 0.92, "refund": 0.08}),
    ("billing", "You charged me ${amount} instead of ${amount2} for the {plan}", True,
     {"billing": 0.35, "refund": 0.65}, {"billing": 0.85, "refund": 0.15}),
    ("refund", "Please refund the {plan} I bought by mistake", False,
     {"refund": 0.97, "billing": 0.03}, {"refund": 0.97, "billing": 0.03}),
    ("refund", "Order {order} never arrived and I want a refund", False,
     {"refund": 0.96, "other": 0.04}, {"refund": 0.96, "other": 0.04}),
    ("refund", "I want my money back for order {order}", False,
     {"refund": 0.95, "billing": 0.05}, {"refund": 0.95, "billing": 0.05}),
    ("refund", "I cancelled in {month} but you still charged me ${amount}, I want it back", True,
     {"refund": 0.55, "billing": 0.45}, {"refund": 0.45, "billing": 0.55}),
    ("bug", "The export button does nothing on the {page} page", False,
     {"bug": 0.97, "other": 0.03}, {"bug": 0.97, "other": 0.03}),
    ("bug", "The app crashes when I open {page}", False,
     {"bug": 0.98, "other": 0.02}, {"bug": 0.98, "other": 0.02}),
    ("bug", "The {page} page takes a minute to load, is that normal", True,
     {"bug": 0.70, "other": 0.30}, {"bug": 0.70, "other": 0.30}),
    ("other", "Do you have a student discount on the {plan}", False,
     {"other": 0.93, "billing": 0.07}, {"other": 0.88, "billing": 0.12}),
    ("other", "How do I invite a teammate to {page}", False,
     {"other": 0.95, "bug": 0.05}, {"other": 0.95, "bug": 0.05}),
    ("other", "Where can I download all my invoices from {month}", True,
     {"other": 0.55, "billing": 0.45}, {"other": 0.50, "billing": 0.50}),
]


def draw(chances, u, gold):
    """Pick a label from a dict of chances with one uniform number u. The gold label is walked
    first, then the others in LABELS order, so a version is right exactly when u < its chance of
    the gold label. Sharing u between versions keeps their labels together where they agree."""
    total = 0.0
    for label in [gold] + [k for k in LABELS if k != gold and k in chances]:
        total += chances[label]
        if u < total:
            return label
    return max(chances, key=chances.get)


def fill(template, rng):
    amount = rng.choice([29, 49, 79, 99, 149, 199, 249])
    opening = rng.choice(OPENINGS)
    if opening and not template.startswith("I "):
        template = template[0].lower() + template[1:]
    template = opening + template + rng.choice(CLOSINGS)
    return template.format(
        month=rng.choice(MONTHS), plan=rng.choice(PLANS), page=rng.choice(PAGES),
        order="%d" % rng.randint(10000, 99999), acct="A%04d" % rng.randint(1000, 9999),
        amount=amount, amount2=amount - rng.choice([10, 20]),
    )


def label_pair(text, template, seed):
    """Both versions' labels for one text, from one random number seeded by (seed, text)."""
    u = random.Random("%d|%s" % (seed, text)).random()
    return draw(template[3], u, template[0]), draw(template[4], u, template[0])


def make_tickets(rng, n, seed, prefix, ambiguous_weight):
    by_class = {label: [t for t in TEMPLATES if t[0] == label] for label in LABELS}
    rows = []
    for i in range(1, n + 1):
        u, total, gold = rng.random(), 0.0, LABELS[-1]
        for label in LABELS:
            total += CLASS_MIX[label]
            if u < total:
                gold = label
                break
        options = by_class[gold]
        weights = [ambiguous_weight if t[2] else 1.0 for t in options]
        template = rng.choices(options, weights=weights)[0]
        text = fill(template[1], rng)
        v1, v2 = label_pair(text, template, seed)
        rows.append({"ticket_id": "%s%04d" % (prefix, i), "text": text, "gold_label": gold,
                     "v1_label": v1, "v2_label": v2})
    return rows


def build(seed=DEFAULT_SEED, n=200):
    """Return {"tickets", "run_v1", "run_v2", "other_week_v2", "dev_examples"}. Nothing is written."""
    rng = random.Random(seed)
    week = make_tickets(rng, n, seed, "T", ambiguous_weight=1.0)
    other = make_tickets(rng, n, seed, "W", ambiguous_weight=0.25)
    # The author's 10 examples: ambiguous charge wordings that v2 gets right.
    dev, tries = [], 0
    charge = [t for t in TEMPLATES if t[2] and t[0] == "billing"]
    while len(dev) < 10 and tries < 10000:
        tries += 1
        template = rng.choice(charge)
        text = fill(template[1], rng)
        v1, v2 = label_pair(text, template, seed)
        if v2 == template[0] and text not in {d["text"] for d in dev}:
            dev.append({"ticket_id": "D%02d" % (len(dev) + 1), "text": text, "gold_label": template[0],
                        "v1_label": v1, "v2_label": v2})
    return {
        "tickets": [{"ticket_id": r["ticket_id"], "text": r["text"], "gold_label": r["gold_label"]} for r in week],
        "run_v1": [{"ticket_id": r["ticket_id"], "label": r["v1_label"]} for r in week],
        "run_v2": [{"ticket_id": r["ticket_id"], "label": r["v2_label"]} for r in week],
        "other_week_v2": [{"ticket_id": r["ticket_id"], "text": r["text"], "gold_label": r["gold_label"],
                           "label": r["v2_label"]} for r in other],
        "dev_examples": dev,
    }


FIXTURE_INFO = {
    "files": ["run_v1.csv", "run_v2.csv", "other_week_v2.csv", "dev_examples.csv"],
    "label_source": "simulated",
    "model": "none: no model was called",
    "prompt_v1": PROMPT_V1,
    "prompt_v2": PROMPT_V2,
    "temperature": "simulated as 0: the same text always gets the same label",
    "date": "not applicable",
    "how": "make_data.py draws one random number per (seed, text) and maps it through each version's "
           "chances for that wording template, so the two versions only disagree where v2 changed the chances.",
    "gold_label_source": "simulated single human labeller, treated as the truth",
    "seed": DEFAULT_SEED,
}


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    d = build()
    for name in ("tickets", "run_v1", "run_v2", "other_week_v2", "dev_examples"):
        write_csv(os.path.join(data, name + ".csv"), d[name])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", data)


if __name__ == "__main__":
    main()
