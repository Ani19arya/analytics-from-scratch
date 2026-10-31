"""Solution: count tokens with a toy tokenizer, cost a batch from a fictional rate card,
and see why temperature makes the same prompt give different answers."""
import csv
import math
import os
import random
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    """Words in the vocabulary are one token. Other words are cut into pieces of 4 letters.
    Each digit and each punctuation mark is one token. Spaces are not tokens."""
    tokens = []
    for piece in PIECE.findall(text):
        if piece.isalpha() and piece.lower() not in vocab:
            tokens.extend(piece[i:i + CHUNK] for i in range(0, len(piece), CHUNK))
        else:
            tokens.append(piece)
    return tokens


def count_tokens(text, vocab):
    return len(toy_tokenize(text, vocab))


def batch_tokens(rows, instructions, vocab):
    """(input tokens, output tokens) for the whole batch.

    Every request sends the instructions AND the review, so the instructions are paid for once
    per request. The output is the summary the model writes back."""
    inst = count_tokens(instructions, vocab)
    input_tokens = sum(inst + count_tokens(r["text"], vocab) for r in rows)
    output_tokens = sum(count_tokens(r["summary"], vocab) for r in rows)
    return input_tokens, output_tokens


def cost(input_tokens, output_tokens, rate):
    """Dollars, with prices per million tokens. Input and output have different prices."""
    return (input_tokens * rate["input_per_million"] + output_tokens * rate["output_per_million"]) / 1_000_000


def monthly_estimate(rows, instructions, vocab, rate, requests_per_month):
    """Average cost per request in the sample, times the requests expected in a month."""
    if not rows:
        return 0.0
    input_tokens, output_tokens = batch_tokens(rows, instructions, vocab)
    return cost(input_tokens, output_tokens, rate) / len(rows) * requests_per_month


def softmax(logits, temperature):
    """Turn scores into chances: p = exp(z / T) / sum of exp(z / T).

    T = 0 means always pick the highest score (ties go to the first token in sorted order)."""
    if temperature < 0:
        raise ValueError("temperature cannot be negative")
    tokens = sorted(logits)
    if not tokens:
        return {}
    if temperature == 0:
        best = max(tokens, key=lambda t: logits[t])
        return {t: 1.0 if t == best else 0.0 for t in tokens}
    top = max(logits.values())
    weights = {t: math.exp((logits[t] - top) / temperature) for t in tokens}
    total = sum(weights.values())
    return {t: weights[t] / total for t in tokens}


def sample_next(probs, rng):
    """One draw: walk the tokens in sorted order and stop where the running total passes r."""
    r = rng.random()
    running = 0.0
    last = None
    for t in sorted(probs):
        if probs[t] <= 0:
            continue
        running += probs[t]
        last = t
        if r < running:
            return t
    return last


def run_many(logits, temperature, runs, seed):
    """Ask the same question `runs` times and count the answers. One generator for all runs."""
    rng = random.Random(seed)
    probs = softmax(logits, temperature)
    counts = {t: 0 for t in sorted(logits)}
    for _ in range(runs):
        counts[sample_next(probs, rng)] += 1
    return counts


def main():
    vocab = load_vocab()
    rows = load_csv("reviews.csv")
    rates = load_rates()
    inp, out = batch_tokens(rows, INSTRUCTIONS, vocab)
    print("reviews %d, input tokens %d, output tokens %d" % (len(rows), inp, out))
    for model, rate in rates.items():
        print("%-13s this batch $%.4f, 60,000 reviews a month $%.2f" % (
            model, cost(inp, out, rate), monthly_estimate(rows, INSTRUCTIONS, vocab, rate, 60000)))
    logits = load_logits("Your order was")
    for t in (0, 0.5, 1.0, 2.0):
        print("T=%.1f" % t, run_many(logits, t, 20, seed=1))


if __name__ == "__main__":
    main()
