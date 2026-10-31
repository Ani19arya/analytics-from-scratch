"""Tests for lesson 11-03: visa-aware search.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Expected answers come from labels written out by hand below (committed data) or from the
generator's truth (second datasets built in memory). Sums and verdicts are worked out here
in plain Python, never read from the solution.
"""
import csv
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

sys.path.insert(0, HERE)
import make_data  # noqa: E402

# What a careful reader concludes from each committed posting, by hand.
SAYS = {
    "V01": "not_stated", "V02": "sponsors", "V03": "not_stated", "V04": "not_stated",
    "V05": "not_stated", "V06": "not_stated", "V07": "will_not_sponsor", "V08": "not_stated",
    "V09": "not_stated", "V10": "will_not_sponsor", "V11": "not_stated",
    "V12": "citizen_or_clearance", "V13": "citizen_or_clearance", "V14": "sponsors",
    "V15": "will_not_sponsor", "V16": "not_stated", "V17": "sponsors", "V18": "not_stated",
    "V19": "will_not_sponsor", "V20": "citizen_or_clearance", "V21": "not_stated", "V22": "not_stated",
}
# The filed names that really belong to each committed company.
NAMES = {
    "Kestrel Ledger": ["KESTREL LEDGER INC", "KESTREL LEDGER INC FKA KESTREL BOOKS LLC", "KESTREL LEDGER, INC."],
    "Orrin Health": ["ORRIN SERVICES CORP"],
    "Pellow Freight": ["PELLOW FREIGHT LLC"],
    "Saltmarsh Retail": [],
    "Tamsin Bank": ["TAMSIN BANK NA", "TAMSIN BANK, NATIONAL ASSOCIATION"],
    "Brindlecombe Aerospace": ["BRINDLECOMBE AEROSPACE CORP"],
    "Quarry Lane Analytics": [],
    "Larchmere Insurance": [],
}
REGISTER_NAMES = {
    "Ashgrove Mutual": ["ASHGROVE MUTUAL LIMITED"],
    "Thistledown Media": ["Thistledown Media Ltd"],
    "Fenmoor Defence": ["FENMOOR DEFENCE PLC"],
    "Wrenfield Retail": [],
    "Cobbold & Hart": ["COBBOLD AND HART LLP"],
}


def read(name):
    with open(os.path.join(HERE, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def as_dicts(rows, header):
    return [dict(zip(header, [str(v) for v in r])) for r in rows]


def expected_by_year(history, names):
    out = {}
    for r in history:
        if r["employer_name"] in names:
            y = out.setdefault(int(r["fiscal_year"]), {"new": 0, "continuing": 0, "denials": 0})
            y["new"] += int(r["new_approvals"])
            y["continuing"] += int(r["continuing_approvals"])
            y["denials"] += int(r["denials"])
    return out


def expected_verdict(says, has_record):
    table = {"will_not_sponsor": "ruled_out", "citizen_or_clearance": "ruled_out", "sponsors": "apply"}
    if says in table:
        return table[says]
    return "ask_has_record" if has_record else "ask_no_record"


class TestEmployerKey(unittest.TestCase):
    def test_amazon_names_from_the_real_evidence(self):
        names = ["AMAZON COM SERVICES LLC", "AMAZON.COM SERVICES LLC",
                 "AMAZON.COM SERVICES LLC FKA AMAZON.COM SERVICES INC"]
        keys = {lesson.employer_key(n) for n in names}
        self.assertEqual(keys, {"amazon com services"},
                         "the three USCIS names for Amazon should share one key: cut at FKA, dots to spaces, drop LLC")

    def test_variants(self):
        self.assertEqual(lesson.employer_key("Kestrel Ledger, Inc."), "kestrel ledger")
        self.assertEqual(lesson.employer_key("TAMSIN BANK, NATIONAL ASSOCIATION"), "tamsin bank")
        self.assertEqual(lesson.employer_key("Cobbold & Hart"), lesson.employer_key("COBBOLD AND HART LLP"),
                         "& and AND must give the same key")
        self.assertNotEqual(lesson.employer_key("ORRIN HEALTHCARE STAFFING INC"), lesson.employer_key("Orrin Health"),
                            "a longer name is a different employer, not a variant")

    def test_empty(self):
        self.assertEqual(lesson.employer_key(""), "", "an empty name gives an empty key")
        self.assertEqual(lesson.employer_key("LLC"), "", "a name that is only a suffix gives an empty key")


class TestClassify(unittest.TestCase):
    def test_committed_postings(self):
        for p in read("postings.csv"):
            self.assertEqual(lesson.classify_posting(p["text"]), SAYS[p["posting_id"]],
                             "%s: %s" % (p["posting_id"], p["text"]))

    def test_traps(self):
        cases = {
            "": "not_stated",
            "We proudly sponsor the city marathon.": "not_stated",
            "Analyse our clearance sale.": "not_stated",
            "Candidates must be authorized to work in the U.S.": "not_stated",
            "Sponsorship is not available.": "will_not_sponsor",
            "We don't sponsor visas.": "will_not_sponsor",
            "Authorized to work without the need for sponsorship.": "will_not_sponsor",
            "We sponsor H-1B visas.": "sponsors",
            "Visa sponsorship available. Requires U.S. citizenship.": "citizen_or_clearance",
            "Must hold DV clearance. We can sponsor a Skilled Worker visa.": "citizen_or_clearance",
            "We sponsor visas, but not for this role.": "will_not_sponsor",
        }
        for text, want in cases.items():
            self.assertEqual(lesson.classify_posting(text), want,
                             "%r should be %s: restriction first, then any negated sponsor sentence" % (text, want))


class TestRecords(unittest.TestCase):
    def setUp(self):
        self.history = read("uscis_history.csv")
        self.register = read("uk_register.csv")
        self.aliases = read("aliases.csv")

    def test_us_records(self):
        for company, names in NAMES.items():
            got = lesson.us_record(company, self.history, self.aliases)
            self.assertEqual(got["names"], sorted(names), company + ": which filed names match")
            self.assertEqual(got["by_year"], expected_by_year(self.history, names),
                             company + ": approvals and denials summed by fiscal year over every matching name")

    def test_register(self):
        for company, names in REGISTER_NAMES.items():
            self.assertEqual(lesson.on_register(company, self.register, self.aliases), sorted(names), company)

    def test_empty_tables(self):
        self.assertEqual(lesson.us_record("Kestrel Ledger", [], []), {"names": [], "by_year": {}},
                         "no history rows: empty names and years, not an error")
        self.assertEqual(lesson.on_register("Ashgrove Mutual", [], []), [])

    def test_zero_new_approvals_is_still_a_record(self):
        got = lesson.us_record("Pellow Freight", self.history, self.aliases)
        self.assertTrue(got["names"])
        self.assertEqual(sum(y["new"] for y in got["by_year"].values()), 0)


class TestVerdicts(unittest.TestCase):
    def test_verdict_table(self):
        for says in ["sponsors", "will_not_sponsor", "citizen_or_clearance", "not_stated"]:
            for has in (True, False):
                self.assertEqual(lesson.verdict(says, has), expected_verdict(says, has),
                                 "%s with record=%s: the posting decides first, silence is never ruled out" % (says, has))

    def test_triage_committed(self):
        postings, history, register, aliases = (read("postings.csv"), read("uscis_history.csv"),
                                                read("uk_register.csv"), read("aliases.csv"))
        rows = lesson.triage(postings, history, register, aliases)
        self.assertEqual([r["posting_id"] for r in rows], [p["posting_id"] for p in postings])
        for r in rows:
            has = bool((REGISTER_NAMES if r["country"] == "GB" else NAMES)[r["company"]])
            self.assertEqual(r["has_record"], has, r["posting_id"])
            self.assertEqual(r["verdict"], expected_verdict(SAYS[r["posting_id"]], has), r["posting_id"])
        want = {"apply": 0, "ask_has_record": 0, "ask_no_record": 0, "ruled_out": 0}
        for r in rows:
            want[expected_verdict(SAYS[r["posting_id"]], r["has_record"])] += 1
        self.assertEqual(lesson.summary(rows), want)
        self.assertEqual(want["ruled_out"], 7)

    def test_summary_empty(self):
        self.assertEqual(lesson.summary([]), {"apply": 0, "ask_has_record": 0, "ask_no_record": 0, "ruled_out": 0},
                         "every verdict is present, with zero")


class TestSecondDataset(unittest.TestCase):
    def test_other_seeds(self):
        for seed in (3, 8, 21):
            d = make_data.build(seed=seed)
            postings = as_dicts(d["postings"], ["posting_id", "company", "title", "country", "text"])
            history = as_dicts(d["history"], ["employer_name", "fiscal_year", "state", "new_approvals",
                                              "continuing_approvals", "denials"])
            register = as_dicts(d["register"], ["organisation_name", "town", "route"])
            aliases = as_dicts(d["aliases"], ["company", "filed_name"])
            truth = d["truth"]
            rows = lesson.triage(postings, history, register, aliases)
            for p, r in zip(postings, rows):
                names = truth["names"][p["company"]]
                self.assertEqual(r["says"], truth["says"][p["posting_id"]], "seed %d, %s: %s" % (seed, p["posting_id"], p["text"]))
                self.assertEqual(r["has_record"], bool(names), "seed %d, %s (%s)" % (seed, p["posting_id"], p["company"]))
                self.assertEqual(r["verdict"], expected_verdict(r["says"], bool(names)), "seed %d, %s" % (seed, p["posting_id"]))
                if p["country"] == "US":
                    got = lesson.us_record(p["company"], history, aliases)
                    self.assertEqual(got["names"], sorted(names), "seed %d, %s: matched names" % (seed, p["company"]))
                    self.assertEqual(got["by_year"], expected_by_year(history, names), "seed %d, %s" % (seed, p["company"]))
                else:
                    self.assertEqual(lesson.on_register(p["company"], register, aliases), sorted(names),
                                     "seed %d, %s" % (seed, p["company"]))


if __name__ == "__main__":
    unittest.main()
