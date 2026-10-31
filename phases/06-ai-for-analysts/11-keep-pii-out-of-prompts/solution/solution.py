"""Solution: replace emails, phone numbers and card numbers with stable placeholders, then
audit the whole prompt and block it if anything that looks personal is left."""
import csv
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")

# Not inside a longer word, id or URL path: no letter, digit, #, /, ., + or hyphen just before.
EDGE_BEFORE = r"(?<![\w#/.+-])"
EDGE_AFTER = r"(?!\w)"

# local part, then @ (or %40, its URL-encoded form), then a domain with at least one dot.
EMAIL = re.compile(r"(?<![\w.%+-])[A-Za-z0-9._%+-]+(?:@|%40)[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w-])")
# 13 to 19 digits, optionally in groups split by single spaces or hyphens.
CARD_CANDIDATE = re.compile(r"(?<![\w-])\d(?:[ -]?\d){12,18}(?![\w-])")
# Indian mobile: optional +91, 0091 or 0, then 10 digits starting 6 to 9, optionally split 5 and 5.
IN_PHONE = re.compile(EDGE_BEFORE + r"(?:\+91[\s-]?|0091[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}" + EDGE_AFTER)
# US: optional +1, then (415) 555-0142, 415-555-0142, 415.555.0142, 415 555 0142, or +14155550142.
US_PHONE = re.compile(EDGE_BEFORE + r"(?:(?:\+1[\s.-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}|\+1\d{10})" + EDGE_AFTER)
# "asha dot k at example dot com": the redactor leaves it, the audit blocks it.
SPELLED_EMAIL = re.compile(r"\b[\w.]+\s+(?:at|\[at\]|\(at\))\s+[\w-]+(?:\s+(?:dot|\[dot\]|\(dot\))\s+[\w-]+)+\b", re.I)

LABEL = {"email": "EMAIL", "phone": "PHONE", "card": "CARD"}


def load_csv(name):
    with open(os.path.join(DATA, name), newline="") as f:
        return list(csv.DictReader(f))


def luhn_ok(number):
    """The Luhn check that card numbers pass. Spaces and hyphens are ignored."""
    digits = [int(ch) for ch in number if ch.isdigit()]
    if not digits:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def normalise(kind, value):
    if kind == "email":
        return value.replace("%40", "@").lower()
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits[-10:] if kind == "phone" else digits


def find_pii(text):
    """[(start, end, kind, normalised value)], sorted, never overlapping.

    Emails first, then phones, then card candidates that pass Luhn. A later match that
    overlaps an earlier one is skipped. Phones go before cards because a number written
    with 0091 has 14 digits and can pass the Luhn check by chance."""
    found = []

    def free(s, e):
        return all(e <= fs or s >= fe for fs, fe, _, _ in found)

    for m in EMAIL.finditer(text):
        found.append((m.start(), m.end(), "email", normalise("email", m.group())))
    for pattern in (IN_PHONE, US_PHONE):
        for m in pattern.finditer(text):
            if free(m.start(), m.end()):
                found.append((m.start(), m.end(), "phone", normalise("phone", m.group())))
    for m in CARD_CANDIDATE.finditer(text):
        if luhn_ok(m.group()) and free(m.start(), m.end()):
            found.append((m.start(), m.end(), "card", normalise("card", m.group())))
    return sorted(found)


def redact(text, mapping):
    """Replace every find with a placeholder such as [EMAIL_1].

    mapping {(kind, normalised): placeholder} is shared across calls, so the same person gets
    the same placeholder in every message. It stays inside the building: never send it."""
    out, last = [], 0
    for start, end, kind, norm in find_pii(text):
        key = (kind, norm)
        if key not in mapping:
            n = 1 + sum(1 for k in mapping if k[0] == kind)
            mapping[key] = "[%s_%d]" % (LABEL[kind], n)
        out.append(text[last:start])
        out.append(mapping[key])
        last = end
    out.append(text[last:])
    return "".join(out)


def redact_all(texts):
    mapping = {}
    return [redact(t, mapping) for t in texts], mapping


def audit(prompt):
    """Everything in the final prompt that still looks personal: [(kind, text)]. Empty means clean."""
    findings = [(kind, prompt[s:e]) for s, e, kind, _ in find_pii(prompt)]
    findings += [("spelled_email", m.group()) for m in SPELLED_EMAIL.finditer(prompt)]
    return findings


class Blocked(Exception):
    pass


def send_or_block(prompt):
    """Return the prompt if the audit is clean. Otherwise raise Blocked: fail closed, never fix silently."""
    findings = audit(prompt)
    if findings:
        raise Blocked("not sent, personal data found: %s" % ", ".join(kind for kind, _ in findings))
    return prompt


INSTRUCTIONS = "Summarise this support message in one sentence for the weekly report."


def main():
    rows = load_csv("messages.csv")
    redacted, mapping = redact_all([r["text"] for r in rows])
    sent = blocked = 0
    for r, text in zip(rows, redacted):
        try:
            send_or_block(INSTRUCTIONS + "\n\n" + text)
            sent += 1
        except Blocked:
            blocked += 1
    counts = {}
    for kind, _ in mapping:
        counts[kind] = counts.get(kind, 0) + 1
    print("messages %d, ready to send %d, blocked for review %d" % (len(rows), sent, blocked))
    print("distinct values replaced:", dict(sorted(counts.items())))
    for r, text in list(zip(rows, redacted))[:4]:
        print(r["message_id"], text)


if __name__ == "__main__":
    main()
