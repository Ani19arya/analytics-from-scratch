"""Solution: how many labelled tickets an eval needs, for one score and for a comparison."""
import csv
import math
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
Z95 = 1.96      # two-sided 95%
Z_POWER80 = 0.8416  # one-sided z for 80% power


def load_rows(path=os.path.join(DATA, "labelled_tickets.csv")):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def right(row, version):
    return row[version + "_label"] == row["gold_label"]


def wilson_interval(k, n, z=Z95):
    """95% Wilson score interval for k successes out of n. (0.0, 1.0) when n is 0."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def margin(k, n, z=Z95):
    """Half the width of the Wilson interval: the 'plus or minus' you can quote."""
    low, high = wilson_interval(k, n, z)
    return (high - low) / 2


def n_for_margin(p, target, z=Z95):
    """Smallest n whose Wilson half-width, at an expected rate p, is at most target."""
    if not 0 < target < 0.5:
        raise ValueError("target margin must be between 0 and 0.5")

    def half(n):
        return margin(p * n, n, z)

    high = 1
    while half(high) > target:
        high *= 2
    low = high // 2
    while high - low > 1:
        mid = (low + high) // 2
        if half(mid) > target:
            low = mid
        else:
            high = mid
    return high


def paired_table(rows, a="v2", b="v3"):
    """(both right, only a right, only b right, both wrong) over the same tickets."""
    both = only_a = only_b = neither = 0
    for r in rows:
        ra, rb = right(r, a), right(r, b)
        if ra and rb:
            both += 1
        elif ra:
            only_a += 1
        elif rb:
            only_b += 1
        else:
            neither += 1
    return both, only_a, only_b, neither


def paired_difference_interval(only_a, only_b, n, z=Z95):
    """95% interval for accuracy(b) - accuracy(a) on n paired tickets.

    diff = (only_b - only_a) / n, se = sqrt(only_a + only_b - (only_b - only_a)^2 / n) / n.
    With n = 0 there is no evidence: (-1.0, 1.0).
    """
    if n == 0:
        return -1.0, 1.0
    diff = (only_b - only_a) / n
    se = math.sqrt(max(only_a + only_b - (only_b - only_a) ** 2 / n, 0.0)) / n
    return diff - z * se, diff + z * se


def verdict(rows, a="v2", b="v3"):
    """'b better', 'a better' or 'not proven', from whether the paired interval excludes 0."""
    _, only_a, only_b, _ = paired_table(rows, a, b)
    low, high = paired_difference_interval(only_a, only_b, len(rows))
    if low > 0:
        return b + " better"
    if high < 0:
        return a + " better"
    return "not proven"


def n_for_paired_difference(delta, discordant, z_alpha=Z95, z_beta=Z_POWER80):
    """Tickets needed to detect a true gain delta with 80% power, both versions on the same tickets.

    discordant is the expected share of tickets where exactly one version is right.
    n = (z_alpha * sqrt(discordant) + z_beta * sqrt(discordant - delta^2))^2 / delta^2
    """
    if delta <= 0 or discordant < delta:
        raise ValueError("need 0 < delta <= discordant share")
    top = z_alpha * math.sqrt(discordant) + z_beta * math.sqrt(discordant - delta * delta)
    return math.ceil(top * top / (delta * delta))


def n_for_unpaired_difference(p1, p2, z_alpha=Z95, z_beta=Z_POWER80):
    """Tickets needed PER VERSION if each version is graded on its own separate tickets."""
    if p1 == p2:
        raise ValueError("p1 and p2 must differ")
    var = p1 * (1 - p1) + p2 * (1 - p2)
    return math.ceil((z_alpha + z_beta) ** 2 * var / (p1 - p2) ** 2)


def main():
    rows = load_rows()
    print("first n   v2 acc  v3 acc   v3 margin   paired 95% interval for v3 - v2")
    for n in [50, 100, 200, 400, 800, 1600]:
        part = rows[:n]
        k2 = sum(right(r, "v2") for r in part)
        k3 = sum(right(r, "v3") for r in part)
        _, oa, ob, _ = paired_table(part)
        low, high = paired_difference_interval(oa, ob, n)
        print("%7d   %.3f   %.3f    +/- %.3f   %+.3f to %+.3f  %s" % (
            n, k2 / n, k3 / n, margin(k3, n), low, high, verdict(part)))
    print("n for +/- 0.02 at 0.87:", n_for_margin(0.87, 0.02))
    print("n for a 2-point gain, paired, 12% discordant:", n_for_paired_difference(0.02, 0.12))
    print("n per version for 0.86 vs 0.88, unpaired:", n_for_unpaired_difference(0.86, 0.88))


if __name__ == "__main__":
    main()
