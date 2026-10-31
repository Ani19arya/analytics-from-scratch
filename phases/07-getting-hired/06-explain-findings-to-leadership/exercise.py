"""Exercise: check an executive summary, and draft one from the analysis results.

load_results, numbers_in, first_two_lines and main are done for you.
Write SUMMARY, then fill in untraceable_numbers, check_summary and draft_summary.
Then run: python3 test_lesson.py

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

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MAX_WORDS = 100

# A number: an optional minus sign, digits with optional thousands commas, optional decimals.
# The lookbehind stops "GA4" or "Q3" giving a number, and stops "week-4" giving "-4".
# The lookahead stops "4.5x" giving "4" (a number glued to a word is not read at all).
NUMBER = re.compile(r"(?<![\w.,])-?\d+(?:,\d{3})*(?:\.\d+)?(?!\.?\w)")
UP_WORDS = {"rose", "rise", "risen", "up", "increased", "increase", "improved", "higher", "gained"}
DOWN_WORDS = {"fell", "fall", "fallen", "down", "decreased", "decrease", "dropped", "drop", "worsened", "lower", "declined"}
FLAT_WORDS = {"unchanged", "flat"}
DECISION_WORDS = {"approve", "decide", "decision", "choose", "agree"}

# TODO: write the summary you would send Sanjana for data/results.csv.
# Answer first (the change in points and its direction), the decision second,
# then the detail, then a line that starts with "Caveat:". Copy numbers from results.csv.
SUMMARY = """"""


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


def untraceable_numbers(text, results):
    """Numbers in the summary that are not in the results file, in order, each once."""
    # TODO: allowed = every number in every results value (use numbers_in), exactly as written,
    # plus the size of the headline change: results["change_pts"] without its minus sign.
    # Return the numbers_in(text) that are not allowed, in order, without repeats.
    raise NotImplementedError


def check_summary(text, results):
    """Sorted list of problem codes. An empty list means the summary passes."""
    # TODO: if the text is blank, return ["empty"]. Otherwise collect these codes:
    #   "headline"    the size of results["change_pts"] is not a number in the first two lines
    #   "direction"   the first two lines have no word from the right set (UP_WORDS when the
    #                 change is above 0, DOWN_WORDS below 0, FLAT_WORDS at 0), or a word from another set
    #   "decision"    the first two lines have no word from DECISION_WORDS
    #   "units"       the headline size is written as a percent: "4.0%" or "4.0 percent"
    #   "untraceable" untraceable_numbers is not empty
    #   "caveat"      no line starts with "Caveat:" (any case)
    #   "too_long"    more than MAX_WORDS words (text.split())
    # Words: re.findall(r"[a-z]+", first_two_lines(text).lower()).
    raise NotImplementedError


def draft_summary(results):
    """A summary for any results file: answer first, decision second, detail and caveat after."""
    # TODO: line 1: the metric moved (rose / fell / were unchanged) by the size of change_pts
    #       points, from control_rate_pct% to pilot_rate_pct%.
    # line 2: the decision and when it is needed (decide_by), with the recommendation.
    # then the orders in each group, the weeks and the interval (ci_low_pts to ci_high_pts),
    # and "Caveat: " + results["caveat"].
    # Only use numbers from results. It must pass check_summary for every seed.
    raise NotImplementedError


def main():
    results = load_results()
    for name, text in (("your summary", SUMMARY), ("draft", draft_summary(results))):
        problems = check_summary(text, results)
        print("%s: %s" % (name, ", ".join(problems) if problems else "passes"))
    print()
    print(draft_summary(results))


if __name__ == "__main__":
    main()
