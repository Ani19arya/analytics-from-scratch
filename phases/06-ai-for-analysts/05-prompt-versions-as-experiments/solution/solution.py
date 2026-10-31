"""Solution: compare two prompt versions on the same tickets with a paired, exact test."""
import csv
import math
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
ALPHA = 0.05


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def pair_runs(gold_rows, run_a, run_b):
    """Join the gold labels and two runs on ticket_id: [{"ticket_id", "gold", "a", "b"}].

    Refuse (ValueError) when an id is repeated, or when the three files do not hold exactly
    the same tickets. A comparison on different tickets is not a comparison of prompts."""
    tables = {}
    for name, rows, col in (("gold", gold_rows, "gold_label"), ("run a", run_a, "label"), ("run b", run_b, "label")):
        table = {}
        for r in rows:
            if r["ticket_id"] in table:
                raise ValueError("%s has ticket %s twice" % (name, r["ticket_id"]))
            table[r["ticket_id"]] = r[col]
        tables[name] = table
    ids = set(tables["gold"])
    for name in ("run a", "run b"):
        if set(tables[name]) != ids:
            missing = sorted(ids - set(tables[name]))[:3]
            extra = sorted(set(tables[name]) - ids)[:3]
            raise ValueError("%s is not on the same tickets: missing %s, extra %s" % (name, missing, extra))
    return [{"ticket_id": t, "gold": tables["gold"][t], "a": tables["run a"][t], "b": tables["run b"][t]}
            for t in sorted(ids)]


def accuracy(pairs, key):
    """Share of tickets where pairs[i][key] equals the gold label. 0.0 for no tickets."""
    if not pairs:
        return 0.0
    return sum(1 for p in pairs if p[key] == p["gold"]) / len(pairs)


def paired_table(pairs):
    """(both right, only a right, only b right, both wrong)."""
    both = a_only = b_only = neither = 0
    for p in pairs:
        a_ok, b_ok = p["a"] == p["gold"], p["b"] == p["gold"]
        if a_ok and b_ok:
            both += 1
        elif a_ok:
            a_only += 1
        elif b_ok:
            b_only += 1
        else:
            neither += 1
    return both, a_only, b_only, neither


def exact_two_sided_p(k, n):
    """Two-sided exact binomial p-value for k out of n when the true chance is one half.

    p = 2 x P(X <= min(k, n - k)), capped at 1. With n = 0 there is no evidence: 1.0."""
    if n == 0:
        return 1.0
    low = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(low + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def compare(pairs, alpha=ALPHA):
    """The paired comparison: accuracies, the discordant counts, the exact p-value, and a verdict."""
    _, a_only, b_only, _ = paired_table(pairs)
    p = exact_two_sided_p(b_only, a_only + b_only)
    if p < alpha and b_only > a_only:
        verdict = "v2 better"
    elif p < alpha and a_only > b_only:
        verdict = "v1 better"
    else:
        verdict = "no clear difference"
    return {"n": len(pairs), "acc_a": accuracy(pairs, "a"), "acc_b": accuracy(pairs, "b"),
            "a_only": a_only, "b_only": b_only, "p_value": p, "verdict": verdict}


def main():
    pairs = pair_runs(load_csv("tickets.csv"), load_csv("run_v1.csv"), load_csv("run_v2.csv"))
    both, a_only, b_only, neither = paired_table(pairs)
    print("tickets", len(pairs))
    print("                 v2 right  v2 wrong")
    print("v1 right         %8d  %8d" % (both, a_only))
    print("v1 wrong         %8d  %8d" % (b_only, neither))
    r = compare(pairs)
    print("accuracy v1 %.3f, v2 %.3f, difference %+.1f points" % (r["acc_a"], r["acc_b"], 100 * (r["acc_b"] - r["acc_a"])))
    print("discordant: v1 only %d, v2 only %d, exact p = %.4f" % (r["a_only"], r["b_only"], r["p_value"]))
    print("verdict:", r["verdict"])


if __name__ == "__main__":
    main()
