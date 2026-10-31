"""Tests for lesson 06: pivot tables and Power Query steps.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected rows come from make_data.truth(), the generator's record of the receipts
before it made the export messy. The expected pivot is summed here from those rows in
plain Python. Nothing is read from the solution file.

The same steps must clean the committed September and October files AND the two months
that make_data.build(seed=2031) makes in memory in other export styles (other headers,
another date format, no Total row). Steps that only fit the committed files fail there.
"""
import csv
import importlib.util
import os
import tempfile
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
OTHER_SEED = 2031
STEP_NAMES = ["Removed Top Rows", "Promoted Headers", "Renamed Columns", "Trimmed Text", "Capitalized Each Word",
              "Filtered Rows", "Changed Type", "Removed Duplicates", "Added Custom"]


def read_raw(name):
    with open(os.path.join(HERE, "data", name + ".csv"), newline="") as f:
        return list(csv.reader(f))


def ref_pivot(rows, index, columns, values):
    cells = {}
    for r in rows:
        cells[(r[index], r[columns])] = cells.get((r[index], r[columns]), 0) + r[values]
    return {k: round(v, 2) for k, v in cells.items()}


class TestStepList(unittest.TestCase):
    def test_step_names_match_power_query(self):
        self.assertEqual([name for name, _ in lesson.STEPS], STEP_NAMES,
                         "STEPS should list the nine named steps in this order, like Applied Steps")


class TestSteps(unittest.TestCase):
    def test_removed_top_rows_finds_the_header_by_rule(self):
        for title_lines in (0, 1, 3):
            raw = [["A title"]] * title_lines + [["Receipt", "Date"], ["R1", "2026-09-01"]]
            self.assertEqual(lesson.removed_top_rows(raw)[0], ["Receipt", "Date"],
                             "skip lines until the first cell is Receipt, whatever their number (%d)" % title_lines)
        with self.assertRaises(ValueError, msg="a file with no header row should raise ValueError"):
            lesson.removed_top_rows([["no header"], ["here"]])

    def test_promoted_headers_and_short_rows(self):
        got = lesson.promoted_headers([["Receipt", "Date", "Units"], ["R1", "2026-09-01", "2"], ["Total"]])
        self.assertEqual(got, [{"Receipt": "R1", "Date": "2026-09-01", "Units": "2"},
                               {"Receipt": "Total", "Date": "", "Units": ""}], "pad short rows with empty cells")
        self.assertEqual(lesson.promoted_headers([["Receipt", "Date"]]), [], "a header with no rows is an empty table")

    def test_renamed_columns(self):
        got = lesson.renamed_columns([{"Receipt": "R1", "Qty": "2", "Sales": "9.99", "Store name": "X"}])
        self.assertEqual(got, [{"Receipt": "R1", "Units": "2", "Revenue": "9.99", "Store": "X"}])
        same = [{"Receipt": "R1", "Units": "2", "Revenue": "9.99", "Store": "X"}]
        self.assertEqual(lesson.renamed_columns(same), same, "a file that already uses the names is left alone")

    def test_trim_capitalize_filter(self):
        t = lesson.trimmed_text([{"Receipt": " R1 ", "Store": "  old   TOWN ", "Units": None}])
        self.assertEqual(t, [{"Receipt": "R1", "Store": "old TOWN", "Units": ""}], "a missing cell (None) becomes ''")
        self.assertEqual(lesson.capitalized_each_word(t)[0]["Store"], "Old Town")
        rows = [{"Receipt": "R1"}, {"Receipt": ""}, {"Receipt": "Total"}, {"Receipt": "R2"}]
        self.assertEqual([r["Receipt"] for r in lesson.filtered_rows(rows)], ["R1", "R2"],
                         "drop blank lines and the Total line")
        self.assertEqual(lesson.filtered_rows([]), [])

    def test_changed_type(self):
        rows = [{"Receipt": "R1", "Date": "14/09/2026", "Units": "2", "Revenue": "$1,204.50"},
                {"Receipt": "R2", "Date": "Sep 03, 2026", "Units": "1", "Revenue": "0.00"},
                {"Receipt": "R3", "Date": "2026-09-30", "Units": "3", "Revenue": "89.97"}]
        got = lesson.changed_type(rows)
        self.assertEqual([(r["Date"], r["Units"], r["Revenue"]) for r in got],
                         [("2026-09-14", 2, 1204.5), ("2026-09-03", 1, 0.0), ("2026-09-30", 3, 89.97)],
                         "three date formats (slashes day first), money with $ and commas, and a zero kept")
        for bad in ({"Receipt": "R9", "Date": "TBD", "Units": "1", "Revenue": "1"},
                    {"Receipt": "R9", "Date": "2026-09-01", "Units": "two", "Revenue": "1"}):
            with self.assertRaises(ValueError, msg="an unreadable cell should raise ValueError, not be guessed"):
                lesson.changed_type([bad])

    def test_removed_duplicates_and_added_custom(self):
        rows = [{"Receipt": "R1", "Date": "2026-09-01", "Store": "A", "Product": "P", "Units": 1, "Revenue": 5.0},
                {"Receipt": "R1", "Date": "2026-09-01", "Store": "A", "Product": "P", "Units": 1, "Revenue": 5.0},
                {"Receipt": "R2", "Date": "2026-10-02", "Store": "A", "Product": "P", "Units": 1, "Revenue": 5.0}]
        dedup = lesson.removed_duplicates(rows)
        self.assertEqual([r["Receipt"] for r in dedup], ["R1", "R2"])
        out = lesson.added_custom(dedup)
        self.assertEqual(list(out[0]), ["Receipt", "Date", "Month", "Store", "Product", "Units", "Revenue"])
        self.assertEqual([r["Month"] for r in out], ["2026-09", "2026-10"])


class TestAppendAndPivot(unittest.TestCase):
    def test_appended_fills_missing_columns_with_none(self):
        got = lesson.appended([[{"Receipt": "R1", "Units": 2}], [{"Receipt": "R2", "Qty": 3}]])
        self.assertEqual(got, [{"Receipt": "R1", "Units": 2, "Qty": None}, {"Receipt": "R2", "Units": None, "Qty": 3}],
                         "like Table.Combine: the union of the columns, None where a table lacks one")
        self.assertEqual(lesson.appended([]), [])

    def test_pivot_small(self):
        rows = [{"Store": "A", "Month": "m1", "Revenue": 10.0}, {"Store": "A", "Month": "m1", "Revenue": 5.0},
                {"Store": "B", "Month": "m2", "Revenue": 0.0}, {"Store": "B", "Month": "m1", "Revenue": None}]
        p = lesson.pivot(rows)
        self.assertEqual(p["cells"], {("A", "m1"): 15.0, ("B", "m2"): 0.0},
                         "sum per store and month, a None is skipped, a real zero is kept, no row means no cell")
        self.assertEqual((p["rows"], p["columns"]), (["A", "B"], ["m1", "m2"]))
        self.assertEqual(p["row_totals"], {"A": 15.0, "B": 0.0})
        self.assertEqual(p["column_totals"], {"m1": 15.0, "m2": 0.0})
        self.assertEqual(p["grand_total"], 15.0)
        empty = lesson.pivot([])
        self.assertEqual((empty["cells"], empty["grand_total"]), ({}, 0))


class MonthChecks:
    raw = truth = None

    def test_each_month_cleans_to_the_true_receipts(self):
        for name in sorted(self.raw):
            table, log = lesson.apply_steps(self.raw[name])
            self.assertEqual([n for n, _ in log], STEP_NAMES)
            self.assertEqual(len(table), len(self.truth[name]),
                             "%s: wrong number of receipts after the steps; check Filtered Rows and Removed Duplicates"
                             % name)
            self.assertEqual(table, self.truth[name], "%s: cleaned rows differ from the true receipts" % name)

    def test_combine_then_pivot(self):
        tables = [lesson.apply_steps(self.raw[n])[0] for n in sorted(self.raw)]
        rows = [r for n in sorted(self.truth) for r in self.truth[n]]
        combined = lesson.combine(tables)
        self.assertEqual(len(combined), len(rows))
        again = lesson.combine(tables + tables[-1:])
        self.assertEqual(len(again), len(rows), "appending the last month twice must not add rows")
        for values in ("Revenue", "Units"):
            p = lesson.pivot(again, "Store", "Month", values)
            self.assertEqual(p["cells"], ref_pivot(rows, "Store", "Month", values), "pivot of %s by store and month"
                             % values)
            self.assertAlmostEqual(p["grand_total"], sum(r[values] for r in rows), places=2)


class TestCommittedMonths(MonthChecks, unittest.TestCase):
    truth = make_data.truth(make_data.DEFAULT_SEED)
    raw = {name: read_raw(name) for name in truth}

    def test_the_two_files_really_differ(self):
        heads = [lesson.removed_top_rows(self.raw[n])[0] for n in sorted(self.raw)]
        self.assertNotEqual(heads[0], heads[1])


class TestOtherSeed(MonthChecks, unittest.TestCase):
    """Two months in other export styles, built in memory."""
    raw, truth = make_data.build(OTHER_SEED), make_data.truth(OTHER_SEED)


class TestRefreshFolder(unittest.TestCase):
    def test_refresh_reads_every_file_in_the_folder(self):
        raw, truth = make_data.build(OTHER_SEED), make_data.truth(OTHER_SEED)
        with tempfile.TemporaryDirectory() as d:
            for name, lines in raw.items():
                with open(os.path.join(d, name + ".csv"), "w", newline="") as f:
                    csv.writer(f).writerows(lines)
            got = lesson.refresh(d)
        want = [r for n in sorted(truth) for r in truth[n]]
        self.assertEqual(got, want, "refresh(folder) should clean and append every sales_*.csv file in name order")


if __name__ == "__main__":
    unittest.main()
