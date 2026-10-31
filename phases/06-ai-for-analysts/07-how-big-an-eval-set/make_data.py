"""Build data/labelled_tickets.csv: 1,600 tickets with a gold label and SIMULATED labels from two prompts.

No model was called. Each ticket has a gold label from a person (simulated too) and a
label from prompt v2 and from prompt v3. The two prompts are mostly right on the same
tickets, as real prompt versions are: for every ticket one draw decides which of four
cells it falls in (both right, only v2 right, only v3 right, both wrong). A wrong label
is one of the other three labels, drawn at random.

The chances below are what the simulation is built from, so the lesson can say what the
true answer is. They are not a claim about any real model.

Run: python3 make_data.py
"""
import csv
import json
import os
import random

DEFAULT_SEED = 672
LABELS = ["billing", "bug", "refund", "other"]
MIX = [("billing", 0.30), ("bug", 0.25), ("refund", 0.20), ("other", 0.25)]
# (v2 right, v3 right): chance. True accuracy: v2 0.86, v3 0.88. Discordant share 0.12.
CELLS = [((True, True), 0.81), ((True, False), 0.05), ((False, True), 0.07), ((False, False), 0.07)]


def pick(options, rng):
    r = rng.random()
    total = 0.0
    for value, chance in options:
        total += chance
        if r < total:
            return value
    return options[-1][0]


def build(seed=DEFAULT_SEED, n=1600):
    """Return {"tickets": [...]} for this seed. Rows are in the order they were labelled."""
    rng = random.Random(seed)
    rows = []
    for i in range(1, n + 1):
        gold = pick(MIX, rng)
        v2_right, v3_right = pick(CELLS, rng)
        others = [x for x in LABELS if x != gold]
        v2 = gold if v2_right else rng.choice(others)
        v3 = gold if v3_right else rng.choice(others)
        rows.append({"ticket_id": "T%04d" % i, "gold_label": gold, "v2_label": v2, "v3_label": v3})
    return {"tickets": rows}


FIXTURE_INFO = {
    "file": "labelled_tickets.csv",
    "label_source": "simulated",
    "model": "none: no model was called",
    "prompt_versions": ["v2", "v3"],
    "temperature": "not applicable",
    "date": "not applicable",
    "how": "one seeded draw per ticket picks both right (0.81), only v2 right (0.05), only v3 right (0.07) "
           "or both wrong (0.07). A wrong label is a random other label.",
    "true_accuracy": {"v2": 0.86, "v3": 0.88},
    "gold_label_source": "simulated single human labeller, treated as the truth",
    "pilot": "the first 50 rows are the tickets Sam scored first",
    "seed": DEFAULT_SEED,
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    path = os.path.join(data, "labelled_tickets.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["ticket_id", "gold_label", "v2_label", "v3_label"])
        w.writeheader()
        w.writerows(build()["tickets"])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
