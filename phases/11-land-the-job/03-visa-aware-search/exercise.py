"""Exercise: visa-aware search, from scratch.

Fill in RESTRICTED, employer_key, classify_posting, company_keys, us_record, on_register,
verdict, triage and summary. sentences, read, load and main are done for you.
Then run: python3 test_lesson.py
"""
import csv
import os
import re

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Words at the end of a filed name that say what kind of company it is, not which company.
LEGAL_SUFFIXES = {"inc", "incorporated", "llc", "corp", "corporation", "co", "company",
                  "ltd", "limited", "plc", "llp", "lp", "na"}
# A previous or trading name follows one of these. Keep only the part before it.
NAME_CUT = re.compile(r"\b(?:fka|dba|formerly|aka)\b")

# TODO: a regex, for lower case text, that finds a restriction only citizens or clearance
# holders can meet: us citizen(s), us citizenship, us person(s), itar, security clearance,
# sc / dv / secret / top secret clearance, british citizen(s) or national(s).
# Careful: "clearance sale" is not a restriction.
RESTRICTED = None
SPONSOR = re.compile(r"\bsponsor")
NEGATION = re.compile(r"\b(?:not|no|never|nor|unable|cannot|without|unavailable)\b|n't\b")
VISA_WORD = re.compile(r"\b(?:visas?|h-?1b|work permits?|immigration|skilled worker|green cards?)\b")

SAYS = ["sponsors", "will_not_sponsor", "citizen_or_clearance", "not_stated"]
VERDICTS = ["apply", "ask_has_record", "ask_no_record", "ruled_out"]


def employer_key(name):
    """A matching key, so that 'AMAZON.COM SERVICES LLC' and 'Amazon com Services, LLC' agree."""
    # TODO: lower case; keep only the part before NAME_CUT; '&' to ' and ';
    # 'national association' to 'na'; anything not a letter or digit to a space; split;
    # drop trailing tokens that are in LEGAL_SUFFIXES; join with single spaces.
    raise NotImplementedError


def sentences(text):
    """Lower case sentences, with U.S. written as us so its full stops do not split a sentence."""
    text = re.sub(r"\bu\.s\.(?:a\.)?", "us", text.lower())
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def classify_posting(text):
    """One of SAYS, from the posting's own words."""
    # TODO: decide the order of the checks yourself. Which mistake is the expensive one?
    raise NotImplementedError


def company_keys(company, aliases):
    """The set of keys this company can appear under: its own name plus every
    filed_name listed for it in aliases (rows with company, filed_name)."""
    # TODO
    raise NotImplementedError


def us_record(company, history, aliases):
    """{"names": sorted filed names that match, "by_year": {fiscal_year (int): {"new", "continuing", "denials"}}}.
    Both are empty when the company is not in the data."""
    # TODO: match on keys, never on a substring of the name.
    raise NotImplementedError


def on_register(company, register, aliases):
    """Sorted organisation_name values on the register that match the company."""
    # TODO
    raise NotImplementedError


def verdict(says, has_record):
    """One of VERDICTS, for a candidate who needs sponsorship."""
    # TODO
    raise NotImplementedError


def triage(postings, history, register, aliases):
    """One dict per posting: posting_id, company, country, says, has_record, verdict.
    US postings use the history; GB postings use the register."""
    # TODO
    raise NotImplementedError


def summary(rows):
    """{verdict: count} with every verdict in VERDICTS present, zeros included."""
    # TODO
    raise NotImplementedError


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
