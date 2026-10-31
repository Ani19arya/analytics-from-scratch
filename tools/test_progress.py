"""Tests for tools/progress.py. Run from the repo root:

    python3 -B -m unittest discover -s tools -p "test_*.py"

Every test uses a profile in a temp folder, never .learner/ in the repo.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import progress as pr  # noqa: E402

LESSONS = pr.load_lessons()
FAST_LESSON = "00-01"   # the quickest lesson test in the course


def placement_result(counts, track="data-analyst", path=("01-02", "03-05"), skip=(), strong=(), levels=None):
    """A dict shaped like placement.py --json output."""
    areas = dict((a, {"correct": c, "total": t}) for a, (c, t) in counts.items())
    if levels:
        for a, lv in levels.items():
            areas[a]["level"] = lv
    rec = {"track": track, "track_title": track, "beginner": False, "strong_areas": list(strong),
           "start": {"id": path[0]}, "path": [{"id": x} for x in path], "skip": [{"id": x} for x in skip],
           "do_not_skip_yet": []}
    return {"scores": {"areas": areas, "correct": sum(c for c, _ in counts.values()),
                       "total": sum(t for _, t in counts.values()), "results": []},
            "recommendation": rec}


def card(scores, date="2026-10-20", revisit=None):
    c = pr.scorecard_template()
    c["date"] = date
    for r, s in zip(pr.ROUNDS, scores):
        c["rounds"][r]["score"] = s
    if revisit:
        c["rounds"]["sql"]["revisit"] = list(revisit)
    return c


class TempProfile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="w9-progress-")
        self.path = os.path.join(self.dir, "learner", "profile.json")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = pr.main(["--profile", self.path] + list(args))
        return code, out.getvalue()

    def write_json(self, name, data):
        p = os.path.join(self.dir, name)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return p


class TestMapping(unittest.TestCase):
    def test_every_live_lesson_has_one_known_area(self):
        self.assertGreater(len(LESSONS), 100)
        for l in LESSONS:
            self.assertIn(l["area"], pr.AREAS, l["id"])
            self.assertIn(l["level"], pr.LEVELS, l["id"])

    def test_phase_and_skill_rules(self):
        by_id = dict((l["id"], l) for l in LESSONS)
        self.assertEqual(by_id["00-01"]["area"], "foundations")
        self.assertEqual(by_id["00-04"]["area"], "sql")
        self.assertEqual(by_id["00-06"]["area"], "python")
        self.assertEqual(by_id["01-02"]["area"], "sql")
        self.assertEqual(by_id["04-05"]["area"], "dashboards")
        self.assertEqual(by_id["06-07"]["area"], "ai")
        self.assertIn("statistics", by_id["06-07"]["also"])

    def test_every_phase_is_mapped(self):
        self.assertEqual(sorted(set(l["phase"] for l in LESSONS)), sorted(pr.PHASE_AREA))


class TestProfile(TempProfile):
    def test_created_on_first_use_with_schema(self):
        self.assertFalse(os.path.exists(self.path))
        code, out = self.cli("status")
        self.assertEqual(code, 0)
        self.assertIn("Lessons passed: 0 / %d" % len(LESSONS), out)
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(sorted(data), sorted(["version", "created", "track", "fast_track", "placements",
                                               "attempts", "interviews", "notes"]))
        self.assertEqual(data["version"], pr.VERSION)
        self.assertEqual(os.listdir(os.path.dirname(self.path)), ["profile.json"])

    def test_status_counts(self):
        p = pr.new_profile()
        pr.record_attempt(p, "01-01", False, "2026-10-01")
        pr.record_attempt(p, "01-01", True, "2026-10-02")
        pr.record_attempt(p, "01-02", True, "2026-10-02")
        pr.record_attempt(p, "02-01", True, "2026-10-03")
        pr.record_attempt(p, "02-02", True, "2026-10-03", target="solution")  # never counts
        pr.record_attempt(p, "03-01", False, "2026-10-04")
        st = pr.status(p, LESSONS)
        areas = dict((a["area"], a) for a in st["areas"])
        self.assertEqual(st["passed"], 3)
        self.assertEqual(areas["sql"]["passed"], 2)
        self.assertEqual(areas["statistics"]["passed"], 1)
        self.assertEqual(sum(a["total"] for a in st["areas"]), len(LESSONS))
        levels = dict((x["level"], x) for x in st["levels"])
        self.assertEqual(levels["beginner"]["passed"], 3)
        phases = dict((x["phase"], x) for x in st["phases"])
        self.assertEqual(phases["01-sql"]["passed"], 2)
        self.assertEqual(st["in_progress"], ["03-01"])
        self.assertEqual(st["next"]["id"], "03-01")

    def test_next_follows_track_then_roadmap(self):
        p = pr.new_profile()
        pr.record_placement(p, placement_result({"sql": (2, 2), "metrics": (0, 2)}, path=("01-02", "03-05"),
                                                strong=["sql"], skip=["00-01"]), "2026-10-01")
        self.assertEqual(pr.next_lesson(p, LESSONS)[0], "03-05")   # gap area first
        pr.record_attempt(p, "03-05", True, "2026-10-02")
        self.assertEqual(pr.next_lesson(p, LESSONS)[0], "01-02")   # then the strong area's lesson
        pr.record_attempt(p, "01-02", True, "2026-10-02")
        self.assertEqual(pr.next_lesson(p, LESSONS)[0], "00-02")   # roadmap order, skip list respected

    def test_interview_revisit_comes_before_the_track(self):
        p = pr.new_profile()
        pr.record_placement(p, placement_result({"sql": (0, 2)}), "2026-10-01")
        p["interviews"].append(pr.interview_entry(card([2, 3, 3, 3], revisit=["01-03"]), LESSONS))
        self.assertEqual(pr.next_lesson(p, LESSONS)[0], "01-03")


class TestRecording(TempProfile):
    def test_placement_from_file_keeps_levels_and_sets_track(self):
        f = self.write_json("result.json", placement_result({"sql": (1, 2), "ai": (3, 3)}, track="bi-analyst",
                                                            levels={"sql": "intermediate"}))
        code, out = self.cli("placement", "--from", f, "--date", "2026-09-01")
        self.assertEqual(code, 0, out)
        p = pr.load_profile(self.path)
        self.assertEqual(p["track"], "bi-analyst")
        self.assertEqual(p["placements"][0]["areas"]["sql"], {"correct": 1, "total": 2, "level": "intermediate"})
        self.assertEqual(p["placements"][0]["date"], "2026-09-01")
        self.assertEqual(p["fast_track"]["path"], ["01-02", "03-05"])

    def test_placement_answers_runs_placement_json(self):
        answers = self.write_json("a.json", {"track": "interview-prep", "answers": {}})
        code, out = self.cli("placement", "--answers", answers)
        self.assertEqual(code, 0, out)
        entry = pr.load_profile(self.path)["placements"][0]
        self.assertEqual(entry["track"], "interview-prep")
        self.assertEqual(entry["correct"], 0)
        self.assertTrue(set(pr.PLACEMENT_AREAS) <= set(entry["areas"]))

    def test_bad_placement_is_refused(self):
        f = self.write_json("bad.json", {"track": "x"})
        code, _ = self.cli("placement", "--from", f)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.path))

    def test_interview_schema_and_rubric_rule(self):
        e = pr.interview_entry(card([3, 3, 3, 2]), LESSONS)
        self.assertEqual(e["overall"], "pass")
        self.assertEqual(pr.interview_entry(card([4, 4, 4, 1]), LESSONS)["overall"], "not yet")
        self.assertEqual(pr.interview_entry(card([3, 3, 2, 2]), LESSONS)["overall"], "not yet")
        bad = card([5, 3, 3, 3])
        self.assertRaises(pr.ProgressError, pr.interview_entry, bad, LESSONS)
        nudged = card([3, 3, 3, 3])
        nudged["rounds"]["sql"]["nudges"] = "2+"
        self.assertRaises(pr.ProgressError, pr.interview_entry, nudged, LESSONS)
        wrong = card([3, 3, 3, 3])
        wrong["overall"] = "not yet"
        self.assertRaises(pr.ProgressError, pr.interview_entry, wrong, LESSONS)
        self.assertRaises(pr.ProgressError, pr.interview_entry, card([3, 3, 3, 3], revisit=["99-99"]), LESSONS)
        missing = card([3, 3, 3, 3])
        del missing["rounds"]["behavioural"]
        self.assertRaises(pr.ProgressError, pr.interview_entry, missing, LESSONS)

    def test_interview_cli(self):
        code, out = self.cli("interview", "--template")
        self.assertEqual(sorted(json.loads(out)["rounds"]), sorted(pr.ROUNDS))
        f = self.write_json("card.json", card([3, 2, 4, 3], revisit=["01-02"]))
        code, out = self.cli("interview", "--from", f)
        self.assertEqual(code, 0, out)
        i = pr.load_profile(self.path)["interviews"][0]
        self.assertEqual(i["rounds"]["metrics-case"]["score"], 4)
        self.assertEqual(i["revisit"], ["01-02"])

    def test_check_runs_the_exercise_and_records_it(self):
        ldir = os.path.join(pr.ROOT, next(l["path"] for l in LESSONS if l["id"] == FAST_LESSON))
        cache = os.path.join(ldir, "__pycache__")
        had_cache = os.path.isdir(cache)   # run_all_tests.py may have left one; -B must not add one
        code, out = self.cli("check", FAST_LESSON, "--quiet", "--date", "2026-10-01")
        self.assertEqual(code, 1, out)   # exercises fail as shipped
        code, out = self.cli("check", FAST_LESSON, "--quiet", "--use-solution", "--date", "2026-10-02")
        self.assertEqual(code, 0, out)
        p = pr.load_profile(self.path)
        self.assertEqual([(a["passed"], a["target"]) for a in p["attempts"]],
                         [(False, "exercise"), (True, "solution")])
        self.assertEqual(pr.passed_lessons(p), {})   # the solution never counts as the learner's pass
        if not had_cache:
            self.assertFalse(os.path.isdir(cache), "check must run the lesson test with -B")

    def test_check_unknown_and_guide(self):
        self.assertEqual(self.cli("check", "99-99")[0], 2)
        guide = next(l["id"] for l in LESSONS if l["kind"] == "guide")
        self.assertEqual(self.cli("check", guide)[0], 1)
        self.assertEqual(self.cli("check", guide, "--self-check")[0], 0)
        self.assertIn(guide, pr.passed_lessons(pr.load_profile(self.path)))


class TestReport(TempProfile):
    def build(self):
        p = pr.new_profile()
        pr.record_placement(p, placement_result({"sql": (1, 2), "statistics": (0, 2)}), "2026-09-01")
        pr.record_placement(p, placement_result({"sql": (2, 2), "statistics": (1, 2)}), "2026-10-15")
        pr.record_attempt(p, "01-01", True, "2026-09-03")
        pr.record_attempt(p, "01-02", True, "2026-09-10")
        pr.record_attempt(p, "02-01", True, "2026-09-10")
        p["interviews"].append(pr.interview_entry(card([2, 2, 3, 3], date="2026-09-20"), LESSONS))
        p["interviews"].append(pr.interview_entry(card([3, 3, 3, 4], date="2026-10-20"), LESSONS))
        pr.save_profile(p, self.path)
        return p

    def test_before_and_after(self):
        rep = pr.report(self.build(), LESSONS)
        areas = dict((a["area"], a) for a in rep["placement"]["areas"])
        self.assertEqual(areas["sql"]["change_pct"], 50)
        self.assertEqual(areas["statistics"]["change_pct"], 50)
        self.assertEqual(rep["placement"]["first_total"], [1, 4])
        self.assertEqual(rep["placement"]["latest_total"], [3, 4])
        self.assertEqual([t["cumulative"] for t in rep["lessons"]["timeline"]], [1, 3])
        self.assertEqual([i["overall"] for i in rep["interviews"]], ["not yet", "pass"])
        self.assertEqual(len(rep["placement"]["areas"]), 2)

    def test_formats(self):
        self.build()
        code, out = self.cli("report", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(json.loads(out)), ["interviews", "lessons", "notes", "placement", "track"])
        code, md = self.cli("report", "--md")
        self.assertIn("# Learning progress", md)
        self.assertIn("| SQL | 1 / 2 | 2 / 2 | +50 points |", md)
        self.assertIn("| 2026-10-20 | 3 / 4 | 3 / 4 | 3 / 4 | 4 / 4 | pass |", md)
        code, text = self.cli("report")
        self.assertIn("Placement: first and latest", text)
        for ch in (chr(0x2014), chr(0x2013), chr(0x201C), chr(0x201D)):
            self.assertNotIn(ch, md + text)

    def test_empty_report(self):
        code, text = self.cli("report")
        self.assertEqual(code, 0)
        self.assertIn("No placement recorded yet.", text)
        self.assertIn("No mock interviews recorded yet.", text)


class FakeTty(io.StringIO):
    def __init__(self, text, tty):
        io.StringIO.__init__(self, text)
        self._tty = tty

    def isatty(self):
        return self._tty


SECRET_TEXT = ["Bob Example", "bob@example.com", "joins feel slow", "Senior analyst at Acme", "my strongest moment"]


class TestExport(TempProfile):
    def build(self):
        p = pr.new_profile()
        res = placement_result({"sql": (1, 2), "statistics": (0, 2)}, levels={"sql": "mixed", "statistics": "weak"})
        res["scores"]["areas"]["sql"]["why"] = "Bob Example wrote this"
        pr.record_placement(p, res, "2026-09-01")
        pr.record_placement(p, placement_result({"sql": (2, 2), "statistics": (1, 2)},
                                                levels={"sql": "strong", "statistics": "Bob Example"}), "2026-10-15")
        pr.record_attempt(p, "01-01", False, "2026-09-02")
        pr.record_attempt(p, "01-01", False, "2026-09-03")
        pr.record_attempt(p, "01-01", True, "2026-09-03")
        pr.record_attempt(p, "01-01", True, "2026-09-05")
        pr.record_attempt(p, "01-02", False, "2026-09-10")
        pr.record_attempt(p, "02-01", True, "2026-09-10", target="solution")   # never exported
        pr.record_attempt(p, "bob@example.com", True, "2026-09-10")              # not a lesson id: dropped
        c = card([3, 3, 3, 4], date="2026-10-20")
        c["role"], c["strongest_moment"] = "Senior analyst at Acme", "my strongest moment"
        c["rounds"]["sql"]["question"] = "Bob Example asked about joins"
        p["interviews"].append(pr.interview_entry(c, LESSONS))
        p["notes"] += [{"date": "2026-09-01", "text": "joins feel slow"}, {"date": "2026-09-02", "text": "Bob Example"}]
        p["email"] = "bob@example.com"   # an unexpected field in the profile never leaks
        pr.save_profile(p, self.path)
        return p

    def export(self, *args, stdin=None):
        out, err = io.StringIO(), io.StringIO()
        old = sys.stdin
        sys.stdin = stdin if stdin is not None else FakeTty("", False)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = pr.main(["--profile", self.path, "export"] + list(args))
        finally:
            sys.stdin = old
        return code, out.getvalue(), err.getvalue()

    def check_keys(self, data):
        K = pr.EXPORT_KEYS
        self.assertEqual(sorted(data), sorted(K["top"]))
        self.assertEqual(sorted(data["placement"]), sorted(K["placement"]))
        for which in ("first", "latest"):
            e = data["placement"][which]
            self.assertEqual(sorted(e), sorted(K["placement_entry"]))
            for area, v in e["areas"].items():
                self.assertIn(area, pr.PLACEMENT_AREAS)
                self.assertEqual(sorted(v), sorted(K["placement_area"]))
        self.assertEqual(sorted(data["lessons"]), sorted(K["lessons"]))
        for it in data["lessons"]["items"]:
            self.assertEqual(sorted(it), sorted(K["lesson_item"]))
        self.assertEqual(sorted(data["activity"]), sorted(K["activity"]))
        for i in data["interviews"]:
            self.assertEqual(sorted(i), sorted(K["interview"]))
            self.assertEqual(sorted(i["scores"]), sorted(pr.ROUNDS))

    def test_allowlist_schema_and_values(self):
        self.build()
        code, out, err = self.export("--yes")
        self.assertEqual(code, 0, err)
        data = json.loads(out)
        self.check_keys(data)
        self.assertEqual(data["schema"], pr.EXPORT_SCHEMA)
        self.assertRegex(data["pilot_id"], r"^p-[0-9a-f]{16}$")
        self.assertRegex(data["course_version"], r"^([0-9a-f]{7,40}|unknown)$")
        self.assertEqual(data["placement"]["count"], 2)
        self.assertEqual(data["placement"]["first"]["areas"]["sql"], {"correct": 1, "total": 2, "level": "mixed"})
        self.assertIsNone(data["placement"]["latest"]["areas"]["statistics"]["level"])   # free text dropped
        items = dict((x["id"], x) for x in data["lessons"]["items"])
        self.assertEqual(sorted(items), ["01-01", "01-02"])
        self.assertEqual(items["01-01"], {"id": "01-01", "first_attempt": "2026-09-02", "attempts": 4,
                                          "passed": True, "passed_on": "2026-09-03", "attempts_before_pass": 2})
        self.assertFalse(items["01-02"]["passed"])
        self.assertEqual(data["activity"], {"first_day": "2026-09-01", "latest_day": "2026-10-20",
                                            "days_between": 49})
        self.assertEqual(data["interviews"], [{"date": "2026-10-20", "overall": "pass",
                                               "scores": {"sql": 3, "statistics": 3, "metrics-case": 3,
                                                          "behavioural": 4}}])

    def test_notes_names_and_paths_never_exported(self):
        self.build()
        code, out, _ = self.export("--yes")
        for text in SECRET_TEXT + ["notes", self.dir, os.path.expanduser("~"), "why", "role"]:
            self.assertNotIn(text, out)

    def test_dates_are_cut_to_the_day(self):
        p = pr.new_profile()
        pr.record_attempt(p, "01-01", True, "2026-09-02T13:45:10")
        data = pr.export_summary(p, LESSONS, version="abc1234", on="2026-10-31T08:00:00")
        self.assertEqual(data["lessons"]["items"][0]["passed_on"], "2026-09-02")
        self.assertEqual(data["exported_on"], "2026-10-31")
        self.assertEqual(pr.export_summary(p, LESSONS, version="not a sha")["course_version"], "unknown")

    def test_notice_shown_and_yes_required_when_not_interactive(self):
        self.build()
        before = pr.load_profile(self.path)
        code, out, err = self.export()
        self.assertEqual(code, 1)
        self.assertEqual(out, "")
        self.assertIn("It includes ONLY", err)
        self.assertIn("never includes your notes", err)
        self.assertIn("--yes", err)
        self.assertNotIn("pilot_id", pr.load_profile(self.path))
        self.assertEqual(before, pr.load_profile(self.path))
        code, out, err = self.export("--yes")
        self.assertIn("It includes ONLY", err)   # shown even with --yes
        self.assertEqual(code, 0)

    def test_interactive_y_and_no(self):
        self.build()
        code, out, _ = self.export(stdin=FakeTty("n\n", True))
        self.assertEqual((code, out), (1, ""))
        code, out, _ = self.export(stdin=FakeTty("y\n", True))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["schema"], pr.EXPORT_SCHEMA)

    def test_pilot_id_is_kept_and_can_be_regenerated(self):
        self.build()
        first = json.loads(self.export("--yes")[1])["pilot_id"]
        self.assertEqual(json.loads(self.export("--yes")[1])["pilot_id"], first)
        new = json.loads(self.export("--yes", "--new-id")[1])["pilot_id"]
        self.assertNotEqual(new, first)
        self.assertEqual(pr.load_profile(self.path)["pilot_id"], new)

    def test_out_file(self):
        self.build()
        target = os.path.join(self.dir, "pilot.json")
        code, out, _ = self.export("--yes", "--out", target)
        self.assertEqual((code, out), (0, ""))
        with open(target, encoding="utf-8") as f:
            self.check_keys(json.load(f))

    def test_course_version_never_fails(self):
        self.assertEqual(pr.course_version(self.dir), "unknown")
        self.assertEqual(pr.course_version(os.path.join(self.dir, "missing")), "unknown")


class TestAggregate(TempProfile):
    def learner(self, name, attempts, placements=(), interviews=(), on="2026-10-31"):
        p = pr.new_profile()
        p["pilot_id"] = pr.new_pilot_id()
        for counts, date in placements:
            pr.record_placement(p, placement_result(counts), date)
        for lid, ok, date in attempts:
            pr.record_attempt(p, lid, ok, date)
        for scores, date in interviews:
            p["interviews"].append(pr.interview_entry(card(scores, date=date), LESSONS))
        self.write_json(name, pr.export_summary(p, LESSONS, version="abc1234", on=on))

    def test_metrics(self):
        self.learner("a.json", [("00-01", False, "2026-10-01"), ("00-01", True, "2026-10-02"),
                                ("01-01", True, "2026-10-09"), ("10-01", True, "2026-10-20")],
                     placements=[({"sql": (1, 4)}, "2026-10-01"), ({"sql": (3, 4)}, "2026-10-20")],
                     interviews=[([3, 3, 3, 3], "2026-10-25")])
        self.learner("b.json", [("00-01", False, "2026-10-01")], placements=[({"sql": (0, 4)}, "2026-10-01")])
        self.learner("c.json", [("00-01", True, "2026-10-28")], on="2026-10-30")   # too new for day 7
        self.write_json("junk.json", {"hello": 1})
        code, out = self.cli("aggregate", self.dir, "--json")
        self.assertEqual(code, 0, out)
        agg = json.loads(out)
        self.assertEqual(agg["learners"], 3)
        self.assertEqual(agg["skipped"], ["junk.json"])
        self.assertEqual(agg["placement_completed"], 2)
        self.assertEqual(agg["first_lesson_passed"], 2)
        self.assertEqual(agg["median_days_to_first_pass"], 0.5)
        self.assertEqual(agg["day7_return"], {"returned": 1, "eligible": 2})
        self.assertEqual(agg["lessons_passed_per_learner"], {"median": 1, "min": 0, "max": 3})
        self.assertEqual(agg["placement_before_after"], {"learners_with_two_or_more": 1,
                                                         "median_change_points_by_area": {"sql": 50.0}})
        self.assertEqual(agg["capstone_passed"], 1)
        self.assertEqual(agg["mock_interview"], {"learners": 1, "latest_pass": 1})
        stuck = dict((r["id"], r) for r in agg["where_stuck"])
        self.assertEqual(stuck["00-01"]["tried"], 3)
        self.assertEqual(stuck["00-01"]["not_passed"], 1)
        code, text = self.cli("aggregate", self.dir)
        self.assertIn("Day-7 return:               1 of 2", text)

    def test_latest_export_per_pilot_wins(self):
        p = pr.new_profile()
        p["pilot_id"] = "p-0123456789abcdef"
        self.write_json("old.json", pr.export_summary(p, LESSONS, on="2026-10-01"))
        pr.record_attempt(p, "00-01", True, "2026-10-02")
        self.write_json("new.json", pr.export_summary(p, LESSONS, on="2026-10-10"))
        exports, _ = pr.load_exports(self.dir)
        self.assertEqual(len(exports), 1)
        self.assertEqual(exports[0]["lessons"]["passed"], 1)

    def test_empty_folder(self):
        os.makedirs(os.path.join(self.dir, "empty"))
        code, text = self.cli("aggregate", os.path.join(self.dir, "empty"))
        self.assertEqual(code, 0)
        self.assertIn("No exports to count.", text)


if __name__ == "__main__":
    unittest.main()
