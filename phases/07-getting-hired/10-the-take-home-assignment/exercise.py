"""Exercise 07-10: the take-home assignment.

load_orders, read_answers, sections and numbers_in are done for you. Fill in clean,
expected_answers, check_answers, check_writeup and grade. Run: python3 test_lesson.py

A grader for take-home submissions. It recomputes the answers from the raw data, then
checks the write-up against a rubric. grade(folder, rows) returns a sorted list of problem
codes; an empty list is a strong submission.

  answers_wrong     answers.csv is missing, lacks a question, or a value does not match
  no_code           no code or query file in the folder (.py, .sql, .ipynb, .r)
  no_readme         no README.md (the write-up checks below are then skipped)
  answer_not_first  the first line of text under the title does not give the top region
                    (as the submission's own answers.csv names it) and a number
  data_checks       the "## Data checks" section needs, for each problem in the data, a line
                    with its word (duplicate, test, refund) and the count found in the data
  no_assumptions    no "## Assumptions" section with at least one "- " bullet
  too_long          more than MAX_WORDS words: Hana reads one page
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
QUESTIONS = ("oct_revenue", "top_growth_region", "top_growth_amount", "repeat_rate_pct")
TOLERANCE = {"oct_revenue": 0.01, "top_growth_amount": 0.01, "repeat_rate_pct": 0.05}
TEST_DOMAIN = "@kestrelhome.test"
CODE_SUFFIXES = (".py", ".sql", ".ipynb", ".r")
MAX_WORDS = 500
# Each data check needs a line with its word and its count, such as "24 duplicate rows".
CHECK_WORDS = {"duplicates": "duplicat", "test_orders": "test", "refunded": "refund"}


def load_orders(path=os.path.join(DATA, "takehome", "orders.csv")):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def read_answers(folder):
    """{question: answer text} from folder/answers.csv, or {} if there is no file."""
    path = os.path.join(folder, "answers.csv")
    if not os.path.isfile(path):
        return {}
    with open(path, newline="") as f:
        return {r["question"].strip(): r["answer"].strip() for r in csv.DictReader(f)}


def sections(text):
    """{"## Heading": the text under it, up to the next heading}."""
    out, current = {}, None
    for line in text.splitlines():
        if line.startswith("#"):
            current = line.strip()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def numbers_in(text):
    """Every number in text, with $ and thousands commas removed: '$3,353.18' -> '3353.18'."""
    return [m.replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text)]


def clean(rows):
    """Remove the three data problems, in this order:
    1. repeated order_id: keep the first row of each order
    2. test orders: customer_email ends with TEST_DOMAIN
    3. refunded orders: status is not "paid"
    Returns (paid rows, {"duplicates": n, "test_orders": n, "refunded": n})."""
    # TODO
    raise NotImplementedError


def expected_answers(paid):
    """The four answers from cleaned rows, as numbers (the region as text).
    Growth = October revenue - September revenue per region; the top region is the
    largest growth, ties to the region that comes first alphabetically. The repeat rate is
    the percentage of October customers with 2 or more October orders (0.0 with none)."""
    # TODO: revenue by (month, region) first; months are order_date[:7].
    raise NotImplementedError


def check_answers(submitted, expected):
    """Sorted list of questions that are missing or wrong. Numbers must be within
    TOLERANCE (a "$" and thousands commas are allowed); the region matches ignoring case."""
    # TODO
    raise NotImplementedError


def check_writeup(text, counts, region):
    """Problem codes for the write-up (answer_not_first, data_checks, no_assumptions,
    too_long), sorted. region is the top region the submission itself names."""
    # TODO: use sections, numbers_in and CHECK_WORDS.
    raise NotImplementedError


def grade(folder, rows):
    """All problem codes for one submission folder, sorted. [] is a strong submission."""
    # TODO: put the pieces together. Skip the write-up checks when there is no README.md.
    raise NotImplementedError


def main():
    rows = load_orders()
    paid, counts = clean(rows)
    print(len(rows), "rows;", counts)
    print(expected_answers(paid))
    for name in ("strong", "weak_fast", "weak_buried"):
        print(name, grade(os.path.join(DATA, "submissions", name), rows))


if __name__ == "__main__":
    main()
