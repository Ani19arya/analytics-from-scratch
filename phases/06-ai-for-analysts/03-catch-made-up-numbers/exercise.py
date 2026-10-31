"""Exercise: catch made-up numbers in an AI-written summary.

load_csv, compute_metrics and matches are done for you, and so are the parts of the
NUMBER pattern around the digits. Fill in what is marked TODO: DIGITS, read_number,
extract_numbers and check_summary. Then run: python3 test_lesson.py
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Labels that contain digits but are not numbers: Q2, H1, FY26, 3rd.
LABEL = r"\b(?:[QH][1-4]|FY\d{2,4}|\d+(?:st|nd|rd|th))\b"
# A minus or plus sign, but not one inside a word or a range such as 3-5.
# \u2212 is the Unicode minus sign, which LLMs often write.
SIGN = r"(?<![\w.,])[-+\u2212]"
# $, pound, euro, rupee.
CURRENCY = r"[$\u00a3\u20ac\u20b9]"
# Digits in groups of three with commas, or plain digits; optional decimals.
# TODO: write the pattern. It must read "156,142" as one number and "650.59" as one
# number, and must not swallow the full stop at the end of a sentence.
DIGITS = r"TODO"
# 51k, 1.5M, 2bn, 3 million. Letter suffixes must touch the number.
SUFFIX = r"\s?(?:thousand|million|billion)\b|(?:k|K|m|M|mn|bn|B)\b"

NUMBER = re.compile(
    "(?P<label>%s)|(?P<sign>%s)?(?P<cur>%s)?(?P<digits>%s)(?P<suffix>%s)?(?P<pct>\\s?%%)?"
    % (LABEL, SIGN, CURRENCY, DIGITS, SUFFIX))

SCALE = {"k": 3, "thousand": 3, "m": 6, "mn": 6, "million": 6, "b": 9, "bn": 9, "billion": 9}


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def read_number(m):
    """Turn one NUMBER match into (value, decimals), or None for a label or a year.

    m.group("label") is set for Q2, H1, FY26 or 3rd: return None.
    m.group("digits") is the number as written. Remove commas. decimals is how many
    digits follow the point. A year is 4 plain digits from 1900 to 2100 with no sign,
    currency, suffix or percent: return None.
    m.group("suffix") such as k or million multiplies by 10 ** SCALE[suffix.strip().lower()]
    and lowers decimals by the same power: 77.9k -> (77900.0, -2).
    m.group("sign") of "-" or "\u2212" makes the value negative.
    Round the value to max(decimals, 0) places so 77.9 * 1000 is exactly 77900.0.
    """
    # TODO
    raise NotImplementedError


def extract_numbers(sentence):
    """Return [(value, decimals), ...] in the order they appear, skipping labels and years.

    Use NUMBER.finditer and read_number.
    """
    # TODO
    raise NotImplementedError


def compute_metrics(rows):
    """The true value of every metric the summary is allowed to mention."""
    rev = [int(r["revenue"]) for r in rows]
    total = sum(rev)

    def region(name):
        return sum(int(r["revenue"]) for r in rows if r["region"] == name)

    def month(name):
        return sum(int(r["revenue"]) for r in rows if r["month"] == name)

    def change(new, old):
        return (new - old) / old * 100

    jan, mar, apr, jun = month("Jan"), month("Mar"), month("Apr"), month("Jun")
    q1 = sum(month(m) for m in ("Jan", "Feb", "Mar"))
    q2 = sum(month(m) for m in ("Apr", "May", "Jun"))
    return {
        "total_revenue": total,
        "order_count": len(rows),
        "avg_order_value": total / len(rows),
        "region_count": len(set(r["region"] for r in rows)),
        "north_revenue": region("North"),
        "south_revenue": region("South"),
        "west_revenue": region("West"),
        "north_share_pct": region("North") / total * 100,
        "jan_revenue": jan,
        "jun_revenue": jun,
        "growth_pct": change(jun, jan),
        "q2_revenue": q2,
        "q2_vs_q1_pct": change(q2, q1),
        "apr_revenue": apr,
        "apr_vs_mar_pct": change(apr, mar),
    }


def matches(claimed, decimals, actual):
    """A stated number matches if the true value rounds to it at the stated precision."""
    return abs(actual - claimed) <= 0.5 * 10 ** (-decimals) + 1e-9


def check_summary(rows, summary):
    """Return one dict per number: sentence_id, metric, claimed, actual, ok."""
    # TODO: split s["metrics"] on ";", extract the numbers from s["sentence"],
    # pair them in order, and compare each with matches(). Raise ValueError if
    # the counts differ.
    raise NotImplementedError


def main():
    for r in check_summary(load_csv("orders.csv"), load_csv("ai_summary.csv")):
        flag = "ok  " if r["ok"] else "FLAG"
        print(flag, r["sentence_id"], r["metric"].ljust(16), "claimed", r["claimed"], "actual", round(r["actual"], 2))


if __name__ == "__main__":
    main()
