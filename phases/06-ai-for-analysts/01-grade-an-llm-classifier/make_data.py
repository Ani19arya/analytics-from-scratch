"""Build data/tickets.csv: synthetic support tickets with a human label and an LLM label.

The LLM labels are a saved fixture. No API is called. Run: python3 make_data.py
"""
import csv
import os
import random

random.seed(601)

LABELS = ["billing", "bug", "refund", "other"]

TEXTS = {
    "billing": [
        "I was charged twice this month",
        "Please update the card on my account",
        "Why did my invoice go up",
        "I need a copy of last month's invoice",
    ],
    "bug": [
        "The export button does nothing",
        "App crashes when I open settings",
        "Dashboard shows a blank page",
        "Login loops back to the start",
    ],
    "refund": [
        "I want my money back for this order",
        "Please refund the annual plan I bought by mistake",
        "Cancel and refund my last payment",
        "The product never arrived, I want a refund",
    ],
    "other": [
        "Do you have a student discount",
        "How do I invite a teammate",
        "Can I change my username",
        "Where is your office located",
    ],
}

# How the (simulated) LLM mislabels each true class.
CONFUSION = {
    "billing": {"billing": 0.86, "refund": 0.10, "bug": 0.00, "other": 0.04},
    "bug": {"billing": 0.00, "refund": 0.00, "bug": 0.93, "other": 0.07},
    "refund": {"billing": 0.13, "refund": 0.84, "bug": 0.00, "other": 0.03},
    "other": {"billing": 0.06, "refund": 0.02, "bug": 0.08, "other": 0.84},
}
CLASS_MIX = {"billing": 0.30, "bug": 0.30, "refund": 0.20, "other": 0.20}


def pick(weights):
    r = random.random()
    total = 0.0
    for key in LABELS:
        total += weights[key]
        if r < total:
            return key
    return LABELS[-1]


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(here, "data"), exist_ok=True)
    path = os.path.join(here, "data", "tickets.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticket_id", "text", "human_label", "llm_label"])
        for i in range(1, 401):
            human = pick(CLASS_MIX)
            llm = pick(CONFUSION[human])
            w.writerow(["T%04d" % i, random.choice(TEXTS[human]), human, llm])
    print("wrote", path)


if __name__ == "__main__":
    main()
