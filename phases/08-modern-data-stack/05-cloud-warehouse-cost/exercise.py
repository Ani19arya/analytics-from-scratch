"""Query cost in a cloud warehouse: bytes scanned, partitions and clustering.

Exercise. The helpers and the rate card at the top are done for you. Write the
four functions marked TODO, then run: python3 test_lesson.py

Python 3.9+ standard library only.

The table app_events is stored in blocks (data/blocks.csv). Each block belongs
to one event_date partition, holds a range of store_id values (min_store to
max_store, both included), and stores each column separately, so a query pays
only for the columns it reads, in the blocks it cannot skip.

Layouts, from least to most the warehouse can skip:
  "none"         read every block
  "partitioned"  skip blocks outside the query's event_date range, but only
                 when the query's date filter is prunable (written on event_date)
  "clustered"    as "partitioned", and also skip blocks whose store range
                 cannot contain the query's store_id
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# A FICTIONAL rate card for this lesson. It is not any real warehouse's price.
PRICE_PER_TIB = 5.00             # dollars per tebibyte scanned
MIN_BILLED_BYTES = 10 * 2 ** 20  # every query is billed at least 10 MiB
TIB = 2 ** 40
LAYOUTS = ("none", "partitioned", "clustered")


# Given helpers.

def read_blocks(data_dir=DATA):
    """One dict per block: event_date (text), block_id, rows, min_store, max_store (ints),
    and bytes[column] (int) for every column."""
    out = []
    with open(os.path.join(data_dir, "blocks.csv"), newline="") as f:
        for r in csv.DictReader(f):
            out.append(parse_block(r))
    return out


def parse_block(r):
    return {"event_date": r["event_date"], "block_id": int(r["block_id"]), "rows": int(r["rows"]),
            "min_store": int(r["min_store"]), "max_store": int(r["max_store"]),
            "bytes": {k[6:]: int(v) for k, v in r.items() if k.startswith("bytes_")}}


def read_queries(data_dir=DATA):
    """One dict per query: columns (list), date_from and date_to (text or None),
    prunable (bool), store_id (int or None), runs (int), plus the text fields."""
    with open(os.path.join(data_dir, "queries.csv"), newline="") as f:
        return [parse_query(r) for r in csv.DictReader(f)]


def parse_query(r):
    return {"query_id": r["query_id"], "dashboard": r["dashboard"], "tile": r["tile"], "sql": r["sql"],
            "columns": [c for c in str(r["columns"]).split(";") if c],
            "date_from": r["date_from"] or None, "date_to": r["date_to"] or None,
            "prunable": str(r["prunable"]) == "1",
            "store_id": int(r["store_id"]) if str(r["store_id"]) != "" else None,
            "runs": int(r["runs"])}


# The cost model. Your turn.

def block_survives(block, query, layout):
    """True when the warehouse must read this block for this query under this layout.
    A missing date_from or date_to means that end is open. Raise ValueError for an unknown layout."""
    raise NotImplementedError("TODO: block_survives")


def bytes_scanned(blocks, query, layout):
    """Bytes read: the query's columns, in every block that survives pruning."""
    raise NotImplementedError("TODO: bytes_scanned")


def run_cost(scanned):
    """Dollars for one run that scans this many bytes, on the fictional rate card above
    (every run is billed at least MIN_BILLED_BYTES)."""
    raise NotImplementedError("TODO: run_cost")


def dashboard_costs(blocks, queries, layout):
    """{dashboard: dollars for all of its runs in the log}, each total rounded to cents."""
    raise NotImplementedError("TODO: dashboard_costs")
