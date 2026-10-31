"""Lesson 08-05 solution: a bytes-scanned cost model with partition and cluster pruning."""
import csv
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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


# The cost model.

def block_survives(block, query, layout):
    """True when the warehouse must read this block for this query under this layout."""
    if layout not in LAYOUTS:
        raise ValueError("layout must be one of %s, not %r" % (", ".join(LAYOUTS), layout))
    if layout in ("partitioned", "clustered") and query["prunable"]:
        if query["date_from"] is not None and block["event_date"] < query["date_from"]:
            return False
        if query["date_to"] is not None and block["event_date"] > query["date_to"]:
            return False
    if layout == "clustered" and query["store_id"] is not None:
        if not block["min_store"] <= query["store_id"] <= block["max_store"]:
            return False
    return True


def bytes_scanned(blocks, query, layout):
    """Bytes read: the query's columns, in every block that survives pruning."""
    return sum(b["bytes"][c] for b in blocks if block_survives(b, query, layout) for c in query["columns"])


def run_cost(scanned):
    """Dollars for one run that scans this many bytes, on the fictional rate card."""
    return max(scanned, MIN_BILLED_BYTES) / TIB * PRICE_PER_TIB


def dashboard_costs(blocks, queries, layout):
    """{dashboard: dollars for all its runs in the log}, each rounded to cents."""
    out = {}
    for q in queries:
        out[q["dashboard"]] = out.get(q["dashboard"], 0.0) + run_cost(bytes_scanned(blocks, q, layout)) * q["runs"]
    return {d: round(v, 2) for d, v in out.items()}


if __name__ == "__main__":
    blocks, queries = read_blocks(), read_queries()
    for layout in LAYOUTS:
        print(layout, dashboard_costs(blocks, queries, layout))
    for q in queries:
        print(q["query_id"], q["tile"].ljust(28), ["%.2f" % (run_cost(bytes_scanned(blocks, q, l)) * q["runs"]) for l in LAYOUTS])
