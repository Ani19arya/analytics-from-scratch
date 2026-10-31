"""Checker for capstone 11-08: a 30-day job search plan.
Run: python3 test_lesson.py                    (checks exercise.py, your submission)
     CHECK_SOLUTION=1 python3 test_lesson.py   (checks solution/solution.py)

It checks what has one right answer: which postings are usable, the funnel of
the first week's log, and whether the plan you build keeps every rule in
DELIVERABLES.md (dates inside the 30 days, hours within the weekly budget,
only eligible, fresh, clean, target-family postings, one application per
role, search terms that cover the synonym families, a review every week with
the baseline funnel computed correctly). Every expected value is computed
here in plain Python, never read from the submission. The checks run on the
committed data, on a second dataset built in memory with another seed (so a
typed-in plan fails), and on small hand-made cases. Judgement (which postings
you put first, the write-up) is scored with RUBRIC.md, not here.
"""
import copy
import csv
import importlib.util
import json
import os
import sys
import unittest
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OTHER_SEED = 7
SOLUTION = os.environ.get("CHECK_SOLUTION") == "1"
TARGET = os.path.join(HERE, "solution", "solution.py") if SOLUTION else os.path.join(HERE, "exercise.py")
PLAN_FILE = os.path.join(HERE, "solution", "plan.json") if SOLUTION else os.path.join(HERE, "plan.json")

spec = importlib.util.spec_from_file_location("submission", TARGET)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
sys.path.insert(0, HERE)
import make_data  # noqa: E402

# ---- the rules, restated here so the checker does not trust the submission ----
FAMILIES = [("bi", ("business intelligence", "bi analyst", "bi developer")),
            ("product", ("product analyst", "growth analyst")),
            ("business", ("business analyst", "operations analyst")),
            ("data", ("data analyst", "insights analyst", "reporting analyst", "analytics analyst"))]
NO_WORDS = ("no visa sponsorship", "unable to sponsor", "must have the right to work")
YES_WORDS = ("visa sponsorship available", "we sponsor visas")
FLAG_WORDS = ("registration fee", "pay for your training", "guaranteed job", "whatsapp only", "security deposit")
MIN_HOURS = {"apply": 1.5, "network": 0.5, "search": 0.5, "follow_up": 0.25, "review": 1.0, "skill": 1.0}


def d(text):
    return date.fromisoformat(text)


def ref_family(title):
    low = title.lower()
    for fam, words in FAMILIES:
        for w in words:
            if w in low:
                return fam
    return None


def ref_eligible(p, prof):
    text = p["description"].lower()
    if p["work_mode"] == "remote":
        return any(r in prof["home_regions"] for r in p["remote_regions"].split(";"))
    if p["country"] == prof["home_country"]:
        return p["city"] in prof["onsite_cities"]
    return (not any(w in text for w in NO_WORDS)) and any(w in text for w in YES_WORDS)


def ref_fresh(p, prof):
    start = d(prof["plan_start"])
    if start - d(p["posted_date"]) > timedelta(days=prof["stale_after_days"]):
        return False
    return p["closes_on"] == "" or d(p["closes_on"]) >= start


def ref_clean(p):
    return not any(w in p["description"].lower() for w in FLAG_WORDS)


def key(p):
    return (p["company"].strip().lower(), p["title"].strip().lower(), p["city"].strip().lower())


def ref_usable(postings, log, prof):
    by_id = dict((p["posting_id"], p) for p in postings)
    applied_roles = set(key(by_id[r["posting_id"]]) for r in log if r["posting_id"] in by_id)
    keep = {}
    ordered = sorted(postings, key=lambda p: (p["posted_date"], -int(p["posting_id"][1:])))
    for p in ordered:  # later in this order = newer, then smaller id; the last one written wins
        if (ref_eligible(p, prof) and ref_fresh(p, prof) and ref_clean(p)
                and ref_family(p["title"]) in prof["target_families"] and key(p) not in applied_roles):
            keep[key(p)] = p["posting_id"]
    return sorted(keep.values())


def ref_funnel(log):
    rows = set((r["application_id"], r["channel"] or "unknown", r["event"].replace("phone_screen", "screen"))
               for r in log)
    apps = sorted(set(a for a, _, _ in rows))
    chan = {}
    for a, c, _ in sorted(rows):
        chan.setdefault(a, c)
    events = dict((a, set(e for b, _, e in rows if b == a)) for a in apps)
    later = {"screen": {"screen", "interview", "offer"}, "interview": {"interview", "offer"}, "offer": {"offer"}}
    reached = dict((s, [a for a in apps if events[a] & later[s]]) for s in later)
    responded = [a for a in apps if events[a] - {"applied"}]
    n = len(apps)
    out = {"applications": n, "responses": len(responded), "screens": len(reached["screen"]),
           "interviews": len(reached["interview"]), "offers": len(reached["offer"]),
           "rejections": len([a for a in apps if "rejected" in events[a]]), "no_reply": n - len(responded),
           "response_rate": len(responded) / n if n else None, "screen_rate": len(reached["screen"]) / n if n else None,
           "interview_rate": (len(reached["interview"]) / len(reached["screen"])) if reached["screen"] else None,
           "by_channel": {}}
    for c in sorted(set(chan.values())):
        mine = [a for a in apps if chan[a] == c]
        s = [a for a in mine if a in reached["screen"]]
        out["by_channel"][c] = {"applications": len(mine), "screens": len(s), "screen_rate": len(s) / len(mine)}
    return out


def assert_funnel(tc, got, exp, where):
    tc.assertIsInstance(got, dict, where + ": the funnel must be a dict")
    for k, v in exp.items():
        tc.assertIn(k, got, "%s: the funnel needs the key %r" % (where, k))
        if k == "by_channel":
            tc.assertEqual(sorted(got[k]), sorted(v), where + ": by_channel needs one entry per channel")
            for c in v:
                for kk, vv in v[c].items():
                    tc.assertAlmostEqual(got[k][c][kk], vv, places=9, msg="%s: by_channel[%r][%r]" % (where, c, kk))
        elif v is None:
            tc.assertIsNone(got[k], "%s: %s has no denominator here, so it is None (not 0)" % (where, k))
        else:
            tc.assertAlmostEqual(got[k], v, places=9,
                                 msg="%s: %s; count each application once and treat phone_screen as screen" % (where, k))


def posting(pid, title, city="Pune", country="IN", mode="hybrid", regions="", posted="2026-10-30",
            closes="", text="Build dashboards.", company="Acme Test Co"):
    return {"posting_id": pid, "company": company, "title": title, "city": city, "country": country,
            "work_mode": mode, "remote_regions": regions, "posted_date": posted, "closes_on": closes,
            "source": "job_board", "tools": "SQL;Excel", "description": text}


def ev(app, pid, event, day, channel="job_board"):
    return {"log_id": "L", "application_id": app, "posting_id": pid, "channel": channel, "event": event,
            "event_date": day}


PROFILE = dict(make_data.PROFILE)


class TestHandMade(unittest.TestCase):
    def test_sponsorship_stated(self):
        self.assertEqual(m.sponsorship_stated("We are UNABLE to sponsor visas."), "no", "case does not matter")
        self.assertEqual(m.sponsorship_stated("Visa sponsorship available. You must have the right to work here."),
                         "no", "a posting that says both: the no wins, because it rules you out in its own words")
        self.assertEqual(m.sponsorship_stated("We sponsor visas for this role."), "yes")
        self.assertEqual(m.sponsorship_stated(""), "not_stated", "silence is not a yes")

    def test_red_flags(self):
        self.assertEqual(m.red_flags("Pay a REGISTRATION FEE, then message us on WhatsApp only."),
                         ["registration fee", "whatsapp only"], "every phrase found, in RED_FLAGS order, any case")
        self.assertEqual(m.red_flags("Analyse funnels."), [], "no red flag: an empty list")

    def test_is_eligible(self):
        cases = [
            (posting("a", "Data Analyst", city="Remote", mode="remote", regions=""), False,
             "remote with no country named is not open to you until the listing says so"),
            (posting("b", "Data Analyst", city="Remote", country="US", mode="remote", regions="US"), False,
             "remote, US only"),
            (posting("c", "Data Analyst", city="Remote", country="SG", mode="remote", regions="APAC"), True,
             "remote, APAC includes India"),
            (posting("d", "Data Analyst", city="Remote", country="GB", mode="remote", regions="GB;IN"), True,
             "remote, one of the named countries is India"),
            (posting("e", "Data Analyst", city="Pune"), True, "on site in one of her cities"),
            (posting("f", "Data Analyst", city="Hyderabad"), False, "Hyderabad is not one of her cities"),
            (posting("g", "Data Analyst", city="London", country="GB", mode="onsite"), False,
             "abroad with sponsorship not stated: she needs a visa, so not stated is a no"),
            (posting("h", "Data Analyst", city="London", country="GB", mode="onsite", text="We sponsor visas."), True,
             "abroad, the posting says it sponsors"),
            (posting("i", "Data Analyst", city="London", country="GB", mode="onsite",
                     text="We sponsor visas. Unable to sponsor for this team."), False, "the no wins"),
        ]
        for p, want, why in cases:
            self.assertEqual(m.is_eligible(p, PROFILE), want, "posting %s: %s" % (p["posting_id"], why))

    def test_is_stale(self):
        self.assertFalse(m.is_stale(posting("a", "x", posted="2026-10-03"), PROFILE),
                         "posted exactly 30 days before 2 November: still fresh")
        self.assertTrue(m.is_stale(posting("b", "x", posted="2026-10-02"), PROFILE), "31 days old: stale")
        self.assertTrue(m.is_stale(posting("c", "x", closes="2026-11-01"), PROFILE), "closed the day before the plan")
        self.assertFalse(m.is_stale(posting("d", "x", closes="2026-11-02"), PROFILE), "closes on day 1: still open")

    def test_title_family(self):
        for title, want in [("Senior Business Intelligence Analyst", "bi"), ("Marketing Insights Analyst", "data"),
                            ("BUSINESS ANALYST", "business"), ("Growth Analyst", "product"),
                            ("Financial Analyst", None), ("Data Engineer", None), ("", None)]:
            self.assertEqual(m.title_family(title), want, "title %r: check FAMILY_ORDER and lower case" % title)

    def test_role_key(self):
        a = posting("a", " Data Analyst ", company="Tiffinbell")
        b = posting("b", "data analyst", company="TIFFINBELL ")
        self.assertEqual(m.role_key(a), m.role_key(b), "case and spaces do not make a new role")

    def test_usable_postings(self):
        postings = [posting("P0001", "Data Analyst", posted="2026-10-20"),
                    posting("P0002", "Data Analyst", posted="2026-10-28"),           # repost of P0001: keep this
                    posting("P0003", "Product Analyst", city="Mumbai", company="B"),
                    posting("P0004", "Product Analyst", city="Mumbai", company="B"),  # tie: keep P0003
                    posting("P0005", "BI Analyst", company="C"),
                    posting("P0006", "BI Analyst", company="C", posted="2026-11-01"),  # repost of a role in the log
                    posting("P0007", "Financial Analyst", company="D"),              # not a target family
                    posting("P0008", "Reporting Analyst", company="E", text="Guaranteed job after training.")]
        log = [ev("A1", "P0005", "applied", "2026-10-27")]
        got = [p["posting_id"] for p in m.usable_postings(postings, log, PROFILE)]
        self.assertEqual(got, ["P0002", "P0003"],
                         "one per role (newest, then smallest id), and a role already in the log is not usable "
                         "under any id")
        self.assertEqual(m.usable_postings([], [], PROFILE), [], "no postings: an empty list")

    def test_funnel_hand_made(self):
        log = [ev("A1", "P1", "applied", "2026-10-26", "referral"),
               ev("A1", "P1", "phone_screen", "2026-10-27", "referral"),
               ev("A1", "P1", "phone_screen", "2026-10-27", "referral"),  # typed twice
               ev("A2", "P2", "applied", "2026-10-26"),
               ev("A2", "P2", "applied", "2026-10-26"),
               ev("A3", "P3", "applied", "2026-10-29"),
               ev("A3", "P3", "screen", "2026-10-30"),
               ev("A3", "P3", "rejected", "2026-10-31"),
               ev("A4", "P4", "applied", "2026-10-30", "")]
        assert_funnel(self, m.funnel(log), ref_funnel(log), "hand-made log")
        f = m.funnel(log)
        self.assertEqual((f["applications"], f["screens"]), (4, 2),
                         "4 applications, 2 reached a screen (phone_screen and screen are the same stage)")
        self.assertIn("unknown", f["by_channel"], "a blank channel is 'unknown'")
        empty = m.funnel([])
        self.assertEqual(empty["applications"], 0)
        self.assertIsNone(empty["response_rate"], "no applications: rates are None, not a division by zero")
        self.assertEqual(empty["by_channel"], {})
        no_screen = m.funnel([ev("A1", "P1", "applied", "2026-10-26")])
        self.assertEqual(no_screen["screen_rate"], 0.0)
        self.assertIsNone(no_screen["interview_rate"], "no screens: interview_rate is None")

    def test_weekly_hours(self):
        plan = {"tasks": [{"date": "2026-11-02", "week": 1, "kind": "apply", "hours": 1.5},
                          {"date": "2026-11-03", "week": 1, "kind": "review", "hours": 1.0},
                          {"date": "2026-11-10", "week": 2, "kind": "search", "hours": 0.5}]}
        self.assertEqual(m.weekly_hours(plan), {1: 2.5, 2: 0.5})
        self.assertEqual(m.weekly_hours({"tasks": []}), {})


class TestPlanProblems(unittest.TestCase):
    """A two-week world small enough to read, a valid plan, and one broken copy per rule."""

    def setUp(self):
        self.prof = dict(PROFILE, plan_days=14, hours_per_week=6)
        self.postings = [
            posting("A", "Data Analyst", company="Ann"),
            posting("B", "Product Analyst", city="Remote", mode="remote", regions="IN", company="Bee"),
            posting("C", "BI Analyst", city="London", country="GB", mode="onsite", text="We sponsor visas.",
                    company="Cee"),
            posting("D", "Data Analyst", city="Austin", country="US", mode="onsite", company="Dee"),
            posting("E", "Business Analyst", posted="2026-09-20", company="Eee"),
            posting("F", "Operations Analyst", text="A security deposit applies.", company="Eff"),
            posting("G", "Financial Analyst", company="Gee"),
            posting("I", "Growth Analyst", closes="2026-11-05", company="Eye"),
            posting("X", "Reporting Analyst", city="Mumbai", posted="2026-10-20", company="Ex"),
            posting("X2", "Reporting Analyst", city="Mumbai", posted="2026-11-01", company="Ex"),
        ]
        self.log = [ev("A1", "X", "applied", "2026-10-27", "careers_page"),
                    ev("A1", "X", "screen", "2026-10-30", "careers_page")]
        terms = [w for _, ws in FAMILIES for w in ws]

        def t(day, kind, **extra):
            out = {"date": day, "week": (d(day) - d("2026-11-02")).days // 7 + 1, "kind": kind,
                   "hours": MIN_HOURS[kind], "note": ""}
            out.update(extra)
            return out
        self.t = t
        self.plan = {"seeker": "Kavya Menon", "start": "2026-11-02", "end": "2026-11-15", "hours_per_week": 6,
                     "search_terms": terms,
                     "tasks": [t("2026-11-02", "review", funnel=ref_funnel(self.log)),
                               t("2026-11-03", "apply", posting_id="A"),
                               t("2026-11-04", "apply", posting_id="B"),
                               t("2026-11-05", "apply", posting_id="I"),
                               t("2026-11-09", "review", funnel=None),
                               t("2026-11-10", "apply", posting_id="C")]}

    def problems(self, plan):
        return m.plan_problems(plan, self.postings, self.log, self.prof)

    def broken(self, code, change):
        plan = copy.deepcopy(self.plan)
        change(plan)
        self.assertEqual(self.problems(plan), [code],
                         "this plan breaks exactly one rule, so plan_problems should return [%r]" % code)

    def test_valid_plan(self):
        self.assertEqual(self.problems(self.plan), [], "a plan that keeps every rule has no problems")

    def test_each_rule(self):
        t = self.t
        self.broken("window", lambda p: p["tasks"].append(dict(t("2026-11-01", "search"), week=0)))
        self.broken("window", lambda p: p.update(end="2026-11-30"))
        self.broken("week", lambda p: p["tasks"][1].update(week=2))
        self.broken("hours", lambda p: p["tasks"].append(t("2026-11-06", "skill")))
        self.broken("task_hours", lambda p: p["tasks"][1].update(hours=0.5))
        self.broken("task_hours", lambda p: p["tasks"].append(dict(t("2026-11-11", "search"), kind="daydream")))
        self.broken("ineligible", lambda p: p["tasks"].append(t("2026-11-11", "apply", posting_id="D")))
        self.broken("ineligible", lambda p: p["tasks"].append(t("2026-11-11", "apply", posting_id="NOPE")))
        self.broken("stale", lambda p: p["tasks"].append(t("2026-11-11", "apply", posting_id="E")))
        self.broken("stale", lambda p: p["tasks"][3].update(date="2026-11-06"))
        self.broken("red_flag", lambda p: p["tasks"].append(t("2026-11-11", "apply", posting_id="F")))
        self.broken("not_target", lambda p: p["tasks"].append(t("2026-11-11", "apply", posting_id="G")))
        self.broken("duplicate", lambda p: p["tasks"].append(t("2026-11-11", "apply", posting_id="X2")))
        self.broken("duplicate", lambda p: p["tasks"].append(t("2026-11-11", "apply", posting_id="A")))
        self.broken("volume", lambda p: p["tasks"].pop(5))
        self.broken("coverage", lambda p: p["search_terms"].remove("growth analyst"))
        self.broken("coverage", lambda p: p["search_terms"].append("analyst"))
        self.broken("review", lambda p: p["tasks"].pop(4))
        self.broken("funnel", lambda p: p["tasks"][0]["funnel"].update(screens=2))
        self.broken("funnel", lambda p: p["tasks"][0].update(funnel=None))


class OnDataMixin:
    @classmethod
    def setUpClass(cls):
        raw = cls.get_raw()
        cls.postings, cls.log, cls.prof = raw["postings"], raw["app_log"], raw["profile"]
        cls.by_id = dict((p["posting_id"], p) for p in cls.postings)
        cls.usable = ref_usable(cls.postings, cls.log, cls.prof)
        cls.plan = m.build_plan(copy.deepcopy(cls.postings), copy.deepcopy(cls.log), dict(cls.prof))
        cls.start = d(cls.prof["plan_start"])
        cls.end = cls.start + timedelta(days=cls.prof["plan_days"] - 1)

    def applies(self):
        return [t for t in self.plan["tasks"] if t["kind"] == "apply"]

    def test_usable_postings(self):
        got = sorted(p["posting_id"] for p in m.usable_postings(self.postings, self.log, self.prof))
        self.assertEqual(got, self.usable, "usable postings: eligible, fresh, no red flag, target family, "
                                           "one per role, and not a role already in the log")

    def test_funnel(self):
        assert_funnel(self, m.funnel(self.log), ref_funnel(self.log), "first-week log")

    def test_plan_is_json(self):
        json.loads(json.dumps(self.plan))
        for k in ("seeker", "start", "end", "hours_per_week", "search_terms", "tasks"):
            self.assertIn(k, self.plan, "the plan needs the key %r (see DELIVERABLES.md)" % k)

    def test_dates_inside_30_days(self):
        self.assertEqual((self.plan["start"], self.plan["end"]), (self.start.isoformat(), self.end.isoformat()),
                         "30 days means start + 29 days: 2 November to 1 December")
        for t in self.plan["tasks"]:
            day = d(t["date"])
            self.assertTrue(self.start <= day <= self.end, "task on %s is outside the 30 days" % t["date"])
            self.assertEqual(t["week"], (day - self.start).days // 7 + 1, "task on %s has the wrong week" % t["date"])

    def test_hours_within_budget(self):
        used = {}
        for t in self.plan["tasks"]:
            self.assertIn(t["kind"], MIN_HOURS, "unknown task kind %r" % t["kind"])
            self.assertGreaterEqual(t["hours"], MIN_HOURS[t["kind"]],
                                    "a %s task takes at least %s hours (BRIEF.md time card)" % (t["kind"], MIN_HOURS[t["kind"]]))
            used[t["week"]] = used.get(t["week"], 0) + t["hours"]
        for w, h in used.items():
            days = min(7, self.prof["plan_days"] - 7 * (w - 1))
            budget = self.prof["hours_per_week"] * days / 7
            self.assertLessEqual(h, budget + 1e-9, "week %d plans %.2f hours, over the budget of %.2f" % (w, h, budget))
        self.assertEqual(m.weekly_hours(self.plan), dict((w, h) for w, h in used.items()) or {},
                         "weekly_hours should add up hours per week")

    def test_every_application_is_allowed(self):
        applied_roles = set(key(self.by_id[r["posting_id"]]) for r in self.log)
        roles = []
        for t in self.applies():
            p = self.by_id.get(t.get("posting_id"))
            self.assertIsNotNone(p, "apply task points at an unknown posting_id %r" % t.get("posting_id"))
            pid = p["posting_id"]
            self.assertTrue(ref_eligible(p, self.prof), "%s: Kavya cannot be hired for it (visa or remote rule)" % pid)
            self.assertTrue(ref_fresh(p, self.prof), "%s is stale or closed before the plan starts" % pid)
            self.assertTrue(p["closes_on"] == "" or t["date"] <= p["closes_on"], "%s is applied to after it closes" % pid)
            self.assertTrue(ref_clean(p), "%s has a red flag in its description" % pid)
            self.assertIn(ref_family(p["title"]), self.prof["target_families"], "%s is not a target role" % pid)
            self.assertNotIn(key(p), applied_roles, "%s is a role she applied to last week (maybe under another id)" % pid)
            roles.append(key(p))
        self.assertEqual(len(roles), len(set(roles)), "two applications to the same role (a repost)")
        self.assertGreaterEqual(len(roles), min(16, len(self.usable)),
                                "the plan needs at least 16 applications (or every usable posting if fewer)")

    def test_search_terms_cover_the_families(self):
        terms = [s.lower() for s in self.plan["search_terms"]]
        fam_of = dict((w, f) for f, ws in FAMILIES for w in ws if f in self.prof["target_families"])
        for s in terms:
            self.assertIn(s, fam_of, "search term %r is not a synonym of a target family" % s)
        for f in self.prof["target_families"]:
            self.assertGreaterEqual(len(set(s for s in terms if fam_of[s] == f)), 2,
                                    "family %r needs at least two search terms" % f)
        for pid in self.usable:
            title = self.by_id[pid]["title"].lower()
            self.assertTrue(any(s in title for s in terms), "no search term finds %s (%s)" % (pid, title))

    def test_weekly_review_with_correct_funnel(self):
        reviews = sorted((t for t in self.plan["tasks"] if t["kind"] == "review"), key=lambda t: t["date"])
        for w in range(1, self.prof["plan_days"] // 7 + 1):
            self.assertTrue(any(t["week"] == w for t in reviews), "week %d has no review task" % w)
        assert_funnel(self, reviews[0].get("funnel"), ref_funnel(self.log), "the first review's baseline funnel")

    def test_plan_problems_agrees(self):
        self.assertEqual(m.plan_problems(self.plan, self.postings, self.log, self.prof), [],
                         "your plan passes the checker, so plan_problems should return []")
        bad = copy.deepcopy(self.plan)
        wrong = [p for p in self.postings if p["work_mode"] == "remote" and p["remote_regions"] == ""][0]
        bad["tasks"].append({"date": self.plan["end"], "week": (self.end - self.start).days // 7 + 1,
                             "kind": "apply", "hours": 0.25, "note": "", "posting_id": wrong["posting_id"]})
        got = m.plan_problems(bad, self.postings, self.log, self.prof)
        self.assertIn("ineligible", got, "a remote posting with no country named is not eligible")
        self.assertIn("task_hours", got, "an application takes 1.5 hours, not 0.25")


class TestOnData(OnDataMixin, unittest.TestCase):
    @staticmethod
    def get_raw():
        out = {}
        for name in ("postings", "app_log"):
            with open(os.path.join(DATA, name + ".csv"), newline="") as f:
                out[name] = list(csv.DictReader(f))
        with open(os.path.join(DATA, "profile.json")) as f:
            out["profile"] = json.load(f)
        return out

    @unittest.skipUnless(SOLUTION or os.path.exists(PLAN_FILE), "no plan.json yet: run python3 exercise.py")
    def test_saved_plan_file(self):
        with open(PLAN_FILE) as f:
            saved = json.load(f)
        self.assertEqual(saved, json.loads(json.dumps(self.plan)),
                         "plan.json is out of date: run the file again to rewrite it from build_plan")


class TestOnSecondDataset(OnDataMixin, unittest.TestCase):
    """Same checks on data built with another seed, so a typed-in plan fails."""

    @staticmethod
    def get_raw():
        return make_data.build(seed=OTHER_SEED)


if __name__ == "__main__":
    unittest.main()
