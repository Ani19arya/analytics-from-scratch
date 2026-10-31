"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are worked out here a second way: the tokenizer is rebuilt as a
character-by-character scan instead of a regex, and the costs and chances are
recomputed from the formulas. The functions also run on a second dataset built
in memory from another seed.
"""
import csv
import importlib.util
import json
import math
import os
import random
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 1604
TINY_VOCAB = {"the", "order", "was", "late"}


def committed(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def ref_tokens(text, vocab):
    """Scan characters: letters build a word, digits and other non-space characters stand alone."""
    out, word = [], ""

    def flush(w):
        if not w:
            return
        if w.lower() in vocab:
            out.append(w)
        else:
            i = 0
            while i < len(w):
                out.append(w[i:i + 4])
                i += 4

    for ch in text:
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            word += ch
            continue
        flush(word)
        word = ""
        if not ch.isspace():
            out.append(ch)
    flush(word)
    return out


def ref_batch(rows, vocab):
    inst = len(ref_tokens(make_data.INSTRUCTIONS, vocab))
    return (sum(inst + len(ref_tokens(r["text"], vocab)) for r in rows),
            sum(len(ref_tokens(r["summary"], vocab)) for r in rows))


def ref_softmax(logits, t):
    exps = {k: math.exp(z / t) for k, z in logits.items()}
    s = sum(exps.values())
    return {k: v / s for k, v in exps.items()}


def ref_run_many(logits, t, runs, seed):
    probs = ref_softmax(logits, t)
    keys = sorted(probs)
    rng = random.Random(seed)
    counts = dict.fromkeys(keys, 0)
    for _ in range(runs):
        r, acc, pick = rng.random(), 0.0, None
        for k in keys:
            acc += probs[k]
            pick = k
            if r < acc:
                break
        counts[pick] += 1
    return counts


RATE = {"input_per_million": 5.0, "output_per_million": 20.0}


class TestTokenizer(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(lesson.toy_tokenize("", TINY_VOCAB), [], "an empty text has no tokens")
        self.assertEqual(lesson.count_tokens("   ", TINY_VOCAB), 0, "spaces are not tokens")

    def test_known_words_are_one_token(self):
        self.assertEqual(lesson.toy_tokenize("The order was LATE", TINY_VOCAB), ["The", "order", "was", "LATE"],
                         "a word in the vocabulary is one token, in any case, and keeps its spelling")

    def test_unknown_word_is_cut_into_fours(self):
        self.assertEqual(lesson.toy_tokenize("Tiffinbell", TINY_VOCAB), ["Tiff", "inbe", "ll"],
                         "a word that is not in the vocabulary is cut into pieces of 4 letters")

    def test_digits_and_punctuation(self):
        self.assertEqual(lesson.toy_tokenize("Rs 2,499!", TINY_VOCAB), ["Rs", "2", ",", "4", "9", "9", "!"],
                         "each digit and each punctuation mark is its own token")

    def test_matches_reference_on_committed_reviews(self):
        vocab = {r["word"] for r in committed("vocab.csv")}
        for r in committed("reviews.csv")[:60]:
            self.assertEqual(lesson.toy_tokenize(r["text"], vocab), ref_tokens(r["text"], vocab),
                             "tokens differ for %s: compare with the rules in the docstring" % r["review_id"])


class TestCost(unittest.TestCase):
    def test_zero_tokens_cost_nothing(self):
        self.assertEqual(lesson.cost(0, 0, RATE), 0.0)

    def test_output_is_priced_separately(self):
        self.assertAlmostEqual(lesson.cost(1_000_000, 0, RATE), 5.0)
        self.assertAlmostEqual(lesson.cost(0, 1_000_000, RATE), 20.0,
                               msg="output tokens use output_per_million, not the input price")
        self.assertAlmostEqual(lesson.cost(2000, 500, RATE), (2000 * 5 + 500 * 20) / 1e6)

    def test_empty_batch(self):
        self.assertEqual(lesson.batch_tokens([], make_data.INSTRUCTIONS, TINY_VOCAB), (0, 0))
        self.assertEqual(lesson.monthly_estimate([], make_data.INSTRUCTIONS, TINY_VOCAB, RATE, 1000), 0.0,
                         "no sample rows means no estimate: return 0.0, do not divide by zero")

    def test_instructions_are_paid_per_request(self):
        rows = [{"text": "late", "summary": "late"}, {"text": "late", "summary": "late"}]
        inst = len(ref_tokens(make_data.INSTRUCTIONS, TINY_VOCAB))
        self.assertEqual(lesson.batch_tokens(rows, make_data.INSTRUCTIONS, TINY_VOCAB), (2 * (inst + 1), 2),
                         "every request sends the instructions again, so count them once per row")

    def test_committed_batch(self):
        vocab = {r["word"] for r in committed("vocab.csv")}
        rows = committed("reviews.csv")
        exp_in, exp_out = ref_batch(rows, vocab)
        self.assertEqual(lesson.batch_tokens(rows, make_data.INSTRUCTIONS, vocab), (exp_in, exp_out))
        rates = {r["model"]: r for r in committed("rate_card.csv")}
        large = {"input_per_million": float(rates["example-large"]["input_per_million"]),
                 "output_per_million": float(rates["example-large"]["output_per_million"])}
        expected = (exp_in * large["input_per_million"] + exp_out * large["output_per_million"]) / 1e6 / len(rows) * 60000
        got = lesson.monthly_estimate(rows, make_data.INSTRUCTIONS, vocab, large, 60000)
        self.assertAlmostEqual(got, expected, places=6)
        input_only = exp_in * large["input_per_million"] / 1e6 / len(rows) * 60000
        self.assertGreater(got, 2 * input_only, "the output tokens are most of the bill here: did you leave them out?")

    def test_second_dataset(self):
        d = make_data.build(seed=OTHER_SEED)
        vocab = set(d["vocab"])
        exp_in, exp_out = ref_batch(d["reviews"], vocab)
        self.assertEqual(lesson.batch_tokens(d["reviews"], make_data.INSTRUCTIONS, vocab), (exp_in, exp_out),
                         "seed %d: token totals differ from an independent count" % OTHER_SEED)
        expected = (exp_in * 0.5 + exp_out * 2.0) / 1e6 / len(d["reviews"]) * 12345
        rate = {"input_per_million": 0.5, "output_per_million": 2.0}
        self.assertAlmostEqual(lesson.monthly_estimate(d["reviews"], make_data.INSTRUCTIONS, vocab, rate, 12345),
                               expected, places=9)


class TestTemperature(unittest.TestCase):
    LOGITS = {"delivered": 2.2, "late": 1.4, "cold": 0.8, "cancelled": 0.3, "wonderful": -1.0}

    def test_softmax_formula(self):
        for t in (0.5, 1.0, 2.0):
            got = lesson.softmax(self.LOGITS, t)
            exp = ref_softmax(self.LOGITS, t)
            self.assertAlmostEqual(sum(got.values()), 1.0, msg="chances must add up to 1")
            for k in exp:
                self.assertAlmostEqual(got[k], exp[k], places=12, msg="T=%s, token %s: check exp(z / T) / sum" % (t, k))

    def test_big_scores_do_not_overflow(self):
        got = lesson.softmax({"a": 1000.0, "b": 999.0}, 1.0)
        self.assertAlmostEqual(got["a"], 1 / (1 + math.exp(-1)), msg="subtract the largest score before exp")

    def test_zero_temperature_and_ties(self):
        self.assertEqual(lesson.softmax(self.LOGITS, 0)["delivered"], 1.0)
        self.assertEqual(lesson.softmax({"b": 1.0, "a": 1.0}, 0), {"a": 1.0, "b": 0.0},
                         "at T = 0 a tie goes to the first token in sorted order")
        self.assertEqual(lesson.softmax({}, 1.0), {})
        with self.assertRaises(ValueError):
            lesson.softmax(self.LOGITS, -1)

    def test_temperature_spreads_the_chances(self):
        low = lesson.softmax(self.LOGITS, 0.5)["delivered"]
        high = lesson.softmax(self.LOGITS, 2.0)["delivered"]
        self.assertGreater(low, high, "a higher temperature must make the top token less likely")

    def test_runs_match_reference(self):
        for t, seed in ((0.5, 1), (1.0, 7), (2.0, 99)):
            self.assertEqual(lesson.run_many(self.LOGITS, t, 50, seed), ref_run_many(self.LOGITS, t, 50, seed),
                             "T=%s seed %d: use one random.Random(seed) and walk tokens in sorted order" % (t, seed))

    def test_zero_temperature_never_varies(self):
        counts = lesson.run_many(self.LOGITS, 0, 30, seed=5)
        self.assertEqual(counts["delivered"], 30)
        self.assertEqual(sum(counts.values()), 30)

    def test_committed_and_second_logits(self):
        for rows in (committed("next_token.csv"), make_data.build(seed=OTHER_SEED)["next_token"]):
            logits = {r["token"]: float(r["logit"]) for r in rows if r["context"] == "Overall the customer is"}
            self.assertEqual(lesson.run_many(logits, 1.0, 40, 3), ref_run_many(logits, 1.0, 40, 3))
            answers = lesson.run_many(logits, 1.0, 40, 3)
            self.assertGreater(sum(1 for v in answers.values() if v), 1,
                               "at T = 1 the same prompt should give more than one answer")


class TestFixture(unittest.TestCase):
    def test_labelled_as_simulated_and_fictional(self):
        with open(os.path.join(HERE, "data", "fixture.json")) as f:
            info = json.load(f)
        self.assertEqual(info["summary_source"], "simulated")
        self.assertTrue(info["model"].startswith("none"))
        for r in committed("rate_card.csv"):
            self.assertIn("fictional", r["note"])


if __name__ == "__main__":
    unittest.main()
