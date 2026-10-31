"""Build the judge data: graded answers and pairwise comparisons. All SIMULATED.

No model was called and no person graded anything. The files stand in for:

- data/answers.csv: 300 draft replies from a support assistant. Two people (rater A and
  rater B) and an LLM judge each marked every reply pass or fail. Each reply also has
  its length in words.
- data/pairs.csv: 150 pairs of replies to the same question. The judge saw each pair
  twice, once in each order, and named the better one each time. A person also chose.

How the simulation works: every reply has a hidden true quality (good or bad). Each
person reads it right most of the time. The judge is fairly good, with two planted
habits that real LLM judges are known to show: it lets long bad replies pass more
often than short bad ones (length bias), and in a pair it leans towards whichever reply
it sees first (position bias). data/fixture.json records the numbers.

Run: python3 make_data.py
"""
import csv
import json
import os
import random

DEFAULT_SEED = 609
TOPICS = ["late order", "missing item", "refund status", "wrong address", "cold food", "promo code"]

P_GOOD = 0.6               # share of replies that are truly good
HUMAN_ERROR = 0.07         # chance a person marks a reply the wrong way
JUDGE_PASS_GOOD = 0.92     # judge passes a good reply
JUDGE_PASS_BAD_SHORT = 0.10  # judge passes a bad reply under 120 words
JUDGE_PASS_BAD_LONG = 0.45   # judge passes a bad reply of 120 words or more
LONG = 120
PAIR_RIGHT = 0.80          # judge picks the truly better reply when order has no effect
FIRST_PULL = 0.15          # extra chance the first-shown reply wins (position bias)
PAIR_HUMAN_RIGHT = 0.90


def flip(mark, rng, error):
    if rng.random() < error:
        return "fail" if mark == "pass" else "pass"
    return mark


def build(seed=DEFAULT_SEED, n_answers=300, n_pairs=150):
    """Return {"answers": [...], "pairs": [...]} for this seed. Nothing is written."""
    rng = random.Random(seed)
    answers = []
    for i in range(1, n_answers + 1):
        good = rng.random() < P_GOOD
        words = int(rng.triangular(30, 260, 90))
        truth = "pass" if good else "fail"
        if good:
            judge_pass = rng.random() < JUDGE_PASS_GOOD
        else:
            judge_pass = rng.random() < (JUDGE_PASS_BAD_LONG if words >= LONG else JUDGE_PASS_BAD_SHORT)
        answers.append({
            "answer_id": "A%03d" % i,
            "topic": rng.choice(TOPICS),
            "words": words,
            "rater_a": flip(truth, rng, HUMAN_ERROR),
            "rater_b": flip(truth, rng, HUMAN_ERROR),
            "judge": "pass" if judge_pass else "fail",
        })
    pairs = []
    for i in range(1, n_pairs + 1):
        better = rng.choice(["x", "y"])
        winners = []
        for first in ["x", "y"]:
            # chance the judge names the first-shown reply
            if first == better:
                p_first = min(1.0, PAIR_RIGHT + FIRST_PULL)
            else:
                p_first = (1 - PAIR_RIGHT) + FIRST_PULL
            second = "y" if first == "x" else "x"
            winners.append(first if rng.random() < p_first else second)
        human = better if rng.random() < PAIR_HUMAN_RIGHT else ("y" if better == "x" else "x")
        pairs.append({
            "pair_id": "P%03d" % i,
            "judge_x_first": winners[0],
            "judge_y_first": winners[1],
            "human": human,
        })
    return {"answers": answers, "pairs": pairs}


FIXTURE_INFO = {
    "files": ["answers.csv", "pairs.csv"],
    "source": "simulated",
    "model": "none: no model was called",
    "judge_prompt": "You are grading a support reply. Answer pass if it answers the customer's question correctly "
                    "and politely, otherwise fail. Reply with one word.",
    "pair_prompt": "Here are two replies to the same customer message, Reply 1 and Reply 2. Which is better? "
                   "Answer 1 or 2.",
    "temperature": "not applicable",
    "date": "not applicable",
    "human_raters": "simulated: two raters, each wrong on 7% of replies, independently",
    "planted_biases": {
        "length": "a bad reply of 120 words or more passes 45% of the time, a shorter bad reply 10%",
        "position": "in a pair, the reply shown first gets 15 extra points of chance to win",
    },
    "seed": DEFAULT_SEED,
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data")
    os.makedirs(data, exist_ok=True)
    built = build()
    with open(os.path.join(data, "answers.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["answer_id", "topic", "words", "rater_a", "rater_b", "judge"])
        w.writeheader()
        w.writerows(built["answers"])
    with open(os.path.join(data, "pairs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pair_id", "judge_x_first", "judge_y_first", "human"])
        w.writeheader()
        w.writerows(built["pairs"])
    with open(os.path.join(data, "fixture.json"), "w") as f:
        json.dump(FIXTURE_INFO, f, indent=2)
        f.write("\n")
    print("wrote", data)


if __name__ == "__main__":
    main()
