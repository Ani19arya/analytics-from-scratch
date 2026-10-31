"""Exercise: count tokens with a toy tokenizer, cost a batch from a fictional rate card,
and see why temperature makes the same prompt give different answers.

Fill in the functions marked TODO. Then run: python3 test_lesson.py
"""
import csv
import math
import os
import random
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

INSTRUCTIONS = ("Summarise this customer review in one sentence. Say if the customer is happy "
                "or unhappy, and name the main problem if there is one.")

# A word, one digit, or one other character that is not a space.
PIECE = re.compile(r"[A-Za-z]+|\d|[^\sA-Za-z\d]")
CHUNK = 4


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def load_vocab():
    return {r["word"] for r in load_csv("vocab.csv")}


def load_rates():
    return {r["model"]: {"input_per_million": float(r["input_per_million"]),
                         "output_per_million": float(r["output_per_million"])}
            for r in load_csv("rate_card.csv")}


def load_logits(context):
    return {r["token"]: float(r["logit"]) for r in load_csv("next_token.csv") if r["context"] == context}


def toy_tokenize(text, vocab):
    """Return the list of tokens.

    Use PIECE.findall(text) to get words, digits and punctuation marks.
    - A word whose lower case form is in vocab is one token (keep the word as written).
    - Any other word is cut into pieces of CHUNK letters: "Tiffinbell" -> ["Tiff", "inbe", "ll"].
    - Each digit and each punctuation mark is one token.
    """
    # TODO
    raise NotImplementedError


def count_tokens(text, vocab):
    # TODO
    raise NotImplementedError


def batch_tokens(rows, instructions, vocab):
    """Return (input tokens, output tokens) for the whole batch.

    Every request sends the instructions AND the review text, so count the instructions
    once per row. Output tokens are the tokens of each row's "summary".
    """
    # TODO
    raise NotImplementedError


def cost(input_tokens, output_tokens, rate):
    """Dollars. rate has "input_per_million" and "output_per_million"."""
    # TODO
    raise NotImplementedError


def monthly_estimate(rows, instructions, vocab, rate, requests_per_month):
    """Average cost per request in the sample, times requests_per_month. 0.0 for no rows."""
    # TODO
    raise NotImplementedError


def softmax(logits, temperature):
    """Return {token: chance}, with tokens in sorted order.

    p = exp(z / T) / sum of exp(z / T). Subtract the largest z first so exp never overflows.
    T == 0: chance 1.0 for the highest score (ties: the first in sorted order), 0.0 for the rest.
    T < 0: raise ValueError. No tokens: return {}.
    """
    # TODO
    raise NotImplementedError


def sample_next(probs, rng):
    """One draw. r = rng.random(). Walk the tokens in sorted order, skipping chances of 0,
    add up the chances, and return the first token where r < running total.
    If rounding leaves r above the total, return the last token you added."""
    # TODO
    raise NotImplementedError


def run_many(logits, temperature, runs, seed):
    """Make ONE random.Random(seed), then call sample_next `runs` times.
    Return {token: how many times it was picked} with every token as a key."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    vocab = load_vocab()
    print(toy_tokenize("Tiffinbell delivered 2 thalis!", vocab))
    rows = load_csv("reviews.csv")
    print(batch_tokens(rows, INSTRUCTIONS, vocab))
    print(run_many(load_logits("Your order was"), 1.0, 20, seed=1))
