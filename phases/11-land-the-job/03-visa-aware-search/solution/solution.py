"""Solution: visa-aware search. Classify what each posting says, join employers to their
sponsorship record by name key, and give each posting a verdict that never turns silence into a no.

Run from the lesson folder: python3 solution/solution.py
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Words at the end of a filed name that say what kind of company it is, not which company.
LEGAL_SUFFIXES = {"inc", "incorporated", "llc", "corp", "corporation", "co", "company",
                  "ltd", "limited", "plc", "llp", "lp", "na"}
# A previous or trading name follows one of these. Keep only the part before it.
NAME_CUT = re.compile(r"\b(?:fka|dba|formerly|aka)\b")

# Restrictions that rule out anyone who is not a citizen or does not hold a clearance.
RESTRICTED = re.compile(r"\b(?:us citizens?(?:hip)?|us persons?|itar|security clearance"
                        r"|(?:sc|dv|secret|top secret) clearance|british (?:citizens?|nationals?))\b")
SPONSOR = re.compile(r"\bsponsor")
NEGATION = re.compile(r"\b(?:not|no|never|nor|unable|cannot|without|unavailable)\b|n't\b")
VISA_WORD = re.compile(r"\b(?:visas?|h-?1b|work permits?|immigration|skilled worker|green cards?)\b")

SAYS = ["sponsors", "will_not_sponsor", "citizen_or_clearance", "not_stated"]
VERDICTS = ["apply", "ask_has_record", "ask_no_record", "ruled_out"]


def employer_key(name):
    """A matching key: lower case, previous names cut off, punctuation to spaces, & to 'and',
    'national association' to 'na', trailing legal suffixes removed."""
    s = NAME_CUT.split(name.lower())[0]
    s = s.replace("&", " and ").replace("national association", "na")
    tokens = re.sub(r"[^a-z0-9]+", " ", s).split()
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def sentences(text):
    """Lower case sentences, with U.S. written as us so its full stops do not split a sentence."""
    text = re.sub(r"\bu\.s\.(?:a\.)?", "us", text.lower())
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def classify_posting(text):
    """What the posting says in its own words, checked in this order:
    citizen_or_clearance, will_not_sponsor, sponsors, not_stated."""
    sents = sentences(text)
    if any(RESTRICTED.search(s) for s in sents):
        return "citizen_or_clearance"
    about = [s for s in sents if SPONSOR.search(s)]
    if any(NEGATION.search(s) for s in about):
        return "will_not_sponsor"
    if any(VISA_WORD.search(s) for s in about):
        return "sponsors"
    return "not_stated"


def company_keys(company, aliases):
    """The company's own key plus the key of every name it files under (aliases.csv)."""
    keys = {employer_key(company)}
    for a in aliases:
        if a["company"] == company:
            keys.add(employer_key(a["filed_name"]))
    return keys


def us_record(company, history, aliases):
    """{"names": sorted filed names that match, "by_year": {fiscal_year: {"new", "continuing", "denials"}}}.
    Both are empty when the company is not in the data."""
    keys = company_keys(company, aliases)
    names, by_year = set(), {}
    for r in history:
        if employer_key(r["employer_name"]) not in keys:
            continue
        names.add(r["employer_name"])
        y = by_year.setdefault(int(r["fiscal_year"]), {"new": 0, "continuing": 0, "denials": 0})
        y["new"] += int(r["new_approvals"])
        y["continuing"] += int(r["continuing_approvals"])
        y["denials"] += int(r["denials"])
    return {"names": sorted(names), "by_year": by_year}


def on_register(company, register, aliases):
    """Sorted organisation names on the register that match the company."""
    keys = company_keys(company, aliases)
    return sorted(r["organisation_name"] for r in register if employer_key(r["organisation_name"]) in keys)


def verdict(says, has_record):
    """For a candidate who needs sponsorship. The posting's own words come first; the
    employer's record only matters when the posting is silent."""
    if says in ("will_not_sponsor", "citizen_or_clearance"):
        return "ruled_out"
    if says == "sponsors":
        return "apply"
    return "ask_has_record" if has_record else "ask_no_record"


def triage(postings, history, register, aliases):
    """One dict per posting: posting_id, company, country, says, has_record, verdict.
    US postings are checked against the USCIS-style history, GB postings against the register."""
    rows = []
    for p in postings:
        says = classify_posting(p["text"])
        if p["country"] == "GB":
            has = bool(on_register(p["company"], register, aliases))
        else:
            has = bool(us_record(p["company"], history, aliases)["names"])
        rows.append({"posting_id": p["posting_id"], "company": p["company"], "country": p["country"],
                     "says": says, "has_record": has, "verdict": verdict(says, has)})
    return rows


def summary(rows):
    """{verdict: count} with every verdict present, zeros included."""
    out = {v: 0 for v in VERDICTS}
    for r in rows:
        out[r["verdict"]] += 1
    return out


def read(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def load(data_dir=DATA):
    return (read("postings.csv", data_dir), read("uscis_history.csv", data_dir),
            read("uk_register.csv", data_dir), read("aliases.csv", data_dir))


def main():
    postings, history, register, aliases = load()
    rows = triage(postings, history, register, aliases)
    for r in rows:
        print("%s  %-22s %s  %-20s record=%-5s %s" % (r["posting_id"], r["company"], r["country"],
                                                       r["says"], r["has_record"], r["verdict"]))
    print(summary(rows))


if __name__ == "__main__":
    main()
