"""Tests for lesson 08-05: query cost in a cloud warehouse.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The expected answers are computed here in plain Python on their own: dates
compared as datetime.date objects, the bytes of each block summed column by
column, and the fictional rate card applied by hand. Your functions run on
three kinds of data:
1. the committed data/blocks.csv and data/queries.csv,
2. a second table and query log built in memory with
   make_data.build(seed=2027), with other block sizes, store ranges and run
   counts, so typing out the dollar figures cannot pass,
3. tiny hand-made blocks and queries: no blocks at all, a date range with no
   partitions (still billed the minimum), a store on the boundary two blocks
   share, an open-ended date range, a filter that is not prunable, a store
   filter on a table that is not clustered, and an unknown layout.
"""
import datetime
import importlib.util
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_data  # noqa: E402

TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

SECOND_SEED = 2027
LAYOUTS = ["none", "partitioned", "clustered"]
PRICE, MIN_BYTES, TIB = 5.00, 10 * 1024 * 1024, 1024 ** 4


# Reference answers.

def as_date(text):
    return datetime.date(*(int(x) for x in text.split("-"))) if text else None


def ref_reads(block, q, layout):
    day = as_date(block["event_date"])
    lo, hi = as_date(q["date_from"]), as_date(q["date_to"])
    if layout != "none" and q["prunable"]:
        if (lo and day < lo) or (hi and day > hi):
            return False
    if layout == "clustered" and q["store_id"] is not None:
        if q["store_id"] < block["min_store"] or q["store_id"] > block["max_store"]:
            return False
    return True


def ref_bytes(blocks, q, layout):
    total = 0
    for b in blocks:
        if ref_reads(b, q, layout):
            for c in q["columns"]:
                total += b["bytes"][c]
    return total


def ref_cost(scanned):
    return (scanned if scanned > MIN_BYTES else MIN_BYTES) * PRICE / TIB


def ref_dashboards(blocks, queries, layout):
    out = {}
    for q in queries:
        out.setdefault(q["dashboard"], 0.0)
        out[q["dashboard"]] += ref_cost(ref_bytes(blocks, q, layout)) * q["runs"]
    return out


def from_build(seed):
    t = make_data.build(seed)
    return ([lesson.parse_block({k: str(v) for k, v in r.items()}) for r in t["blocks"]],
            [lesson.parse_query({k: str(v) for k, v in r.items()}) for r in t["queries"]])


def block(day, lo, hi, nbytes, bid=1):
    return {"event_date": day, "block_id": bid, "rows": 10, "min_store": lo, "max_store": hi,
            "bytes": {"a": nbytes, "b": 2 * nbytes}}


def query(cols, lo=None, hi=None, prunable=True, store=None, runs=1, dash="D"):
    return {"query_id": "x", "dashboard": dash, "tile": "t", "sql": "", "columns": cols, "date_from": lo,
            "date_to": hi, "prunable": prunable, "store_id": store, "runs": runs}


class CostTest(unittest.TestCase):
    def call(self, fn, *args):
        try:
            return getattr(lesson, fn)(*args)
        except NotImplementedError:
            self.fail("%s is not written yet: fill it in in exercise.py" % fn)

    def check(self, blocks, queries, label):
        for q in queries:
            for layout in LAYOUTS:
                want = ref_bytes(blocks, q, layout)
                got = self.call("bytes_scanned", blocks, q, layout)
                self.assertEqual(got, want, "%s: %s (%s) under layout %r should scan %d bytes, not %s: read only its columns, in the blocks pruning cannot skip" % (label, q["query_id"], q["tile"], layout, want, got))
                self.assertAlmostEqual(self.call("run_cost", got), ref_cost(want), 9, "%s: run_cost(%d) should be %.6f dollars" % (label, want, ref_cost(want)))
        for layout in LAYOUTS:
            want = ref_dashboards(blocks, queries, layout)
            got = self.call("dashboard_costs", blocks, queries, layout)
            self.assertEqual(sorted(got), sorted(want), "%s: dashboard_costs needs one entry per dashboard in the log" % label)
            for d, v in want.items():
                self.assertAlmostEqual(got[d], round(v, 2), 2, "%s: %s under %r should cost %.2f dollars (cost per run times runs, summed over its tiles)" % (label, d, layout, v))

    def test_committed_data(self):
        blocks, queries = lesson.read_blocks(), lesson.read_queries()
        self.check(blocks, queries, "committed data")
        got = self.call("dashboard_costs", blocks, queries, "clustered")
        self.assertGreater(got["Store live ops"], 400, "committed data: Store live ops should cost over 400 dollars even on the clustered table")
        q1 = queries[0]
        self.assertEqual(self.call("bytes_scanned", blocks, q1, "clustered"), self.call("bytes_scanned", blocks, q1, "none"),
                         "q1 filters on DATE(event_time), not on event_date, so partitions cannot help it")

    def test_second_dataset(self):
        blocks, queries = from_build(SECOND_SEED)
        self.check(blocks, queries, "seed %d" % SECOND_SEED)

    def test_edge_cases(self):
        blocks = [block("2026-10-01", 1, 5, 100, 1), block("2026-10-01", 5, 9, 1000, 2), block("2026-10-02", 1, 9, 10000, 1)]
        cases = [
            (query(["a"]), "none", 11100, "no filter reads every block"),
            (query(["a", "b"]), "none", 33300, "two columns read both columns' bytes"),
            (query(["a"], "2026-10-02", "2026-10-02"), "none", 11100, "layout 'none' never skips a block"),
            (query(["a"], "2026-10-02", "2026-10-02"), "partitioned", 10000, "one day: only that day's partition"),
            (query(["a"], "2026-10-02", "2026-10-02", prunable=False), "clustered", 11100, "a filter not written on event_date cannot prune"),
            (query(["a"], "2026-10-02", None), "partitioned", 10000, "date_from with no date_to: open end"),
            (query(["a"], None, "2026-10-01"), "partitioned", 1100, "date_to with no date_from: open start, both ends included"),
            (query(["a"], store=5), "clustered", 11100, "store 5 is on the boundary two blocks share, so both are read"),
            (query(["a"], store=2), "clustered", 10100, "store 2 can only be in the first block of 1 Oct, and in 2 Oct's only block"),
            (query(["a"], store=2), "partitioned", 11100, "a partitioned table that is not clustered cannot skip by store"),
            (query(["a"], "2026-10-01", "2026-10-01", store=9), "clustered", 1000, "date and store pruning together"),
            (query(["a"], "2026-11-01", "2026-11-30"), "clustered", 0, "a range with no partitions scans nothing"),
        ]
        for q, layout, want, why in cases:
            self.assertEqual(self.call("bytes_scanned", blocks, q, layout), want, "%s: expected %d bytes under %r" % (why, want, layout))
        self.assertEqual(self.call("bytes_scanned", [], query(["a"]), "clustered"), 0, "no blocks, no bytes")
        self.assertAlmostEqual(self.call("run_cost", 0), MIN_BYTES * PRICE / TIB, 12, "a query that scans nothing is still billed the 10 MiB minimum")
        self.assertAlmostEqual(self.call("run_cost", TIB), 5.0, 9, "one TiB costs 5.00 dollars on the rate card")
        self.assertAlmostEqual(self.call("run_cost", 2 * TIB), 10.0, 9, "cost is linear above the minimum")
        with self.assertRaises(ValueError, msg="an unknown layout must raise ValueError"):
            self.call("block_survives", blocks[0], query(["a"]), "sorted")
        self.assertEqual(self.call("dashboard_costs", blocks, [], "none"), {}, "an empty log costs nothing")
        two = [query(["a"], runs=0, dash="Zero"), query(["a"], runs=3, dash="Zero")]
        self.assertAlmostEqual(self.call("dashboard_costs", [block("2026-10-01", 1, 1, TIB)], two, "none")["Zero"], 15.0, 2,
                               "a tile that never ran costs 0; 3 runs of 1 TiB cost 15.00")


if __name__ == "__main__":
    unittest.main(verbosity=2)
