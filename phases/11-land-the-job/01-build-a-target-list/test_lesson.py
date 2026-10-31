"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are worked out here a second way: the drop is re-read row by row, dates are
parsed with strptime, roles are grouped with a regex key, and the company score is rebuilt from
its definition. Everything runs on the committed postings and on a second set built in memory
from another seed.
"""
import csv
import datetime
import importlib.util
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
DROP_DIR = os.path.join(HERE, "..", "..", "..", "data", "job-market", "2026-10")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 2202
PROFILE = {"countries": ["GB", "IE"], "levels": ["Entry Level", "Mid Level", "Not Specified"],
           "skills": ["SQL", "Excel", "Power BI", "Python"], "min_fit": 0.5, "max_age": 30, "as_of": "2026-10-31"}


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def ref_where(levels, min_postings=30):
    totals = {r["country"]: (int(r["postings"]), int(r["companies"])) for r in read(os.path.join(DROP_DIR, "by_country.csv"))}
    lv = {}
    for r in read(os.path.join(DROP_DIR, "by_country_seniority.csv")):
        lv.setdefault(r["country"], {})[r["experience"]] = int(r["postings"])
    out = []
    for c, (n, comp) in totals.items():
        if c == "UNKNOWN" or n < min_postings:
            continue
        at = sum(v for k, v in lv.get(c, {}).items() if k in levels)
        lab = n - lv.get(c, {}).get("Not Specified", 0)
        lab_at = sum(v for k, v in lv.get(c, {}).items() if k in levels and k != "Not Specified")
        out.append((c, n, comp, at, None if lab == 0 else lab_at * 100.0 / lab))
    return sorted(out, key=lambda t: (-t[3], t[0]))


def days(as_of, d):
    fmt = "%Y-%m-%d"
    return (datetime.datetime.strptime(as_of, fmt) - datetime.datetime.strptime(d, fmt)).days


def ref_scores(postings, prof):
    roles = {}
    for p in postings:
        key = (p["company"], re.sub(r"\s+", " ", p["title"].strip()).lower(), p["country"])
        if key not in roles or days(prof["as_of"], p["posted_date"]) > days(prof["as_of"], roles[key]["posted_date"]):
            roles[key] = p
    mine = set(s.lower() for s in prof["skills"])
    comp = {}
    for p in roles.values():
        age = days(prof["as_of"], p["posted_date"])
        asked = set(x.strip().lower() for x in p["skills"].split(",")) - {""}
        fit = None if not asked else len(asked & mine) / float(len(asked))
        if (p["country"] in prof["countries"] and p["seniority"] in prof["levels"] and 0 <= age <= prof["max_age"]
                and (fit is None or fit >= prof["min_fit"])):
            comp.setdefault(p["company"], []).append((0.5 if fit is None else fit, age))
    out = []
    for c, items in comp.items():
        mf = sum(f for f, _ in items) / len(items)
        new = min(a for _, a in items)
        sc = 40 * mf + 30 * max(0.0, (30 - new) / 30.0) + 6 * min(len(items), 5)
        out.append((c, len(items), mf, new, sc))
    return sorted(out, key=lambda t: (-round(t[4], 6), -t[1], t[3], t[0]))


def posting(company="Acme Test", title="Data Analyst", country="GB", seniority="Entry Level",
            skills="SQL, Excel", posted_date="2026-10-21", source="careers_page"):
    return {"company": company, "title": title, "country": country, "seniority": seniority,
            "skills": skills, "posted_date": posted_date, "source": source}


class TestCountries(unittest.TestCase):
    def test_real_drop(self):
        drop = lesson.load_drop(DROP_DIR)
        for levels in (["Entry Level", "Mid Level"], ["Entry Level"], ["Entry Level", "Not Specified"]):
            got = lesson.where_to_look(drop, levels)
            want = ref_where(levels)
            self.assertEqual([r["country"] for r in got], [w[0] for w in want],
                             "countries for %s: most postings at your levels first, ties by code, UNKNOWN and small countries left out" % levels)
            for g, w in zip(got, want):
                self.assertEqual((g["postings"], g["companies"], g["at_level"]), w[1:4], "counts for %s" % w[0])
                self.assertAlmostEqual(g["share_of_labelled"], w[4], msg="%s: share of LABELLED postings, so leave Not Specified out of both parts" % w[0])
        top = lesson.where_to_look(drop, ["Entry Level", "Mid Level"])
        self.assertEqual(top[0]["at_level"], 1048 + 375)
        self.assertNotIn("UNKNOWN", [r["country"] for r in top], "UNKNOWN is not a place you can move to or target")
        self.assertNotIn("KE", [r["country"] for r in top], "Kenya has 2 postings, below MIN_POSTINGS")

    def test_hand_made_drop(self):
        drop = {"AA": {"postings": 40, "companies": 9, "levels": {"Not Specified": 40}, "skills": {}, "any_tool": 0},
                "BB": {"postings": 40, "companies": 3, "levels": {"Entry Level": 10, "Mid Level": 30}, "skills": {"SQL": 5}, "any_tool": 10},
                "CC": {"postings": 50, "companies": 3, "levels": {"Entry Level": 10, "Senior": 40}, "skills": {}, "any_tool": 0}}
        got = lesson.where_to_look(drop, ["Entry Level"])
        self.assertEqual([r["country"] for r in got], ["BB", "CC", "AA"], "a tie on at_level is broken by country code")
        self.assertIsNone(got[2]["share_of_labelled"], "every posting is Not Specified: there is no labelled share, return None")
        self.assertAlmostEqual(got[0]["share_of_labelled"], 25.0)
        self.assertEqual(lesson.where_to_look({}, ["Entry Level"]), [])
        self.assertAlmostEqual(lesson.skill_share(drop, "BB", "SQL"), 50.0)
        self.assertIsNone(lesson.skill_share(drop, "AA", "SQL"), "no posting lists a tool: no share, not 0")
        self.assertIsNone(lesson.skill_share(drop, "ZZ", "SQL"))
        real = lesson.load_drop(DROP_DIR)
        self.assertAlmostEqual(lesson.skill_share(real, "GB", "SQL"), 100.0 * [int(r["postings_listing_skill"]) for r in read(os.path.join(DROP_DIR, "by_country_skill.csv")) if r["country"] == "GB" and r["skill"] == "SQL"][0]
                               / [int(r["postings_listing_any_tool"]) for r in read(os.path.join(DROP_DIR, "by_country_skill.csv")) if r["country"] == "GB"][0])
        self.assertIsNone(lesson.skill_share(real, "KW", "SQL"))


class TestPostings(unittest.TestCase):
    def test_skills_and_fit(self):
        self.assertEqual(lesson.parse_skills(""), set())
        self.assertEqual(lesson.parse_skills(" sql , SQL, Power BI ,"), {"sql", "power bi"}, "lower-case, strip, drop empties, count once")
        self.assertIsNone(lesson.skill_fit(set(), ["SQL"]), "a posting with no skills listed has no fit: return None, not 0")
        self.assertAlmostEqual(lesson.skill_fit({"sql", "sas"}, ["SQL", "Excel"]), 0.5, msg="fit is the share of the posting's skills you have")
        self.assertEqual(lesson.skill_fit({"sas"}, ["SQL"]), 0)

    def test_age_and_match(self):
        self.assertEqual(lesson.age_days("2026-10-01", "2026-10-31"), 30)
        self.assertEqual(lesson.age_days("2026-10-31", "2026-10-31"), 0)
        self.assertTrue(lesson.is_match(posting(posted_date="2026-10-01"), PROFILE), "30 days old is still inside max_age 30")
        self.assertFalse(lesson.is_match(posting(posted_date="2026-09-30"), PROFILE), "31 days old is outside max_age 30")
        self.assertFalse(lesson.is_match(posting(posted_date="2026-11-02"), PROFILE), "a date after as_of is an error, not a match")
        self.assertFalse(lesson.is_match(posting(country="US"), PROFILE))
        self.assertFalse(lesson.is_match(posting(seniority="Senior"), PROFILE))
        self.assertTrue(lesson.is_match(posting(seniority="Not Specified"), PROFILE), "Not Specified is in the profile's levels")
        self.assertTrue(lesson.is_match(posting(skills=""), PROFILE), "no skills listed: you cannot rule it out, so it matches")
        self.assertTrue(lesson.is_match(posting(skills="SQL, SAS"), PROFILE), "fit 0.5 is exactly min_fit, so it matches")
        self.assertFalse(lesson.is_match(posting(skills="SQL, SAS, R"), PROFILE))

    def test_dedupe_keeps_first_seen(self):
        rows = [posting(posted_date="2026-09-01"), posting(title="DATA ANALYST ", posted_date="2026-10-25", source="reposter"),
                posting(country="IE", posted_date="2026-10-20")]
        got = lesson.dedupe(rows)
        self.assertEqual(len(got), 2, "same company, same title ignoring case and spaces, same country: one role")
        gb = [p for p in got if p["country"] == "GB"][0]
        self.assertEqual(gb["posted_date"], "2026-09-01", "keep the EARLIEST date: a repost does not make an old role fresh")
        self.assertEqual(lesson.dedupe([]), [])

    def test_company_score_by_hand(self):
        rows = [posting(company="Alpha", skills="SQL, Excel", posted_date="2026-10-31"),
                posting(company="Alpha", title="BI Analyst", skills="", posted_date="2026-10-16"),
                posting(company="Beta", skills="SQL", posted_date="2026-10-16"),
                posting(company="Gamma", skills="SQL", posted_date="2026-10-16"),
                posting(company="Delta", country="US")]
        got = lesson.score_companies(rows, PROFILE)
        self.assertEqual([r["company"] for r in got], ["Alpha", "Beta", "Gamma"], "Beta and Gamma tie on everything, so sort by name")
        a = got[0]
        self.assertEqual((a["roles"], a["newest_age"]), (2, 0))
        self.assertAlmostEqual(a["mean_fit"], 0.75, msg="an unknown fit counts as 0.5 in the mean")
        self.assertAlmostEqual(a["score"], 40 * 0.75 + 30 * 1 + 30 * 2 / 5.0)
        self.assertAlmostEqual(got[1]["score"], 40 + 15 + 6)
        self.assertEqual(lesson.score_companies([], PROFILE), [])

    def test_volume_is_capped(self):
        many = [posting(company="Big", title="Analyst %d" % i, skills="SQL, SAS", posted_date="2026-10-31") for i in range(12)]
        got = lesson.score_companies(many, PROFILE)
        self.assertAlmostEqual(got[0]["score"], 40 * 0.5 + 30 + 30, msg="volume counts up to 5 roles, then stops")


class TestOnData(unittest.TestCase):
    def check(self, rows, label):
        got = lesson.target_list(rows, PROFILE)
        want = ref_scores(rows, PROFILE)
        self.assertEqual([r["company"] for r in got], [w[0] for w in want[:30]], "%s: the top 30 companies, in order" % label)
        for g, w in zip(got, want):
            self.assertEqual((g["roles"], g["newest_age"]), (w[1], w[3]), "%s: roles and newest age for %s (after dedupe)" % (label, w[0]))
            self.assertAlmostEqual(g["score"], w[4], msg="%s: score for %s" % (label, w[0]))
        self.assertEqual(len(lesson.target_list(rows, PROFILE, n=5)), 5)
        self.assertEqual(len(lesson.score_companies(rows, PROFILE)), len(want), "%s: every matching company is scored" % label)

    def test_committed_postings(self):
        rows = read(os.path.join(HERE, "data", "postings.csv"))
        self.check(rows, "committed postings")
        self.assertNotIn(make_data.GIANT, [r["company"] for r in lesson.target_list(rows, PROFILE)],
                         "the company with the most postings does not match this profile")

    def test_second_dataset(self):
        self.check(make_data.build(seed=OTHER_SEED), "seed %d" % OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
