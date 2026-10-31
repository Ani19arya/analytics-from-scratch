"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

Expected answers are worked out here a second way: role families come from the generator's
labels (not from a regex), tool lists are parsed with a lower-case lookup, and the data drop's
shares are recomputed from its raw counts. Everything runs on the committed snapshot and on
a second set of postings built in memory from another seed.
"""
import csv
import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
DROP = os.path.join(HERE, "..", "..", "..", "data", "job-market", "2026-10", "by_country_skill.csv")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 1705
SKILLS = ["SQL", "Python", "Excel", "Tableau", "Power BI", "Looker", "R", "dbt"]
FAMILIES = ["data", "business", "bi", "product"]


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def ref_counts(postings, labels):
    """Count by the generator's true family, parsing tools with a lower-case lookup."""
    fam = {r["posting_id"]: r["family"] for r in labels}
    lower = {s.lower(): s for s in SKILLS}
    out = {}
    for p in postings:
        items = [t.strip().lower() for t in p["tools"].split(",")]
        items = [t for t in items if t]
        if not items:
            continue
        g = out.setdefault(fam[p["posting_id"]], {"n": 0, "skills": dict.fromkeys(SKILLS, 0)})
        g["n"] += 1
        for s in {lower[t] for t in items if t in lower}:
            g["skills"][s] += 1
    return out


def ref_share(c, g, s):
    return 100.0 * c[g]["skills"][s] / c[g]["n"]


def ref_gaps(c, a, b):
    rows = [(s, ref_share(c, a, s), ref_share(c, b, s), ref_share(c, a, s) - ref_share(c, b, s)) for s in SKILLS]
    return sorted(rows, key=lambda r: (-abs(r[3]), r[0]))


def ref_drop():
    out = {}
    for r in read(DROP):
        out.setdefault(r["country"], {"n": int(r["postings_listing_any_tool"]), "skills": {}})
        out[r["country"]]["skills"][r["skill"]] = int(r["postings_listing_skill"])
    return out


def counts_of(rows):
    return lesson.count_by_group(rows, lambda p: lesson.title_family(p["title"]))


class TestTitles(unittest.TestCase):
    def test_families(self):
        cases = {"Data Analyst": "data", "Senior Business Analyst": "business", "BI Analyst": "bi",
                 "Business Intelligence Analyst": "bi", "Power BI Analyst": "bi", "Product Analyst II": "product",
                 "Product Data Analyst": "product", "Production Planning Analyst": "other",
                 "Business Data Analyst": "business", "People Analytics Analyst": "data",
                 "Financial Analyst": "other", "BUSINESS ANALYST": "business", "": "other"}
        for title, family in cases.items():
            self.assertEqual(lesson.title_family(title), family,
                             "%r should be %s: check the order of the rules and the word edges" % (title, family))

    def test_every_generated_title(self):
        for seed in (make_data.DEFAULT_SEED, OTHER_SEED):
            d = make_data.build(seed=seed)
            truth = {r["posting_id"]: r["family"] for r in d["labels"]}
            for p in d["postings"]:
                self.assertEqual(lesson.title_family(p["title"]), truth[p["posting_id"]],
                                 "seed %d: %r is labelled %s" % (seed, p["title"], truth[p["posting_id"]]))


class TestCounting(unittest.TestCase):
    def test_parse_tools(self):
        self.assertEqual(lesson.parse_tools(""), (set(), False), "an empty tool list lists no tool")
        self.assertEqual(lesson.parse_tools(" , "), (set(), False))
        self.assertEqual(lesson.parse_tools("Jira, Snowflake"), (set(), True),
                         "a posting that lists only other tools still lists a tool")
        self.assertEqual(lesson.parse_tools(" sql , SQL, power bi, RStudio"), ({"SQL", "Power BI"}, True),
                         "compare whole items without case: RStudio is not R")

    def test_count_once_and_skip_no_tools(self):
        rows = [{"title": "Data Analyst", "tools": "SQL, sql"}, {"title": "Data Analyst", "tools": ""},
                {"title": "Data Analyst", "tools": "Jira"}, {"title": "BI Analyst", "tools": "Power BI"}]
        c = counts_of(rows)
        self.assertEqual(c["data"]["n"], 2, "the posting with no tools is left out of n, as in the data drop")
        self.assertEqual(c["data"]["skills"]["SQL"], 1, "a skill listed twice counts once per posting")
        self.assertEqual(c["data"]["skills"]["dbt"], 0, "every skill should be a key, with 0 when unused")
        self.assertAlmostEqual(lesson.share(c, "data", "SQL"), 50.0)
        self.assertEqual(lesson.count_by_group([], lambda p: "x"), {})

    def test_share_edges(self):
        c = {"a": {"n": 0, "skills": dict.fromkeys(SKILLS, 0)}}
        self.assertIsNone(lesson.share(c, "a", "SQL"), "no postings means no share: return None, not 0")
        self.assertIsNone(lesson.share(c, "missing", "SQL"))

    def test_pool_is_a_ratio_of_sums(self):
        c = {"a": {"n": 10, "skills": dict(dict.fromkeys(SKILLS, 0), SQL=9)},
             "b": {"n": 90, "skills": dict(dict.fromkeys(SKILLS, 0), SQL=9)}}
        p = lesson.pool(c, ["a", "b", "nope"])
        self.assertEqual(p["n"], 100)
        self.assertEqual(p["skills"]["SQL"], 18, "pool adds counts: 18 of 100 is 18%, not the 50% average of 90% and 10%")

    def test_gaps_ties_and_small_groups(self):
        z = dict.fromkeys(SKILLS, 0)
        c = {"a": {"n": 40, "skills": dict(z, SQL=20, Excel=30, R=10)},
             "b": {"n": 40, "skills": dict(z, SQL=30, Excel=20, R=10)},
             "tiny": {"n": 5, "skills": dict(z, SQL=5)}}
        g = lesson.gaps(c, "a", "b")
        self.assertEqual([r[0] for r in g[:2]], ["Excel", "SQL"], "equal-sized gaps are sorted by skill name")
        self.assertAlmostEqual(g[0][3], 25.0)
        self.assertAlmostEqual(g[1][3], -25.0, msg="the gap is share a minus share b, so it can be negative")
        self.assertIsNone(lesson.gaps(c, "a", "tiny"), "5 postings is below MIN_N: return None")
        self.assertIsNone(lesson.gaps(c, "a", "nowhere"))


class TestOnData(unittest.TestCase):
    def check_postings(self, d, label):
        c = counts_of(d["postings"])
        exp = ref_counts(d["postings"], d["labels"])
        self.assertEqual(set(c), set(exp), "%s: families differ" % label)
        for fam in exp:
            self.assertEqual(c[fam]["n"], exp[fam]["n"], "%s: n for %s" % (label, fam))
            for s in SKILLS:
                self.assertAlmostEqual(lesson.share(c, fam, s), ref_share(exp, fam, s),
                                       msg="%s: share of %s in %s" % (label, s, fam))
        for a, b in (("bi", "business"), ("product", "data")):
            got = lesson.gaps(c, a, b)
            want = ref_gaps(exp, a, b)
            self.assertEqual([r[0] for r in got], [r[0] for r in want], "%s: gap order %s vs %s" % (label, a, b))
            for g, w in zip(got, want):
                self.assertAlmostEqual(g[3], w[3])
        for fam in FAMILIES:
            r = lesson.roadmap(c, fam, FAMILIES)
            rest = {"n": 0, "skills": dict.fromkeys(SKILLS, 0)}
            for o in FAMILIES:
                if o != fam:
                    rest["n"] += exp[o]["n"]
                    for s in SKILLS:
                        rest["skills"][s] += exp[o]["skills"][s]
            both = {"f": exp[fam], "r": rest}
            core = sorted([s for s in SKILLS if ref_share(both, "f", s) >= 50], key=lambda s: (-ref_share(both, "f", s), s))
            diff = sorted([(s, ref_share(both, "f", s) - ref_share(both, "r", s)) for s in SKILLS
                           if ref_share(both, "f", s) - ref_share(both, "r", s) > 0], key=lambda x: (-x[1], x[0]))
            self.assertEqual(r, {"core": core, "stands_out": [s for s, _ in diff[:2]]},
                             "%s: roadmap for %s (compare against the POOLED other families)" % (label, fam))
        return c

    def test_committed_postings(self):
        d = {"postings": read(os.path.join(HERE, "data", "postings.csv")), "labels": read(os.path.join(HERE, "data", "labels.csv"))}
        c = self.check_postings(d, "committed postings")
        self.assertEqual(lesson.gaps(c, "bi", "business")[0][0], "Power BI")

    def test_second_dataset(self):
        self.check_postings(make_data.build(seed=OTHER_SEED), "seed %d" % OTHER_SEED)

    def test_real_data_drop(self):
        drop = lesson.load_drop(DROP)
        exp = ref_drop()
        self.assertAlmostEqual(lesson.share(drop, "US", "SQL"), 100 * 1477 / 2056)
        got = lesson.gaps(drop, "US", "IN")
        want = sorted([(s, 100 * exp["US"]["skills"][s] / exp["US"]["n"] - 100 * exp["IN"]["skills"][s] / exp["IN"]["n"])
                       for s in SKILLS], key=lambda r: (-abs(r[1]), r[0]))
        self.assertEqual([r[0] for r in got], [r[0] for r in want], "US vs IN gap order, from the raw counts")
        self.assertEqual(got[0][0], "Power BI")
        self.assertAlmostEqual(got[0][3], want[0][1])
        self.assertIsNone(lesson.gaps(drop, "US", "KE"), "Kenya has 2 postings that list a tool: too few to compare")
        self.assertIsNone(lesson.share(drop, "KW", "SQL"), "no Kuwait posting lists a tool, so there is no share")


if __name__ == "__main__":
    unittest.main()
