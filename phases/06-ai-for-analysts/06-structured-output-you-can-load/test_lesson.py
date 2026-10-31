"""Tests. Default: checks exercise.py. With CHECK_SOLUTION=1: checks solution/solution.py.

The answer key does not come from the solution. make_data.build(seed) records which damage
it applied to every output, so the test knows which rows must load (no damage, or only a
fence, surrounding text or a trailing comma) and what their true fields are.
"""
import csv
import importlib.util
import json
import os
import sqlite3
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))

OTHER_SEED = 1606
FIELDS = ["order_id", "issue", "refund_requested", "amount_rs", "severity"]
GOOD = {"order_id": "TB-12345", "issue": "late", "refund_requested": True, "amount_rs": 240, "severity": 3}


def committed_rows():
    with open(os.path.join(HERE, "data", "outputs.csv"), newline="") as f:
        return list(csv.DictReader(f))


def with_change(**changes):
    obj = dict(GOOD)
    for key, value in changes.items():
        if value is KeyError:
            del obj[key]
        else:
            obj[key] = value
    return obj


class TestRepair(unittest.TestCase):
    def test_fence_prose_and_trailing_comma(self):
        body = json.dumps(GOOD)
        for raw in ["```json\n" + body + "\n```", "```\n" + body + "\n```", "Sure! Here it is:\n" + body + "\nThanks",
                    body[:-1] + ",}", "  " + body + "\n"]:
            text, _ = lesson.repair(raw)
            self.assertIsNotNone(text, "repair gave up on %r" % raw[:30])
            self.assertEqual(json.loads(text), GOOD, "after repair, %r should parse to the original object" % raw[:30])

    def test_nothing_to_repair(self):
        for raw in ["", "I could not find an order in this message.", "}{"]:
            text, _ = lesson.repair(raw)
            self.assertIsNone(text, "%r holds no JSON object, so repair should return None" % raw)

    def test_repair_never_changes_values(self):
        text, _ = lesson.repair(json.dumps(dict(GOOD, severity="3")))
        self.assertEqual(json.loads(text)["severity"], "3", "repair must not convert types: that is the schema's job")


class TestValidate(unittest.TestCase):
    def test_good_object_and_null_amount(self):
        self.assertEqual(lesson.validate(GOOD), [])
        self.assertEqual(lesson.validate(with_change(amount_rs=None)), [], "amount_rs may be null")
        self.assertEqual(lesson.validate(with_change(amount_rs=0)), [], "zero is a real amount, not a missing one")
        self.assertEqual(lesson.validate(with_change(amount_rs=99.5)), [], "a float is a number")

    def test_each_problem_is_rejected(self):
        bad = {
            "severity as text": with_change(severity="3"),
            "severity true": with_change(severity=True),
            "severity 3.0": with_change(severity=3.0),
            "refund as yes": with_change(refund_requested="yes"),
            "refund as 1": with_change(refund_requested=1),
            "issue off the list": with_change(issue="Late delivery"),
            "issue null": with_change(issue=None),
            "severity 0": with_change(severity=0),
            "severity 6": with_change(severity=6),
            "negative amount": with_change(amount_rs=-1),
            "NaN amount": with_change(amount_rs=float("nan")),
            "amount as text": with_change(amount_rs="Rs 240"),
            "missing amount": with_change(amount_rs=KeyError),
            "extra key": with_change(confidence=0.9),
            "order id format": with_change(order_id="12345"),
        }
        for name, obj in bad.items():
            self.assertNotEqual(lesson.validate(obj), [], "%s should be rejected, but validate found no problem" % name)

    def test_not_an_object(self):
        for obj in [[GOOD], "late", 3, None, {}]:
            self.assertNotEqual(lesson.validate(obj), [], "%r is not a valid record" % (obj,))

    def test_parse_reports_a_reason(self):
        record, reason = lesson.parse('{"order_id": "TB-12345"')
        self.assertIsNone(record)
        self.assertTrue(reason, "a rejected output needs a reason so someone can fix the prompt")
        record, reason = lesson.parse("```json\n" + json.dumps(GOOD) + "\n```")
        self.assertEqual((record, reason), (GOOD, ""))


class TestPipeline(unittest.TestCase):
    def check_seed(self, seed, rows):
        truth = {t["message_id"]: t for t in make_data.build(seed)["truth"]}
        valid, rejects = lesson.process(rows)
        loaded = {r["message_id"] for r in valid}
        rejected = {m for m, _ in rejects}
        self.assertEqual(loaded | rejected, set(truth), "seed %d: every output must end up loaded or rejected" % seed)
        self.assertFalse(loaded & rejected, "seed %d: an output cannot be both loaded and rejected" % seed)
        for mid, t in sorted(truth.items()):
            self.assertEqual(mid in loaded, t["valid"],
                             "seed %d, %s (wrapper %s, problem %s): expected %s" %
                             (seed, mid, t["wrapper"], t["content"], "loaded" if t["valid"] else "rejected"))
        for r in valid:
            self.assertEqual({k: r[k] for k in FIELDS}, {k: truth[r["message_id"]][k] for k in FIELDS},
                             "seed %d, %s: loaded fields differ from the true fields" % (seed, r["message_id"]))
        conn = sqlite3.connect(":memory:")
        lesson.load_into_sqlite(conn, valid, rejects)
        expected = {}
        for t in truth.values():
            if t["valid"]:
                expected[t["issue"]] = expected.get(t["issue"], 0) + 1
        want = sorted(expected.items(), key=lambda kv: (-kv[1], kv[0]))
        self.assertEqual([tuple(x) for x in lesson.issue_counts(conn)], want, "seed %d: issue counts" % seed)
        types = conn.execute("SELECT DISTINCT typeof(severity), typeof(refund_requested) FROM complaints").fetchall()
        self.assertEqual(types, [("integer", "integer")], "severity and refund_requested must be stored as integers")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM rejects").fetchone()[0], len(rejects))

    def test_committed_data(self):
        rows = committed_rows()
        self.assertEqual(rows, make_data.build()["outputs"], "data/outputs.csv is out of date: run python3 make_data.py")
        self.check_seed(make_data.DEFAULT_SEED, rows)

    def test_second_dataset(self):
        self.check_seed(OTHER_SEED, make_data.build(OTHER_SEED)["outputs"])

    def test_empty_input(self):
        self.assertEqual(lesson.process([]), ([], []))
        conn = sqlite3.connect(":memory:")
        lesson.load_into_sqlite(conn, [], [])
        self.assertEqual(list(lesson.issue_counts(conn)), [], "no rows should give no counts")

    def test_tie_in_issue_counts(self):
        rows = [{"message_id": "A", "raw_output": json.dumps(with_change(issue="other"))},
                {"message_id": "B", "raw_output": json.dumps(with_change(order_id="TB-22222", issue="late"))}]
        valid, rejects = lesson.process(rows)
        conn = sqlite3.connect(":memory:")
        lesson.load_into_sqlite(conn, valid, rejects)
        self.assertEqual([tuple(x) for x in lesson.issue_counts(conn)], [("late", 1), ("other", 1)],
                         "ties are broken by issue name")

    def test_fixture_is_labelled(self):
        with open(os.path.join(HERE, "data", "fixture.json")) as f:
            info = json.load(f)
        self.assertEqual(info["raw_output_source"], "simulated")
        self.assertTrue(info["model"].startswith("none"))


if __name__ == "__main__":
    unittest.main()
