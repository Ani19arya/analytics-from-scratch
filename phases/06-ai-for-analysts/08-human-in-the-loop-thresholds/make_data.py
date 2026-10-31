"""Build data/tickets.csv: 1,200 labelled tickets with a SIMULATED LLM label and confidence.

No model was called. Each ticket has a gold label (a simulated person, treated as the
truth), the label the LLM gave, and the confidence the LLM reported, from 0.50 to 1.00
in steps of 0.01. Many tickets share the same confidence, as real reported scores do.

The simulation is overconfident on purpose, as models often are: a ticket with reported
confidence c is labelled right with chance 1 - 1.4 * (1 - c), capped at 0.99. So at a
reported 0.90 the label is right about 86% of the time, not 90%.

The first 600 tickets are the validation split (used to choose a threshold), the last
600 are the held-out split (used once, to report the result).

Run: python3 make_data.py
"""
import csv
import json
import os
import random

DEFAULT_SEED = 612
LABELS = ["billing", "bug", "refund", "other"]
MIX = [("billing", 0.30), ("bug", 0.25), ("refund", 0.20), ("other", 0.25)]
N_VALIDATION = 600
N_HELDOUT = 600


def pick(options, rng):
    r = rng.random()
    total = 0.0
    for value, chance in options:
        total += chance
        if r < total:
            return value
    return options[-1][0]


def chance_right(confidence):
    return min(0.99, 1 - 1.3 * (1 - confidence))


def build(seed=DEFAULT_SEED, n_validation=N_VALIDATION, n_heldout=N_HELDOUT):
    """Return {"tickets": [...]} for this seed. Nothing is written."""
    rng = random.Random(seed)
    rows = []
    for i in range(1, n_validation + n_heldout + 1):
        gold = pick(MIX, rng)
        # most reported scores sit near the top, as they do for real models
        confidence = round(0.5 + 0.5 * rng.betavariate(4.0, 1.0), 2)
        if rng.random() < chance_right(confidence):
            label = gold
        else:
            label = rng.choice([x for x in LABELS if x != gold])
        rows.append({
            "ticket_id": "T%04d" % i,
            "split": "validation" if i <= n_validation else "heldout",
            "gold_label": gold,
            "llm_label": label,
            "confidence": "%.2f" % confidence,
        })
    return {"tickets": rows}


FIXTURE_INFO = {
    "file": "tickets.csv",
    "label_source": "simulated",
    "model": "none: no model was called",
    "prompt_version": "none",
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "confidence = 0.5 + 0.5 * Beta(4, 1), rounded to 0.01. The label is right with chance "
           "min(0.99, 1 - 1.4 * (1 - confidence)), otherwise a random other label. Overconfident on purpose.",
    "splits": "T0001 to T0600 validation, T0601 to T1200 held-out",
    "gold_label_source": "simulated single human labeller, treated as the truth",
    "seed": DEFAULT_SEED,
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    path = os.path.join(data, "tickets.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticket_id", "split", "gold_label", "llm_label", "confidence"])
        w.writeheader()
        w.writerows(build()["tickets"])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
