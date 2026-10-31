"""Solution: measure whether an LLM judge agrees with people, and find its biases."""
import csv
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LONG = 120  # replies of this many words or more count as long


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        if "words" in r:
            r["words"] = int(r["words"])
    return rows


def cohen_kappa(a, b):
    """Return (observed agreement, chance agreement, kappa) for two equal-length lists of labels.

    observed = share of items where a and b give the same label.
    chance   = sum over labels of (share of a with that label) x (share of b with that label).
    kappa    = (observed - chance) / (1 - chance).
    kappa is None when chance is 1 (both raters always used one and the same label).
    Raise ValueError if the lists differ in length or are empty.
    """
    if len(a) != len(b) or not a:
        raise ValueError("need two non-empty lists of the same length")
    n = len(a)
    observed = sum(1 for x, y in zip(a, b) if x == y) / n
    labels = set(a) | set(b)
    chance = sum((a.count(k) / n) * (b.count(k) / n) for k in labels)
    if chance == 1:
        return observed, chance, None
    return observed, chance, (observed - chance) / (1 - chance)


def kappas(rows):
    """Kappa for every pair of graders: A with B, judge with A, judge with B."""
    col = {k: [r[k] for r in rows] for k in ["rater_a", "rater_b", "judge"]}
    return {
        "a_vs_b": cohen_kappa(col["rater_a"], col["rater_b"])[2],
        "judge_vs_a": cohen_kappa(col["judge"], col["rater_a"])[2],
        "judge_vs_b": cohen_kappa(col["judge"], col["rater_b"])[2],
    }


def false_pass_by_length(rows, long_words=LONG):
    """Among replies BOTH people failed, how often the judge passed them, split by length.

    Return {"short": (judge passes, replies), "long": (judge passes, replies)}.
    Long means words >= long_words.
    """
    out = {"short": [0, 0], "long": [0, 0]}
    for r in rows:
        if r["rater_a"] == "fail" and r["rater_b"] == "fail":
            key = "long" if r["words"] >= long_words else "short"
            out[key][1] += 1
            out[key][0] += r["judge"] == "pass"
    return {k: tuple(v) for k, v in out.items()}


def position_stats(pairs):
    """How the judge's choice depends on order.

    Each pair was judged twice: judge_x_first (x shown first) and judge_y_first (y shown first),
    each naming the winner, "x" or "y". Return a dict:
    pairs: number of pairs; consistent: pairs where the same reply won in both orders;
    first_wins: verdicts (out of 2 per pair) where the reply shown first won.
    """
    consistent = sum(1 for p in pairs if p["judge_x_first"] == p["judge_y_first"])
    first_wins = sum(1 for p in pairs if p["judge_x_first"] == "x") + sum(1 for p in pairs if p["judge_y_first"] == "y")
    return {"pairs": len(pairs), "consistent": consistent, "first_wins": first_wins}


def swap_verdicts(pairs):
    """One verdict per pair that does not depend on order: the winner if both orders agree, else 'tie'."""
    return [p["judge_x_first"] if p["judge_x_first"] == p["judge_y_first"] else "tie" for p in pairs]


def agreement_with_human(pairs, verdicts):
    """(agree, decided): among pairs whose verdict is not 'tie', how many match the person's choice."""
    decided = [(p, v) for p, v in zip(pairs, verdicts) if v != "tie"]
    agree = sum(1 for p, v in decided if v == p["human"])
    return agree, len(decided)


def main():
    rows = load_csv("answers.csv")
    pairs = load_csv("pairs.csv")
    for name, value in kappas(rows).items():
        print("kappa %-10s %.3f" % (name, value))
    print("judge passes replies both people failed:", false_pass_by_length(rows))
    print("position:", position_stats(pairs))
    first_only = [p["judge_x_first"] for p in pairs]
    print("x-first verdict agrees with the person:", agreement_with_human(pairs, first_only))
    print("both-orders verdict agrees with the person:", agreement_with_human(pairs, swap_verdicts(pairs)))


if __name__ == "__main__":
    main()
