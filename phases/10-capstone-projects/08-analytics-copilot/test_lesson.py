"""Checker for capstone 10-08. Default: checks exercise.py. With CHECK_SOLUTION=1: solution/solution.py.

What it checks, all against answers worked out here, not read from the solution:
- the clean rentals, rebuilt here a second way, on the committed data and on a second city (seed 2008);
- plan validation, the reconciliation, the permutation test and the claim checker on hand-made cases;
- the permutation p-value against an exact count of subset sums and a seeded simulation;
- the replayed session on both datasets: every step's status, the SQL fingerprint of the edited step,
  each query's rows against plain Python over the clean rentals, the checks, every claim's verdict
  (against the answer key make_data.build() keeps in memory) and the release decision;
- what the orchestrator does when an approval is missing, a step is rejected, an approved step
  reads personal data, the step budget runs out, or the plan is invalid.
The database file is hashed before and after, so a step that writes fails.
"""
import copy
import csv
import datetime
import hashlib
import importlib.util
import json
import math
import os
import random
import shutil
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load_module("submission", TARGET)
make_data = load_module("make_data_10_08", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 2008
SNAPSHOT = "2026-10-01 00:00:00"
EXPECTED_STATUS = {"S1": "done", "S2": "done", "S3": "done", "S4": "done", "S5": "rejected",
                   "S6": "done", "S7": "done", "S8": "done"}


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def committed():
    out = {}
    for name in ("stations", "station_events", "riders", "rentals_raw", "approvals"):
        with open(os.path.join(HERE, "data", name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    for name in ("plan", "draft"):
        with open(os.path.join(HERE, "data", name + ".json")) as f:
            out[name] = json.load(f)
    return out


def reference_rentals(raw):
    """A second way: sort loads by time, later overwrite earlier, then drop rentals under 2 minutes."""
    latest = {}
    for r in sorted(raw, key=lambda r: r["loaded_at"]):
        if r["loaded_at"] < SNAPSHOT:
            latest[int(r["rental_id"])] = r
    return [(k, latest[k]["station_id"], latest[k]["start_date"], int(latest[k]["duration_min"]))
            for k in sorted(latest) if int(latest[k]["duration_min"]) >= 2]


def weekend(date_text):
    return datetime.date.fromisoformat(date_text).weekday() >= 5


def exact_p_by_sums(a, b):
    """Exact permutation p from the distribution of subset sums (dynamic programming, no enumeration)."""
    pooled = list(a) + list(b)
    n, k, total = len(pooled), len(a), sum(pooled)
    ways = [dict() for _ in range(k + 1)]
    ways[0][0] = 1
    for x in pooled:
        for size in range(k, 0, -1):
            for s, w in list(ways[size - 1].items()):
                ways[size][s + x] = ways[size].get(s + x, 0) + w
    observed = abs(sum(a) / len(a) - sum(b) / len(b))
    hits = sum(w for s, w in ways[k].items() if abs(s / k - (total - s) / (n - k)) >= observed - 1e-9)
    return hits / math.comb(n, k)


def simulated_p(a, b, sims=20000, seed=11):
    rng = random.Random(seed)
    pooled = list(a) + list(b)
    observed = abs(sum(a) / len(a) - sum(b) / len(b))
    hits = 0
    for _ in range(sims):
        rng.shuffle(pooled)
        x, y = pooled[:len(a)], pooled[len(a):]
        hits += abs(sum(x) / len(x) - sum(y) / len(y)) >= observed - 1e-9
    return hits / sims


class TestData(unittest.TestCase):
    def test_committed_data_matches_the_default_seed(self):
        built = make_data.build(make_data.DEFAULT_SEED)
        data = committed()
        for name in ("stations", "station_events", "riders", "rentals_raw", "approvals"):
            self.assertEqual(data[name], [{k: str(v) for k, v in r.items()} for r in built[name]],
                             "data/%s.csv differs from make_data.build(): run python3 make_data.py" % name)
        self.assertEqual(data["plan"], built["plan"])
        self.assertEqual(data["draft"], built["draft"])


class TestClean(unittest.TestCase):
    def check(self, raw, label):
        got = lesson.clean_rentals(raw)
        want = reference_rentals(raw)
        self.assertEqual(len(got), len(want), "%s: expected %d clean rentals: loads before %s, latest load per rental_id, at least 2 minutes" % (label, len(want), SNAPSHOT))
        self.assertEqual([(r["rental_id"], r["station_id"], r["start_date"], r["duration_min"]) for r in got], want,
                         "%s: the clean rentals differ from the reference" % label)

    def test_committed(self):
        self.check(committed()["rentals_raw"], "committed data")

    def test_second_city(self):
        self.check(make_data.build(OTHER_SEED)["rentals_raw"], "seed %d" % OTHER_SEED)

    def test_hand_made(self):
        base = {"station_id": "BQ01", "start_date": "2026-08-20", "start_hour": "9", "rider_type": "casual", "rider_id": "4"}
        raw = [dict(base, rental_id="1", duration_min="1", loaded_at="2026-08-21 01:00:00"),
               dict(base, rental_id="2", duration_min="2", loaded_at="2026-08-21 01:00:00"),
               dict(base, rental_id="3", duration_min="15", loaded_at="2026-10-01 00:00:00"),
               dict(base, rental_id="4", duration_min="1", loaded_at="2026-08-21 01:00:00"),
               dict(base, rental_id="4", duration_min="12", loaded_at="2026-08-22 04:00:00")]
        got = lesson.clean_rentals(raw)
        self.assertEqual([r["rental_id"] for r in got], [2, 4],
                         "1 minute is a false start, 2 minutes counts, a load at the snapshot time is out, the latest load wins")
        self.assertEqual(got[1]["duration_min"], 12)
        self.assertEqual(lesson.clean_rentals([]), [], "no rows in, no rows out")


class TestPlan(unittest.TestCase):
    def test_fixture_plan_is_valid(self):
        self.assertEqual(lesson.validate_plan(committed()["plan"]), ["S%d" % i for i in range(1, 9)])

    def test_invalid_plans(self):
        plan = committed()["plan"]
        bad = []
        p = copy.deepcopy(plan); p[1]["step"] = "S1"; bad.append((p, "a repeated step id"))
        p = copy.deepcopy(plan); p[0]["kind"] = "email"; bad.append((p, "an unknown kind"))
        p = copy.deepcopy(plan); p[0]["depends_on"] = ["S6"]; bad.append((p, "a dependency on a later step"))
        p = copy.deepcopy(plan); p[5]["depends_on"] = ["S1", "S99"]; bad.append((p, "an unknown dependency"))
        p = copy.deepcopy(plan); p[2]["sql"] = "  "; bad.append((p, "a query with no SQL"))
        p = copy.deepcopy(plan); p[6]["check"] = "vibes"; bad.append((p, "a check that does not exist"))
        for p, why in bad:
            with self.assertRaises(ValueError, msg="validate_plan should reject a plan with %s" % why):
                lesson.validate_plan(p)
        self.assertEqual(lesson.validate_plan([]), [], "an empty plan is valid and has no steps")


class TestChecks(unittest.TestCase):
    def test_reconcile(self):
        totals = [{"month": "2026-07", "rentals": 5, "days": 2}, {"month": "2026-08", "rentals": 10, "days": 2},
                  {"month": "2026-09", "rentals": 7, "days": 2}]
        zones = [{"zone": "A", "month": "2026-08", "rentals": 6}, {"zone": "B", "month": "2026-08", "rentals": 4},
                 {"zone": "A", "month": "2026-09", "rentals": 5}]
        got = lesson.reconcile(totals, zones)
        self.assertEqual(got["diffs"], {"2026-08": 0, "2026-09": -2}, "diffs are zone sum minus total, for August and September only")
        self.assertFalse(got["passed"])
        zones.append({"zone": "B", "month": "2026-09", "rentals": 2})
        self.assertTrue(lesson.reconcile(totals, zones)["passed"])
        self.assertEqual(lesson.reconcile([], [], months=("2026-08",)), {"passed": True, "diffs": {"2026-08": 0}})

    def test_permutation_p(self):
        self.assertAlmostEqual(lesson.permutation_p([1, 2], [3, 4]), 2 / 6, msg="of 6 splits, 2 are as far apart as 1,2 against 3,4")
        self.assertEqual(lesson.permutation_p([5, 5, 5], [5, 5]), 1.0, "no difference at all: p is 1")
        self.assertEqual(lesson.permutation_p([], [1, 2]), 1.0, "an empty group: p is 1")
        for a, b in [([3, 9, 4, 8], [1, 2, 2]), ([20, 18, 25, 19, 22], [17, 16, 21, 15]), ([0, 0, 1], [3])]:
            self.assertAlmostEqual(lesson.permutation_p(a, b), exact_p_by_sums(a, b), places=12,
                                   msg="permutation_p(%r, %r) should be the exact share of splits" % (a, b))

    def test_noise_check(self):
        rows = [{"start_date": "2026-08-01", "month": "2026-08", "rentals": 10},
                {"start_date": "2026-08-02", "month": "2026-08", "rentals": 14},
                {"start_date": "2026-09-05", "month": "2026-09", "rentals": 9}]
        got = lesson.noise_check(rows)
        self.assertEqual((got["n_aug"], got["n_sep"]), (2, 1))
        self.assertAlmostEqual(got["mean_aug"], 12.0)
        self.assertAlmostEqual(got["mean_sep"], 9.0)
        self.assertAlmostEqual(got["p_value"], exact_p_by_sums([10, 14], [9]))
        self.assertTrue(got["passed"])
        self.assertFalse(lesson.noise_check(rows[:2])["passed"], "with no September days the check cannot pass")


class TestClaims(unittest.TestCase):
    def setUp(self):
        self.results = {"S1": [{"month": "2026-08", "rentals": 1234, "days": 10}, {"month": "2026-09", "rentals": 900, "days": 8}],
                        "S3": [{"zone": "Riverside"}, {"zone": "Riverside"}, {"zone": "Harbour"}],
                        "S7": [{"mean_aug": 20.0, "mean_sep": 21.0, "p_value": 0.4321}]}
        self.status = {"S1": "done", "S3": "done", "S5": "rejected", "S7": "done"}
        aug, sep = {"month": "2026-08"}, {"month": "2026-09"}
        self.draft = {"text": "From 1,234 to 900, down 27.1%, per day 123.4 to 112.0; 2 closed; +5.0%; p = 0.43; "
                              "40 riders; 2.3% wrong; 7 extra; a 10% discount; 99 lost",
                      "claims": [
                          {"id": "C1", "text": "1,234", "kind": "value", "step": "S1", "where": aug, "expr": "rentals"},
                          {"id": "C2", "text": "900", "kind": "value", "step": "S1", "where": sep, "expr": "rentals"},
                          {"id": "C3", "text": "27.1%", "kind": "pct_fall", "from": {"step": "S1", "where": aug, "expr": "rentals"},
                           "to": {"step": "S1", "where": sep, "expr": "rentals"}},
                          {"id": "C4", "text": "123.4", "kind": "value", "step": "S1", "where": aug, "expr": "rentals / days"},
                          {"id": "C5", "text": "112.0", "kind": "value", "step": "S1", "where": sep, "expr": "rentals / days"},
                          {"id": "C6", "text": "2", "kind": "count", "step": "S3", "where": {"zone": "Riverside"}},
                          {"id": "C7", "text": "+5.0%", "kind": "pct_change", "from": {"step": "S7", "where": {}, "expr": "mean_aug"},
                           "to": {"step": "S7", "where": {}, "expr": "mean_sep"}},
                          {"id": "C8", "text": "0.43", "kind": "value", "step": "S7", "where": {}, "expr": "p_value"},
                          {"id": "C9", "text": "40", "kind": "count", "step": "S5", "where": {}},
                          {"id": "C10", "text": "2.3%", "kind": "pct_change", "from": {"step": "S1", "where": aug, "expr": "rentals"},
                           "to": {"step": "S1", "where": sep, "expr": "rentals"}},
                          {"id": "C11", "text": "7", "kind": "value", "step": "S1", "where": {"month": "2026-07"}, "expr": "rentals"},
                          {"id": "C12", "text": "10%", "kind": "assumption"},
                      ]}

    def test_verdicts(self):
        got = lesson.check_claims(self.draft, self.results, self.status)
        want = {"C1": "ok", "C2": "ok", "C3": "ok", "C4": "ok", "C5": "mismatch", "C6": "ok", "C7": "ok", "C8": "ok",
                "C9": "not_run", "C10": "mismatch", "C11": "no_such_row", "C12": "assumption"}
        for cid, verdict in want.items():
            self.assertEqual(got["verdicts"].get(cid), verdict, "claim %s (%s) should be %s" % (
                cid, self.draft["claims"][int(cid[1:]) - 1]["text"], verdict))
        self.assertEqual(got["uncited"], ["99"], "99 is in the text but no claim backs it")

    def test_precision(self):
        claim = {"id": "C1", "text": "49.7%", "kind": "value", "step": "S7", "where": {}, "expr": "p_value"}
        for actual, verdict in [(49.66, "ok"), (49.74, "ok"), (49.76, "mismatch"), (49.6, "mismatch")]:
            got = lesson.check_claims({"text": "49.7%", "claims": [claim]}, {"S7": [{"p_value": actual}]}, {"S7": "done"})
            self.assertEqual(got["verdicts"]["C1"], verdict, "49.7%% stated to 1 decimal against %s should be %s" % (actual, verdict))


class TestRelease(unittest.TestCase):
    def test_release(self):
        plan = [{"step": "S1", "kind": "query"}, {"step": "S6", "kind": "check"}, {"step": "S7", "kind": "check"}]
        good = {"verdicts": {"C1": "ok", "C2": "assumption"}, "uncited": []}
        ok_results = {"S6": [{"passed": True}], "S7": [{"passed": True}]}
        all_done = {"S1": "done", "S6": "done", "S7": "done"}
        self.assertEqual(lesson.release(plan, all_done, ok_results, good), {"released": True, "reasons": []})
        cases = [
            (all_done, {"S6": [{"passed": False}], "S7": [{"passed": True}]}, good, 1),
            (dict(all_done, S7="skipped"), {"S6": [{"passed": True}]}, good, 1),
            (all_done, ok_results, {"verdicts": {"C1": "mismatch", "C2": "not_run"}, "uncited": ["15%"]}, 3),
        ]
        for status, results, report, n in cases:
            got = lesson.release(plan, status, results, report)
            self.assertFalse(got["released"], "release must refuse when a check failed or did not run, or a claim is not ok")
            self.assertEqual(len(got["reasons"]), n, "one reason per problem: %r" % got["reasons"])


class SessionCase(unittest.TestCase):
    seed = None

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="w6-cap-c-1008-")
        cls.data = committed() if cls.seed is None else make_data.build(cls.seed)
        cls.key = make_data.build(make_data.DEFAULT_SEED if cls.seed is None else cls.seed)["key"]
        cls.path = os.path.join(cls.tmp, "bramblequay.db")
        lesson.build_db(cls.path, cls.data)
        cls.hash = file_hash(cls.path)
        cls.label = "committed data" if cls.seed is None else "seed %d" % cls.seed
        zone = {s["station_id"]: s["zone"] for s in cls.data["stations"]}
        rentals = reference_rentals(cls.data["rentals_raw"])
        wk = [r for r in rentals if weekend(r[2])]
        cls.s1 = {}
        for m in sorted({r[2][:7] for r in wk}):
            cls.s1[m] = (sum(1 for r in wk if r[2][:7] == m), len({r[2] for r in wk if r[2][:7] == m}))
        cls.s2 = {}
        for r in wk:
            if r[1] in zone and r[2] >= "2026-08-01":
                cls.s2[(zone[r[1]], r[2][:7])] = cls.s2.get((zone[r[1]], r[2][:7]), 0) + 1
        cls.s4 = {}
        for r in wk:
            if zone.get(r[1]) not in (None, "Riverside") and r[2] >= "2026-08-01":
                cls.s4[r[2]] = cls.s4.get(r[2], 0) + 1
        cls.fri_sat = {}
        for r in rentals:
            if datetime.date.fromisoformat(r[2]).weekday() in (4, 5) and zone.get(r[1]) not in (None, "Riverside") and r[2] >= "2026-08-01":
                cls.fri_sat[r[2]] = cls.fri_sat.get(r[2], 0) + 1

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def replay(self, approvals=None, plan=None, max_steps=8):
        run = lesson.run_plan(plan or self.data["plan"], approvals if approvals is not None else self.data["approvals"],
                              self.path, self.data["draft"], max_steps=max_steps)
        self.assertEqual(file_hash(self.path), self.hash, "%s: the database file changed during the session" % self.label)
        self.assertEqual([e["step"] for e in run["log"]], [s["step"] for s in (plan or self.data["plan"])],
                         "the log has one entry per plan step, in plan order")
        return run


class SessionMixin(object):
    def test_session(self):
        run = self.replay()
        L = self.label
        self.assertEqual(run["status"], EXPECTED_STATUS, "%s: step statuses" % L)
        log = {e["step"]: e for e in run["log"]}
        edited = [a for a in self.data["approvals"] if a["step"] == "S4"][0]["edited_sql"]
        self.assertEqual(log["S4"]["sql_sha256"], hashlib.sha256(edited.encode("utf-8")).hexdigest(),
                         "%s: S4 must run the reviewer's edited SQL, and the log must fingerprint what ran" % L)
        self.assertEqual(log["S1"]["sql_sha256"], hashlib.sha256(self.data["plan"][0]["sql"].encode("utf-8")).hexdigest())
        self.assertEqual(log["S5"]["sql_sha256"], "", "a rejected step runs no SQL")
        res = run["results"]
        self.assertNotIn("S5", res, "a rejected step has no result")
        self.assertEqual({r["month"]: (r["rentals"], r["days"]) for r in res["S1"]}, self.s1, "%s: S1 weekend rentals and days per month" % L)
        self.assertEqual({(r["zone"], r["month"]): r["rentals"] for r in res["S2"]}, self.s2, "%s: S2 weekend rentals per zone" % L)
        self.assertEqual({r["start_date"]: r["rentals"] for r in res["S4"]}, self.s4, "%s: S4 must count Saturdays and Sundays" % L)
        self.assertEqual(sum(1 for r in res["S3"] if r["zone"] == "Riverside"), 3)
        s6 = res["S6"][0]
        want_diffs = {m: sum(v for (z, mm), v in self.s2.items() if mm == m) - self.s1[m][0] for m in ("2026-08", "2026-09")}
        self.assertEqual(s6["diffs"], want_diffs, "%s: S6 diffs (zone sum minus total)" % L)
        self.assertFalse(s6["passed"], "%s: rentals at a station missing from stations.csv drop out of the zone join, so S6 fails" % L)
        s7 = res["S7"][0]
        aug = [v for d, v in sorted(self.s4.items()) if d[:7] == "2026-08"]
        sep = [v for d, v in sorted(self.s4.items()) if d[:7] == "2026-09"]
        self.assertAlmostEqual(s7["p_value"], exact_p_by_sums(aug, sep), places=9, msg="%s: S7 exact permutation p" % L)
        self.assertAlmostEqual(s7["p_value"], simulated_p(aug, sep), delta=0.015, msg="%s: S7 p should agree with a simulation" % L)
        self.assertAlmostEqual(s7["mean_aug"], sum(aug) / len(aug))
        self.assertAlmostEqual(s7["mean_sep"], sum(sep) / len(sep))
        verdicts = res["S8"]["claims"]["verdicts"]
        for c in self.data["draft"]["claims"]:
            want = self.key.get(c["id"], "ok")
            self.assertEqual(verdicts.get(c["id"]), want, "%s: claim %s (%s) should be %s" % (L, c["id"], c["text"], want))
        self.assertEqual(res["S8"]["claims"]["uncited"], self.key["uncited"], "%s: uncited numbers" % L)
        rel = res["S8"]["release"]
        self.assertFalse(rel["released"], "%s: a failed check and bad claims must stop the release" % L)
        self.assertEqual(len(rel["reasons"]), 4, "%s: four reasons (S6, C3, C13, 15%%), got %r" % (L, rel["reasons"]))


class TestSessionCommitted(SessionMixin, SessionCase):
    def approvals_without(self, step):
        return [a for a in self.data["approvals"] if a["step"] != step]

    def test_missing_approval_halts(self):
        run = self.replay(self.approvals_without("S3"))
        want = {"S1": "done", "S2": "done", "S3": "halted"}
        want.update({s: "not_reached" for s in ("S4", "S5", "S6", "S7", "S8")})
        self.assertEqual(run["status"], want, "no approval for S3: stop there, run nothing after it")

    def test_rejected_dependency_skips(self):
        approvals = [dict(a, decision="reject") if a["step"] == "S1" else a for a in self.data["approvals"]]
        run = self.replay(approvals)
        self.assertEqual((run["status"]["S1"], run["status"]["S6"], run["status"]["S7"], run["status"]["S8"]),
                         ("rejected", "skipped", "done", "skipped"),
                         "S6 and S8 need S1; S7 does not")

    def test_unedited_bug_runs_fridays(self):
        approvals = [dict(a, decision="approve", edited_sql="") if a["step"] == "S4" else a for a in self.data["approvals"]]
        run = self.replay(approvals)
        self.assertEqual({r["start_date"]: r["rentals"] for r in run["results"]["S4"]}, self.fri_sat,
                         "approved without the edit, S4 runs the planner's SQL as written (Friday and Saturday)")

    def test_approved_personal_data_is_blocked(self):
        approvals = [dict(a, decision="approve") if a["step"] == "S5" else a for a in self.data["approvals"]]
        run = self.replay(approvals)
        self.assertEqual(run["status"]["S5"], "blocked", "the gateway blocks riders.email even when a person approved the step")
        log = {e["step"]: e for e in run["log"]}
        self.assertTrue(log["S5"]["sql_sha256"], "a blocked query was still attempted: fingerprint it")
        self.assertEqual(run["results"]["S8"]["claims"]["verdicts"]["C13"], "not_run")

    def test_budget(self):
        run = self.replay(max_steps=3)
        want = {"S1": "done", "S2": "done", "S3": "done", "S4": "halted"}
        want.update({s: "not_reached" for s in ("S5", "S6", "S7", "S8")})
        self.assertEqual(run["status"], want, "with a budget of 3 steps, the fourth step to run halts the session")

    def test_bad_approvals(self):
        bad_edit = [dict(a, edited_sql=" ") if a["step"] == "S4" else a for a in self.data["approvals"]]
        self.assertEqual(self.replay(bad_edit)["status"]["S4"], "halted", "an edit with no SQL halts")
        maybe = [dict(a, decision="maybe") if a["step"] == "S2" else a for a in self.data["approvals"]]
        self.assertEqual(self.replay(maybe)["status"]["S2"], "halted", "an unknown decision halts")
        last_wins = self.data["approvals"] + [dict(self.data["approvals"][4], decision="approve")]
        self.assertEqual(self.replay(last_wins)["status"]["S5"], "blocked", "the last approval record for a step counts")

    def test_invalid_plan(self):
        plan = copy.deepcopy(self.data["plan"])
        plan[0]["depends_on"] = ["S8"]
        with self.assertRaises(ValueError, msg="run_plan must validate the plan first"):
            lesson.run_plan(plan, self.data["approvals"], self.path, self.data["draft"])


class TestSessionSecondCity(SessionMixin, SessionCase):
    seed = OTHER_SEED


if __name__ == "__main__":
    unittest.main()
