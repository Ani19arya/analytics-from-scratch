"""Solution: check an executive summary, and draft one from the analysis results.

A summary passes when:
- its first two lines give the headline change, its direction and the decision asked for,
- the headline change is written in points, not as a percent,
- every number in it is in the results file,
- it has a line that starts with "Caveat:",
- it is at most MAX_WORDS words.
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
MAX_WORDS = 100

# A number: an optional minus sign, digits with optional thousands commas, optional decimals.
# The lookbehind stops "GA4" or "Q3" giving a number, and stops "week-4" giving "-4".
# The lookahead stops "4.5x" giving "4" (a number glued to a word is not read at all).
NUMBER = re.compile(r"(?<![\w.,])-?\d+(?:,\d{3})*(?:\.\d+)?(?!\.?\w)")
UP_WORDS = {"rose", "rise", "risen", "up", "increased", "increase", "improved", "higher", "gained"}
DOWN_WORDS = {"fell", "fall", "fallen", "down", "decreased", "decrease", "dropped", "drop", "worsened", "lower", "declined"}
FLAT_WORDS = {"unchanged", "flat"}
DECISION_WORDS = {"approve", "decide", "decision", "choose", "agree"}

# The summary we would send Sanjana for the committed results (data/results.csv).
SUMMARY = """On-time deliveries in Pune rose 4.0 points, from 80.5% to 84.5%, on the new dispatch rule.
Please approve switching all four cities by 13 November.

Orders were split at random for 4 weeks: 903 on the new rule, 868 on the current one. The 95% interval for the change is 0.4 to 7.5 points, so the gain is real but could be small.
Caveat: this is Pune in ordinary weeks; the other cities and the festival peak may differ.
"""


def load_results(data_dir=DATA):
    """{name: value} from results.csv. Every value is text."""
    with open(os.path.join(data_dir, "results.csv"), newline="") as f:
        return {r["name"]: r["value"] for r in csv.DictReader(f)}


def numbers_in(text):
    """Every number in text, in order, with thousands commas removed: '1,240' -> '1240'."""
    return [m.replace(",", "") for m in NUMBER.findall(text)]


def first_two_lines(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines[:2])


def allowed_numbers(results):
    """The numbers a summary may quote: every number in a results value, exactly as written,
    plus the size of the headline change (its direction is said in words)."""
    allowed = set()
    for value in results.values():
        allowed.update(numbers_in(value))
    allowed.add(results["change_pts"].lstrip("-"))
    return allowed


def untraceable_numbers(text, results):
    """Numbers in the summary that are not in the results file, in order, each once."""
    allowed = allowed_numbers(results)
    out = []
    for n in numbers_in(text):
        if n not in allowed and n not in out:
            out.append(n)
    return out


def check_summary(text, results):
    """Sorted list of problem codes. An empty list means the summary passes."""
    if not text.strip():
        return ["empty"]
    problems = set()
    top = first_two_lines(text)
    words = set(re.findall(r"[a-z]+", top.lower()))
    size = results["change_pts"].lstrip("-")
    if size not in numbers_in(top):
        problems.add("headline")
    change = float(results["change_pts"])
    if change > 0:
        right, wrong = UP_WORDS, DOWN_WORDS | FLAT_WORDS
    elif change < 0:
        right, wrong = DOWN_WORDS, UP_WORDS | FLAT_WORDS
    else:
        right, wrong = FLAT_WORDS, UP_WORDS | DOWN_WORDS
    if not (words & right) or (words & wrong):
        problems.add("direction")
    if not (words & DECISION_WORDS):
        problems.add("decision")
    if re.search(r"(?<![\w.,])-?%s\s*(%%|percent)" % re.escape(size), text):
        problems.add("units")
    if untraceable_numbers(text, results):
        problems.add("untraceable")
    if not any(line.strip().lower().startswith("caveat:") for line in text.splitlines()):
        problems.add("caveat")
    if len(text.split()) > MAX_WORDS:
        problems.add("too_long")
    return sorted(problems)


def draft_summary(results):
    """A summary for any results file: answer first, decision second, detail and caveat after."""
    r = results
    change = float(r["change_pts"])
    size = r["change_pts"].lstrip("-")
    if change > 0:
        moved = "rose %s points" % size
    elif change < 0:
        moved = "fell %s points" % size
    else:
        moved = "were unchanged (%s points)" % size
    caveat = r["caveat"][0].upper() + r["caveat"][1:]
    lines = [
        "On-time deliveries in %s %s, from %s%% to %s%%, on the new dispatch rule."
        % (r["city"], moved, r["control_rate_pct"], r["pilot_rate_pct"]),
        "Decision needed by %s on %s: I recommend we %s."
        % (r["decide_by"], r["decision"], r["recommendation"]),
        "",
        "Orders were split at random over %s weeks (%s): %s on the new rule, %s on the current one. "
        "The %s for the change is %s to %s points."
        % (r["weeks"], r["period"], r["pilot_orders"], r["control_orders"], r["interval"], r["ci_low_pts"], r["ci_high_pts"]),
        "Caveat: %s." % caveat,
    ]
    return "\n".join(lines) + "\n"


def main():
    results = load_results()
    for name, text in (("your summary", SUMMARY), ("draft", draft_summary(results))):
        problems = check_summary(text, results)
        print("%s: %s" % (name, ", ".join(problems) if problems else "passes"))
    print()
    print(draft_summary(results))


if __name__ == "__main__":
    main()
