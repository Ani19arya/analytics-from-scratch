"""Lesson 13: A/B test pitfalls (sample ratio mismatch, multiple comparisons,
peeking). Worked solution. Uses only csv, math and random. Run from the lesson
folder:
    python3 solution/solution.py
"""
import csv
import math
import os
import random

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS = ("signups", "saves", "shares")


def read_daily(path):
    """One dict per row, every count as an int."""
    rows = []
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            rows.append({"day": int(row["day"]), "variant": row["variant"],
                         "users": int(row["users"]), "signups": int(row["signups"]),
                         "saves": int(row["saves"]), "shares": int(row["shares"])})
    return rows


def totals(rows, last_day=None):
    """{variant: {"users", "signups", "saves", "shares"}} summed over days 1..last_day
    (all days when last_day is None)."""
    out = {}
    for row in rows:
        if last_day is not None and row["day"] > last_day:
            continue
        cell = out.setdefault(row["variant"], {"users": 0, "signups": 0, "saves": 0, "shares": 0})
        for key in cell:
            cell[key] += row[key]
    return out


def normal_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def two_proportion_p(c_a, n_a, c_b, n_b):
    """Two-sided p-value of the pooled two-proportion z-test."""
    if n_a <= 0 or n_b <= 0:
        raise ValueError("each group needs at least one user")
    pool = (c_a + c_b) / (n_a + n_b)
    if pool in (0.0, 1.0):
        return 1.0
    se = math.sqrt(pool * (1 - pool) * (1 / n_a + 1 / n_b))
    z = (c_b / n_b - c_a / n_a) / se
    return min(1.0, 2 * (1 - normal_cdf(abs(z))))


def chi2_sf(x, df):
    """P(chi-square with df degrees of freedom > x), for a whole number df >= 1."""
    if df < 1 or int(df) != df:
        raise ValueError("df must be a whole number, at least 1")
    if x <= 0:
        return 1.0
    half = x / 2
    if df % 2 == 0:
        term, total = 1.0, 1.0
        for j in range(1, df // 2):
            term *= half / j
            total += term
        return min(1.0, math.exp(-half) * total)
    total = 2 * (1 - normal_cdf(math.sqrt(x)))
    term = math.sqrt(2 * x / math.pi) * math.exp(-half)
    for j in range(1, (df - 1) // 2 + 1):
        total += term
        term *= x / (2 * j + 1)
    return min(1.0, total)


def srm_check(counts, weights=None):
    """Chi-square goodness of fit of the observed group sizes to the planned split.
    counts: {group: users}. weights: {group: planned share}, equal when None.
    Returns {"chi2", "df", "p_value"}."""
    groups = sorted(counts)
    if len(groups) < 2:
        raise ValueError("need at least two groups")
    total = sum(counts.values())
    if total == 0:
        raise ValueError("no users")
    if weights is None:
        weights = {g: 1 / len(groups) for g in groups}
    wsum = sum(weights[g] for g in groups)
    chi2 = 0.0
    for g in groups:
        expected = total * weights[g] / wsum
        chi2 += (counts[g] - expected) ** 2 / expected
    df = len(groups) - 1
    return {"chi2": chi2, "df": df, "p_value": chi2_sf(chi2, df)}


def srm_culprits(counts, threshold=0.001):
    """Groups whose own size, tested against all the others together (1 df,
    equal planned shares), has a p-value below threshold. Sorted."""
    out = []
    share = 1 / len(counts)
    total = sum(counts.values())
    for g in sorted(counts):
        test = srm_check({"this": counts[g], "rest": total - counts[g]},
                         {"this": share, "rest": 1 - share})
        if test["p_value"] < threshold:
            out.append(g)
    return out


def bonferroni(pvalues):
    m = len(pvalues)
    return [min(1.0, p * m) for p in pvalues]


def holm(pvalues):
    """Holm step-down adjusted p-values, in the input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return adjusted


def benjamini_hochberg(pvalues):
    """Benjamini-Hochberg adjusted p-values (false discovery rate), in the input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 1.0
    for rank in range(m - 1, -1, -1):
        i = order[rank]
        running = min(running, pvalues[i] * m / (rank + 1))
        adjusted[i] = min(1.0, running)
    return adjusted


def peeking_curve(rows, control, variant, metric):
    """[(day, p-value)] using every user up to and including that day."""
    curve = []
    for day in sorted({r["day"] for r in rows}):
        t = totals(rows, day)
        a, b = t[control], t[variant]
        curve.append((day, two_proportion_p(a[metric], a["users"], b[metric], b["users"])))
    return curve


def simulate_peeking(n_sims, n_days, users_per_day, rate, alpha=0.05, seed=0):
    """Simulate n_sims A/A tests (both groups have the same true rate). Each day
    each group gets users_per_day users. Return (share of tests that were below
    alpha on ANY day, share below alpha on the LAST day)."""
    if n_sims < 1 or n_days < 1 or users_per_day < 1:
        raise ValueError("n_sims, n_days and users_per_day must be at least 1")
    rng = random.Random(seed)
    any_day = final_day = 0
    for _ in range(n_sims):
        ca = cb = n = 0
        crossed = False
        p = 1.0
        for _ in range(n_days):
            n += users_per_day
            ca += sum(1 for _ in range(users_per_day) if rng.random() < rate)
            cb += sum(1 for _ in range(users_per_day) if rng.random() < rate)
            p = two_proportion_p(ca, n, cb, n)
            if p < alpha:
                crossed = True
        any_day += crossed
        final_day += p < alpha
    return any_day / n_sims, final_day / n_sims


def analyse(path, control="A", alpha=0.05):
    """The full read-out, in the order you should do it:
    1. SRM on all groups; drop the culprits (srm_culprits) and do not read them.
    2. Every kept challenger vs control on every metric (sorted by variant, then
       METRICS order): lift (rate difference, 5 decimals) and raw p.
    3. Holm and BH adjusted p over that whole family of tests.
    4. Wins: positive lift and p below alpha, as "B:signups" strings, for raw, Holm and BH."""
    rows = read_daily(path)
    t = totals(rows)
    counts = {g: t[g]["users"] for g in t}
    srm = srm_check(counts)
    dropped = srm_culprits(counts) if srm["p_value"] < 0.001 else []
    tests = []
    for v in sorted(t):
        if v == control or v in dropped:
            continue
        a, b = t[control], t[v]
        for metric in METRICS:
            lift = b[metric] / b["users"] - a[metric] / a["users"]
            p = two_proportion_p(a[metric], a["users"], b[metric], b["users"])
            tests.append({"variant": v, "metric": metric, "lift": round(lift, 5), "p": p})
    raw = [x["p"] for x in tests]
    for x, h, q in zip(tests, holm(raw), benjamini_hochberg(raw)):
        x["holm"] = h
        x["bh"] = q

    def wins(key):
        return [x["variant"] + ":" + x["metric"] for x in tests if x["lift"] > 0 and x[key] < alpha]

    return {"users": counts, "srm_p": srm["p_value"], "dropped": dropped, "tests": tests,
            "wins_raw": wins("p"), "wins_holm": wins("holm"), "wins_bh": wins("bh")}


if __name__ == "__main__":
    result = analyse(os.path.join(HERE, "data", "daily.csv"))
    print("users", result["users"])
    print("srm_p %.3g dropped %s" % (result["srm_p"], result["dropped"]))
    for x in result["tests"]:
        print("%s %-7s lift %+.4f  p %.4f  holm %.4f  bh %.4f" % (
            x["variant"], x["metric"], x["lift"], x["p"], x["holm"], x["bh"]))
    print("wins_raw ", result["wins_raw"])
    print("wins_holm", result["wins_holm"])
    print("wins_bh  ", result["wins_bh"])
