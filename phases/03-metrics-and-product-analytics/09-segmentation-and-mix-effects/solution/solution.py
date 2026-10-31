"""Lesson 09: segmentation and mix effects. Worked answer.

Total rate R = sum over segments of w_s x r_s, where
w_s = segment sessions / all sessions (the mix) and r_s = segment orders / segment sessions.
The change R1 - R0 splits exactly into
  mix effect  = sum (w1_s - w0_s) x ((r0_s + r1_s) / 2 - (R0 + R1) / 2)
  rate effect = sum (r1_s - r0_s) x (w0_s + w1_s) / 2
Subtracting the average overall rate in the mix term changes no total (the share
changes add up to 0), but it makes each segment's mix effect readable: a segment
that grew and converts below average has a negative mix effect.
"""
import csv


def load_periods(path, split_date):
    """Return {"prior": {segment: [sessions, orders]}, "current": {...}}.
    Rows dated before split_date are prior, the rest current."""
    out = {"prior": {}, "current": {}}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            key = "prior" if row["date"] < split_date else "current"
            cell = out[key].setdefault(row["device"], [0, 0])
            cell[0] += int(row["sessions"])
            cell[1] += int(row["orders"])
    return out


def overall_rate(period):
    """Total orders / total sessions for one period, or None with no sessions."""
    sessions = sum(s for s, _ in period.values())
    orders = sum(o for _, o in period.values())
    return orders / sessions if sessions else None


def decompose(prior, current):
    """Split the change in the overall rate into a mix effect and a rate effect.
    Return {"total", "mix", "rate", "segments": {segment: {"w0", "w1", "r0", "r1", "mix", "rate"}}}
    or None if either period has no sessions.
    A segment with no sessions in one period borrows its rate from the other period,
    so all of its contribution is mix. A segment with no sessions in both is skipped."""
    r0_all, r1_all = overall_rate(prior), overall_rate(current)
    if r0_all is None or r1_all is None:
        return None
    n0 = sum(s for s, _ in prior.values())
    n1 = sum(s for s, _ in current.values())
    centre = (r0_all + r1_all) / 2
    result = {"total": r1_all - r0_all, "mix": 0.0, "rate": 0.0, "segments": {}}
    for seg in sorted(set(prior) | set(current)):
        s0, o0 = prior.get(seg, (0, 0))
        s1, o1 = current.get(seg, (0, 0))
        if s0 == 0 and s1 == 0:
            continue
        r0 = o0 / s0 if s0 else o1 / s1
        r1 = o1 / s1 if s1 else r0
        w0, w1 = s0 / n0, s1 / n1
        mix = (w1 - w0) * ((r0 + r1) / 2 - centre)
        rate = (r1 - r0) * (w0 + w1) / 2
        result["segments"][seg] = {"w0": w0, "w1": w1, "r0": r0, "r1": r1, "mix": mix, "rate": rate}
        result["mix"] += mix
        result["rate"] += rate
    return result


def main_cause(result):
    """"mix" or "rate", whichever effect is larger in absolute size. A tie goes to "rate"."""
    return "mix" if abs(result["mix"]) > abs(result["rate"]) else "rate"


if __name__ == "__main__":
    import os
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "daily_devices.csv")
    p = load_periods(data, "2026-10-01")
    print("device    sessions Sep  Oct    share Sep  Oct    rate Sep  Oct")
    for seg in sorted(set(p["prior"]) | set(p["current"])):
        s0, o0 = p["prior"][seg]
        s1, o1 = p["current"][seg]
        n0 = sum(s for s, _ in p["prior"].values())
        n1 = sum(s for s, _ in p["current"].values())
        print("%-8s  %12d %6d    %8.1f%% %4.1f%%    %6.2f%% %4.2f%%" % (
            seg, s0, s1, 100 * s0 / n0, 100 * s1 / n1, 100 * o0 / s0, 100 * o1 / s1))
    print("overall rate %.2f%% -> %.2f%%" % (100 * overall_rate(p["prior"]), 100 * overall_rate(p["current"])))
    r = decompose(p["prior"], p["current"])
    print("change %+.3f points = mix %+.3f + rate %+.3f   main cause: %s" % (
        100 * r["total"], 100 * r["mix"], 100 * r["rate"], main_cause(r)))
    for seg, c in r["segments"].items():
        print("  %-8s mix %+.3f  rate %+.3f" % (seg, 100 * c["mix"], 100 * c["rate"]))
