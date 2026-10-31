"""Exercise: keep customers' emails, phone numbers and card numbers out of LLM prompts.

Write the two phone patterns, then fill in the functions marked TODO.
Then run: python3 test_lesson.py
"""
import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# Not inside a longer word, id or URL path: no letter, digit, #, /, ., + or hyphen just before.
EDGE_BEFORE = r"(?<![\w#/.+-])"
EDGE_AFTER = r"(?!\w)"

# Written for you.
# local part, then @ (or %40, its URL-encoded form), then a domain with at least one dot.
EMAIL = re.compile(r"(?<![\w.%+-])[A-Za-z0-9._%+-]+(?:@|%40)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")
# 13 to 19 digits, optionally in groups split by single spaces or hyphens.
CARD_CANDIDATE = re.compile(r"(?<![\w-])\d(?:[ -]?\d){12,18}(?![\w-])")
# "asha dot k at example dot com": the redactor leaves it, the audit blocks it.
SPELLED_EMAIL = re.compile(r"\b[\w.]+\s+(?:at|\[at\]|\(at\))\s+[\w-]+(?:\s+(?:dot|\[dot\]|\(dot\))\s+[\w-]+)+\b", re.I)

# TODO: Indian mobile. Optional "+91" or "0091" (each may be followed by one space or hyphen)
# or a single "0", then 10 digits that start with 6, 7, 8 or 9, optionally split 5 and 5 by
# one space or hyphen. Put EDGE_BEFORE in front and EDGE_AFTER at the end.
IN_PHONE = re.compile(r"TODO")
# TODO: US number. Optional "+1" (may be followed by a space, dot or hyphen), then either
# "(415) " or "415" plus a space, dot or hyphen, then "555", a space, dot or hyphen, and "0142".
# Also accept "+1" followed by 10 digits with no separators. Wrap it in EDGE_BEFORE and EDGE_AFTER.
US_PHONE = re.compile(r"TODO")

LABEL = {"email": "EMAIL", "phone": "PHONE", "card": "CARD"}


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def luhn_ok(number):
    """True when the digits of number pass the Luhn check. Ignore spaces and hyphens.

    From the right, double every second digit (the 2nd, 4th, ...), subtract 9 from any result
    above 9, add everything up. It passes when the total ends in 0. No digits: False.
    """
    # TODO
    raise NotImplementedError


def normalise(kind, value):
    """The key for a stable placeholder.
    email: replace "%40" with "@" and lower case. phone: the last 10 digits. card: all digits."""
    # TODO
    raise NotImplementedError


def find_pii(text):
    """Return [(start, end, kind, normalised value)], sorted by start, never overlapping.

    In this order: EMAIL matches ("email"), then IN_PHONE and US_PHONE ("phone"), then
    CARD_CANDIDATE matches that pass luhn_ok ("card"). Skip a match that overlaps one
    already found. (Phones go before cards: "0091 97281 38703" has 14 digits and can pass Luhn.)
    """
    # TODO
    raise NotImplementedError


def redact(text, mapping):
    """Replace each find with a placeholder like [EMAIL_1], [PHONE_2], [CARD_1].

    mapping is {(kind, normalised value): placeholder}, shared across calls. Reuse the
    placeholder when the key is already there; otherwise number it 1 + how many keys of
    that kind exist, and add it.
    """
    # TODO
    raise NotImplementedError


def redact_all(texts):
    """Return (list of redacted texts, mapping), with one mapping for the whole batch."""
    # TODO
    raise NotImplementedError


def audit(prompt):
    """Return [(kind, matched text)] for everything in the prompt that still looks personal:
    every find_pii match, plus every SPELLED_EMAIL match as kind "spelled_email". [] means clean."""
    # TODO
    raise NotImplementedError


class Blocked(Exception):
    pass


def send_or_block(prompt):
    """Return the prompt if audit(prompt) is empty. Otherwise raise Blocked. Never fix it silently."""
    # TODO
    raise NotImplementedError


if __name__ == "__main__":
    rows = load_csv("messages.csv")
    redacted, mapping = redact_all([r["text"] for r in rows])
    for r, text in list(zip(rows, redacted))[:5]:
        print(r["message_id"], text)
