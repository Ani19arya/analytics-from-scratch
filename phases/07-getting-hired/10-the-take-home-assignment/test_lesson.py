"""Tests for lesson 07-10: the take-home assignment.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected answers and grades are worked out below in plain Python, separately from the
lesson code. Your grader runs on the committed submissions, on a dataset and submissions
built in a temporary folder from other seeds, and on small hand-made submissions.
"""
import csv
import importlib.util
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

sys.path.insert(0, HERE)
import make_data  # noqa: E402

SUBS = os.path.join(HERE, "data", "submissions")
WANT = {"strong": [], "weak_fast": ["answers_wrong", "data_checks"],
        "weak_buried": ["answer_not_first", "no_assumptions", "no_code", "too_long"]}


def read_orders(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def ref_clean(rows):
    ids = {}
    for r in rows:
        ids.setdefault(r["order_id"], r)
    unique = list(ids.values())
    tests = [r for r in unique if r["customer_email"].lower().endswith("@kestrelhome.test")]
    real = [r for r in unique if r not in tests]
    refunded = [r for r in real if r["status"] != "paid"]
    paid = [r for r in real if r["status"] == "paid"]
    return paid, {"duplicates": len(rows) - len(unique), "test_orders": len(tests), "refunded": len(refunded)}


def ref_answers(paid):
    months = {"2026-09": {}, "2026-10": {}}
    for r in paid:
        m = months.setdefault(r["order_date"][:7], {})
        m[r["region"]] = m.get(r["region"], 0) + round(float(r["amount"]) * 100)  # cents, no float drift
    regions = sorted(set(months["2026-09"]) | set(months["2026-10"]))
    growth = [(months["2026-10"].get(g, 0) - months["2026-09"].get(g, 0), g) for g in regions]
    best = max(c for c, _ in growth) if growth else 0
    top = [g for c, g in growth if c == best][0] if growth else ""
    oct_customers = {}
    for r in paid:
        if r["order_date"][:7] == "2026-10":
            oct_customers.setdefault(r["customer_id"], []).append(r["order_id"])
    repeat = 0.0
    if oct_customers:
        repeat = round(100.0 * len([c for c in oct_customers.values() if len(c) > 1]) / len(oct_customers), 1)
    return {"oct_revenue": sum(months["2026-10"].values()) / 100, "top_growth_region": top,
            "top_growth_amount": best / 100, "repeat_rate_pct": repeat}


def write(folder, files):
    os.makedirs(folder, exist_ok=True)
    for name, text in files.items():
        with open(os.path.join(folder, name), "w") as f:
            f.write(text)


def order(oid, cust, date, region, amount, status="paid", email=None):
    return {"order_id": oid, "customer_id": cust, "customer_email": email or cust.lower() + "@mail.example",
            "order_date": date, "region": region, "amount": amount, "status": status}


# Hand-made orders: one duplicate, one test order, one refund, a tie in growth.
HAND = [
    order("1", "A", "2026-09-03", "East", "100.00"),
    order("2", "A", "2026-10-03", "East", "150.00"),
    order("2", "A", "2026-10-03", "East", "150.00"),
    order("3", "B", "2026-10-04", "West", "50.00"),
    order("4", "B", "2026-10-09", "West", "40.00", status="refunded"),
    order("5", "QA", "2026-10-05", "West", "999.00", email="qa1@kestrelhome.test"),
    order("6", "C", "2026-10-07", "North", "50.00"),
    order("7", "C", "2026-10-08", "North", "10.00"),
    order("8", "C", "2026-09-20", "North", "60.00"),
]
HAND_COUNTS = {"duplicates": 1, "test_orders": 1, "refunded": 1}
HAND_ANSWERS = {"oct_revenue": 260.0, "top_growth_region": "East", "top_growth_amount": 50.0, "repeat_rate_pct": 33.3}
GOOD_README = """# Title

East grew the most, by $50.00. October net revenue was $260.00.

## Data checks

- 1 duplicate row removed.
- 1 test order removed.
- 1 refund left out.

## Assumptions

- Net revenue is paid orders.
"""
GOOD_ANSWERS = "question,answer\noct_revenue,260.00\ntop_growth_region,East\ntop_growth_amount,50.00\nrepeat_rate_pct,33.3\n"


class TestCleanAndAnswers(unittest.TestCase):
    def test_hand_made(self):
        paid, counts = lesson.clean(HAND)
        self.assertEqual(counts, HAND_COUNTS, "remove the repeated order first, then the test order, then the refund")
        self.assertEqual(sorted(r["order_id"] for r in paid), ["1", "2", "3", "6", "7", "8"])
        got = lesson.expected_answers(paid)
        self.assertEqual(got["top_growth_region"], "East",
                         "East and West both grew $50.00: a tie goes to the region first in alphabetical order")
        for q in ("oct_revenue", "top_growth_amount", "repeat_rate_pct"):
            self.assertAlmostEqual(got[q], HAND_ANSWERS[q], places=2, msg="%s is wrong on the hand-made orders" % q)

    def test_empty(self):
        paid, counts = lesson.clean([])
        self.assertEqual((paid, counts), ([], {"duplicates": 0, "test_orders": 0, "refunded": 0}), "no rows, nothing removed")
        got = lesson.expected_answers([])
        self.assertEqual(got["repeat_rate_pct"], 0.0, "with no October customers the repeat rate is 0.0, not an error")
        self.assertEqual(got["oct_revenue"], 0.0)

    def test_committed(self):
        rows = read_orders(os.path.join(HERE, "data", "takehome", "orders.csv"))
        paid, counts = lesson.clean(rows)
        rpaid, rcounts = ref_clean(rows)
        self.assertEqual(counts, rcounts, "data check counts on orders.csv")
        got, want = lesson.expected_answers(paid), ref_answers(rpaid)
        self.assertEqual(got["top_growth_region"], want["top_growth_region"])
        for q in ("oct_revenue", "top_growth_amount", "repeat_rate_pct"):
            self.assertAlmostEqual(got[q], want[q], places=2, msg="%s on orders.csv" % q)


class TestCheckAnswers(unittest.TestCase):
    def test_formats_and_misses(self):
        want = dict(HAND_ANSWERS)
        ok = {"oct_revenue": "$260.00", "top_growth_region": "east", "top_growth_amount": "50", "repeat_rate_pct": "33.3"}
        self.assertEqual(lesson.check_answers(ok, want), [], "accept $, a different case and 50 for 50.00")
        self.assertEqual(lesson.check_answers({}, want), sorted(want), "every missing answer is wrong")
        bad = dict(ok, oct_revenue="1,260.00", repeat_rate_pct="33.4", top_growth_amount="fifty")
        self.assertEqual(lesson.check_answers(bad, want), ["oct_revenue", "repeat_rate_pct", "top_growth_amount"],
                         "1,260.00 is not 260.00, 33.4 is outside 0.05 of 33.3, and text that is not a number is wrong")
        self.assertEqual(lesson.check_answers(dict(ok, oct_revenue="1,260.00"), dict(want, oct_revenue=1260.0)), [],
                         "thousands commas are allowed")


class TestGrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def sub(self, name, files):
        folder = os.path.join(self.tmp, name)
        write(folder, files)
        return folder

    def test_committed(self):
        rows = read_orders(os.path.join(HERE, "data", "takehome", "orders.csv"))
        for name, want in WANT.items():
            self.assertEqual(lesson.grade(os.path.join(SUBS, name), rows), want, "submission %s" % name)

    def test_other_seeds(self):
        for seed in (4, 9):
            root = os.path.join(self.tmp, "seed%d" % seed)
            make_data.write_files(make_data.build(seed), root)
            rows = read_orders(os.path.join(root, "takehome", "orders.csv"))
            rpaid, rcounts = ref_clean(rows)
            self.assertEqual(lesson.clean(rows)[1], rcounts, "seed %d: data check counts" % seed)
            for name, want in WANT.items():
                self.assertEqual(lesson.grade(os.path.join(root, "submissions", name), rows), want,
                                 "seed %d, submission %s" % (seed, name))

    def test_hand_made_strong(self):
        folder = self.sub("good", {"README.md": GOOD_README, "answers.csv": GOOD_ANSWERS, "q.SQL": "select 1;"})
        self.assertEqual(lesson.grade(folder, HAND), [], "a short, correct write-up with code (.SQL counts) passes")

    def test_hand_made_problems(self):
        folder = self.sub("empty", {})
        self.assertEqual(lesson.grade(folder, HAND), ["answers_wrong", "no_code", "no_readme"],
                         "an empty folder: no answers, no code, no README (skip the write-up checks)")
        off_by_one = GOOD_README.replace("1 test order", "2 test orders")
        self.assertNotEqual(off_by_one, GOOD_README)
        folder = self.sub("counts", {"README.md": off_by_one, "answers.csv": GOOD_ANSWERS, "a.py": ""})
        self.assertEqual(lesson.grade(folder, HAND), ["data_checks"], "the data checks must give the real counts")
        no_bullets = GOOD_README.replace("- Net revenue is paid orders.", "Net revenue is paid orders.")
        folder = self.sub("assume", {"README.md": no_bullets, "answers.csv": GOOD_ANSWERS, "a.py": ""})
        self.assertEqual(lesson.grade(folder, HAND), ["no_assumptions"], "assumptions are '- ' bullets under '## Assumptions'")
        buried = GOOD_README.replace("# Title\n", "# Title\n\nWe used Python.\n")
        folder = self.sub("buried", {"README.md": buried, "answers.csv": GOOD_ANSWERS, "a.py": ""})
        self.assertEqual(lesson.grade(folder, HAND), ["answer_not_first"], "the first line under the title must give the answer")
        long_text = GOOD_README + "\nMore words here. " * 200
        folder = self.sub("long", {"README.md": long_text, "answers.csv": GOOD_ANSWERS, "a.py": ""})
        self.assertEqual(lesson.grade(folder, HAND), ["too_long"], "more than 500 words is too long")

    def test_own_region_is_used_for_answer_first(self):
        wrong = GOOD_ANSWERS.replace("East", "West")
        folder = self.sub("west", {"README.md": GOOD_README.replace("East grew", "West grew"), "answers.csv": wrong, "a.py": ""})
        self.assertEqual(lesson.grade(folder, HAND), ["answers_wrong"],
                         "a wrong answer stated first is answers_wrong, not answer_not_first")


if __name__ == "__main__":
    unittest.main()
