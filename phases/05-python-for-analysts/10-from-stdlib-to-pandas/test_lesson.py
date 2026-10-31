"""Tests for lesson 10: from standard library to pandas.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

Without pandas: every function is checked on small hand-made rows (None in every position,
ties, an empty table, a group with no values) and against a reference written here, on the
committed file and on a second file from make_data.build(seed=2040) in memory.
With pandas installed, one more class runs each pandas call from PANDAS_EQUIVALENT's rules on
the same data and checks that your function gives the same answer. It is skipped otherwise.
"""
import csv
import importlib.util
import io
import math
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" \
    else os.path.join(HERE, "exercise.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lesson = load("lesson", TARGET)
make_data = load("make_data", os.path.join(HERE, "make_data.py"))
OTHER_SEED = 2040
CSV_PATH = os.path.join(HERE, "data", "orders.csv")
try:
    import pandas as pd
    HAVE_PANDAS = True
except ImportError:
    HAVE_PANDAS = False


def read_raw(path=CSV_PATH):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def ref_typed(raw_rows):
    """Text rows to typed rows: blank is None, qty int, amount float."""
    out = []
    for r in raw_rows:
        row = dict(r)
        for k, v in r.items():
            if v == "":
                row[k] = None
            elif k == "qty":
                row[k] = int(v)
            elif k == "amount":
                row[k] = float(v)
        out.append(row)
    return out


def ref_dedupe(rows):
    seen, out = [], []
    for r in rows:
        key = tuple(sorted(r.items(), key=lambda kv: kv[0]))
        if key not in seen:
            seen.append(key)
            out.append(r)
    return out


def ref_region_sums(rows):
    sums = {}
    for r in rows:
        sums[r["region"]] = sums.get(r["region"], 0) + (r["amount"] or 0)
    return sums


SMALL = [{"id": 1, "g": "a", "v": 3.0}, {"id": 2, "g": None, "v": 5.0}, {"id": 3, "g": "b", "v": None},
         {"id": 4, "g": "a", "v": None}, {"id": 5, "g": "b", "v": 3.0}, {"id": 6, "g": "c", "v": None}]


class TestSmall(unittest.TestCase):
    def test_read_typed(self):
        path = os.path.join(HERE, "data", "orders.csv")
        rows = lesson.read_typed(path)
        raw = read_raw(path)
        self.assertEqual(rows, ref_typed(raw), "blank cells become None, qty an int, amount a float, the rest text")
        self.assertIn("NA", {r["region"] for r in rows}, "NA is North America: only a blank cell is missing")
        kept = lesson.read_typed(path, types={}, na_values=("", "NA"))
        self.assertNotIn("NA", {r["region"] for r in kept}, "na_values decides which texts become None")

    def test_filter_rows(self):
        ids = lambda rows: [r["id"] for r in rows]
        self.assertEqual(ids(lesson.filter_rows(SMALL, "g", "==", "a")), [1, 4])
        self.assertEqual(ids(lesson.filter_rows(SMALL, "g", "!=", "a")), [2, 3, 5, 6],
                         "like pandas, a None cell is != to everything, so row 2 is kept")
        self.assertEqual(ids(lesson.filter_rows(SMALL, "v", ">=", 3.0)), [1, 2, 5], "a None value never passes > or >=")
        self.assertEqual(ids(lesson.filter_rows(SMALL, "v", "<", 4)), [1, 5])
        self.assertEqual(lesson.filter_rows([], "v", ">", 0), [])
        with self.assertRaises(ValueError):
            lesson.filter_rows(SMALL, "v", "=>", 1)

    def test_group_agg(self):
        self.assertEqual(lesson.group_agg(SMALL, "g", "v", "sum"), {"a": 3.0, "b": 3.0, "c": 0},
                         "the None group is dropped by default, and a group with no values sums to 0")
        self.assertEqual(list(lesson.group_agg(SMALL, "g", "v", "sum", dropna=False)), ["a", "b", "c", None],
                         "dropna=False keeps the None group, sorted last")
        self.assertEqual(lesson.group_agg(SMALL, "g", "v", "sum", dropna=False)[None], 5.0)
        self.assertEqual(lesson.group_agg(SMALL, "g", "v", "count"), {"a": 1, "b": 1, "c": 0}, "count skips None values")
        self.assertEqual(lesson.group_agg(SMALL, "g", "v", "size"), {"a": 2, "b": 2, "c": 1}, "size counts rows")
        self.assertEqual(lesson.group_agg(SMALL, "g", "v", "mean"), {"a": 3.0, "b": 3.0, "c": None},
                         "mean skips None; a group with no values has no mean")
        self.assertEqual(lesson.group_agg([], "g", "v", "sum"), {})
        with self.assertRaises(ValueError):
            lesson.group_agg(SMALL, "g", "v", "median")

    def test_sort_rows(self):
        ids = lambda rows: [r["id"] for r in rows]
        self.assertEqual(ids(lesson.sort_rows(SMALL, "v")), [1, 5, 2, 3, 4, 6], "ties keep their order, None goes last")
        self.assertEqual(ids(lesson.sort_rows(SMALL, "v", ascending=False)), [2, 1, 5, 3, 4, 6],
                         "descending still puts None last")
        self.assertEqual(ids(lesson.sort_rows(SMALL, "g")), [1, 4, 3, 5, 6, 2])

    def test_drop_duplicates(self):
        rows = [{"k": 1, "x": None}, {"k": 1, "x": None}, {"k": 2, "x": "a"}, {"k": 1, "x": "b"}]
        self.assertEqual(lesson.drop_duplicates(rows), [rows[0], rows[2], rows[3]], "None equals None when deduping")
        self.assertEqual(lesson.drop_duplicates(rows, subset=["k"]), [rows[0], rows[2]])
        self.assertEqual(lesson.drop_duplicates(rows, subset=["k"], keep="last"), [rows[2], rows[3]])
        self.assertEqual(lesson.drop_duplicates(rows, subset=["k"], keep=False), [rows[2]])
        self.assertEqual(lesson.drop_duplicates([]), [])

    def test_value_counts(self):
        got = lesson.value_counts(SMALL, "g")
        self.assertEqual(got, {"a": 2, "b": 2, "c": 1})
        self.assertEqual(list(got), ["a", "b", "c"], "most common first, ties in order of first appearance")
        self.assertEqual(lesson.value_counts(SMALL, "g", dropna=False), {"a": 2, None: 1, "b": 2, "c": 1})

    def test_the_map(self):
        need = {"read_typed": ["read_csv", "keep_default_na"], "filter_rows": ["df["],
                "group_agg": ["groupby"], "sort_rows": ["sort_values", "stable"],
                "drop_duplicates": ["drop_duplicates"], "value_counts": ["value_counts"]}
        for name, words in need.items():
            text = lesson.PANDAS_EQUIVALENT.get(name, "")
            for w in words:
                self.assertIn(w, text, "PANDAS_EQUIVALENT[%r] should name the pandas call, including %r" % (name, w))


class DataChecks:
    raw = None

    def typed(self):
        return lesson.read_typed(self.path) if self.path else ref_typed(self.raw)

    def test_dedupe_then_region_totals(self):
        rows = self.typed()
        clean = lesson.drop_duplicates(rows)
        want = ref_dedupe(ref_typed(self.raw))
        self.assertEqual(clean, want, "drop_duplicates keeps the first copy of each repeated row")
        got = lesson.group_agg(clean, "region", "amount", "sum", dropna=False)
        ref = ref_region_sums(want)
        self.assertEqual(sorted(got, key=lambda k: (k is None, k or "")), sorted(ref, key=lambda k: (k is None, k or "")))
        for k, v in ref.items():
            self.assertAlmostEqual(got[k], v, places=2, msg="revenue for region %r" % k)
        self.assertAlmostEqual(sum(got.values()), sum(r["amount"] or 0 for r in want), places=2,
                               msg="with dropna=False the regions add up to the total")

    def test_counts(self):
        rows = ref_typed(self.raw)
        got = lesson.value_counts(rows, "region", dropna=False)
        want = {}
        for r in rows:
            want[r["region"]] = want.get(r["region"], 0) + 1
        self.assertEqual(got, want)
        self.assertEqual(list(got.values()), sorted(want.values(), reverse=True))
        self.assertEqual(lesson.group_agg(rows, "channel", "amount", "size"),
                         {c: sum(1 for r in rows if r["channel"] == c) for c in sorted({r["channel"] for r in rows})})


class TestCommittedFile(DataChecks, unittest.TestCase):
    raw = read_raw()
    path = CSV_PATH


class TestSecondFile(DataChecks, unittest.TestCase):
    raw = make_data.build(OTHER_SEED)["orders"]
    path = None


def nan_to_none(x):
    return None if isinstance(x, float) and math.isnan(x) else x


@unittest.skipUnless(HAVE_PANDAS, "optional: pandas is not installed")
class TestAgainstPandas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datasets = []
        for raw in (read_raw(), make_data.build(OTHER_SEED)["orders"]):
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=list(raw[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(raw)
            text = buf.getvalue()
            df = pd.read_csv(io.StringIO(text), keep_default_na=False, na_values=[""])
            cls.datasets.append((text, df, ref_typed(raw)))

    def test_read_csv_default_loses_na(self):
        text, df, rows = self.datasets[0]
        default = pd.read_csv(io.StringIO(text))
        self.assertEqual(int(default["region"].isna().sum()), sum(1 for r in rows if r["region"] in (None, "NA")),
                         "pandas' default reads the text NA as missing")
        self.assertEqual(int(df["region"].isna().sum()), sum(1 for r in rows if r["region"] is None))

    def test_same_answers_as_pandas(self):
        for text, df, rows in self.datasets:
            for how in ("sum", "mean", "count", "size"):
                for dropna in (True, False):
                    want = df.groupby("region", dropna=dropna)["amount"].agg(how)
                    want = {nan_to_none(k): nan_to_none(float(v)) for k, v in want.items()}
                    got = lesson.group_agg(rows, "region", "amount", how, dropna=dropna)
                    self.assertEqual(list(got), list(want), "group order for %s, dropna=%s" % (how, dropna))
                    for k in want:
                        if want[k] is None:
                            self.assertIsNone(got[k])
                        else:
                            self.assertAlmostEqual(got[k], want[k], places=6, msg="%s for %r" % (how, k))
            for op, value in (("!=", "EU"), ("==", "NA"), (">", 500.0), ("<=", 89.0)):
                col = "region" if isinstance(value, str) else "amount"
                mask = {"!=": df[col] != value, "==": df[col] == value, ">": df[col] > value, "<=": df[col] <= value}[op]
                self.assertEqual([r["order_id"] for r in lesson.filter_rows(rows, col, op, value)],
                                 df[mask]["order_id"].tolist(), "filter %s %s %r" % (col, op, value))
            for asc in (True, False):
                want = df.sort_values("amount", ascending=asc, kind="stable", na_position="last")["order_id"].tolist()
                self.assertEqual([r["order_id"] for r in lesson.sort_rows(rows, "amount", asc)], want)
            self.assertEqual(len(lesson.drop_duplicates(rows)), len(df.drop_duplicates()))
            self.assertEqual(len(lesson.drop_duplicates(rows, keep=False)), len(df.drop_duplicates(keep=False)))
            want = {nan_to_none(k): int(v) for k, v in df["region"].value_counts(dropna=False).items()}
            self.assertEqual(lesson.value_counts(rows, "region", dropna=False), want)


if __name__ == "__main__":
    unittest.main()
