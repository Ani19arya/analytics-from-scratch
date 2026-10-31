"""Lesson 05: lookups and SUMIFS like Excel. Your turn.

read_sheet, is_number, same_kind, _matches, finance_total, customer_table and main are
done for you. Fill in every function that raises NotImplementedError.
Run from this folder: python3 test_lesson.py"""
import csv
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
NA = "#N/A"
REGIONS = ["North", "South", "East", "West"]
AMBIGUOUS, UNMATCHED = "Ambiguous", "Unmatched"


def read_sheet(name, data_dir=DATA):
    """Read a CSV where quoted cells are text and unquoted cells are numbers (floats)."""
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f, quoting=csv.QUOTE_NONNUMERIC))


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def same_kind(a, b):
    """True when a and b can be compared: two numbers, or two pieces of text."""
    return (is_number(a) and is_number(b)) or (isinstance(a, str) and isinstance(b, str))


def vlookup(key, table, col_index, exact=True):
    """VLOOKUP(key, table, col_index, exact) on a list of rows (lists or tuples).

    Looks in the first column. col_index counts from 1, like Excel.
    exact=True: the FIRST row whose first cell equals key. A number never equals text.
    exact=False: the first column must be sorted ascending; returns the row with the
    largest first cell <= key (on duplicates, the last of them). NA if none.
    A col_index outside the row raises ValueError (Excel shows #REF!)."""
    # TODO: check col_index, then exact (first equal row) or approximate (last row with first cell <= key)
    raise NotImplementedError


def xlookup(key, lookup_array, return_array, if_not_found=NA):
    """XLOOKUP(key, lookup_array, return_array, if_not_found): exact match, first to last."""
    # TODO: walk both lists together, return the first value whose key equals key
    raise NotImplementedError


def normalize_key(value):
    """The Excel fix =VALUE(TRIM(cell)), written in Python.
    None or a blank cell -> None. 1042.0 -> 1042. ' 1042 ' -> 1042. 'C-7 ' -> 'C-7'."""
    # TODO: None stays None, whole floats become int, text is trimmed and digits become int
    raise NotImplementedError


OPERATORS = (">=", "<=", "<>", ">", "<", "=")


def _matches(cell, criterion):
    """Does one cell pass one criterion? Done for you. A number or a number after an operator
    ('>=10') compares as a number; plain text compares exactly, with = or <> only."""
    op, target = "=", criterion
    if isinstance(criterion, str):
        for candidate in OPERATORS:
            if criterion.startswith(candidate):
                op, target = candidate, criterion[len(candidate):]
                break
        try:
            target = float(target)
        except ValueError:
            pass
    if is_number(target):
        if not is_number(cell):
            return op == "<>"
        a, b = float(cell), float(target)
    else:
        if op not in ("=", "<>"):
            raise ValueError("text criteria support only = and <>, got %r" % criterion)
        a, b = ("" if cell is None else str(cell)), target
    return {"=": a == b, "<>": a != b, ">": a > b, ">=": a >= b, "<": a < b, "<=": a <= b}[op]


def sumifs(sum_range, *pairs):
    """SUMIFS(sum_range, criteria_range1, criterion1, ...).
    Adds the numbers in sum_range on rows where EVERY criterion holds. A criterion is a
    value (equals) or text with an operator in front: '>=10', '<>West'. Text and empty
    cells in sum_range are skipped. Every range must be as long as sum_range."""
    # TODO: check the pairs and the range lengths, then add every number whose row passes all _matches
    raise NotImplementedError


def finance_total(orders):
    """What finance reports: every order's amount, no lookup involved."""
    return round(sum(o["amount"] for o in orders), 2)


def customer_table(customers):
    """The master as a VLOOKUP range: [customer_id, customer_name, region] rows."""
    return [[c["customer_id"], c["customer_name"], c["region"]] for c in customers]


def naive_region_totals(orders, customers, exact=True):
    """What the old sheet did: =VLOOKUP(customer_id, Customers, 3, exact) on the raw key,
    then =SUMIFS(amount, region, "North") for each region. Rows that return #N/A fall out."""
    # TODO: vlookup each raw customer_id in customer_table(customers), column 3, then sumifs per region
    raise NotImplementedError


def duplicate_keys(customers):
    """Cleaned customer ids that appear more than once in the master, sorted."""
    # TODO: normalize each customer_id and collect the ones seen before
    raise NotImplementedError


def assign_region(key, customers):
    """Region for one cleaned key: the region, AMBIGUOUS if the master lists it twice,
    UNMATCHED if it is not there. Same as
    =IF(COUNTIF(ids, key) > 1, "Ambiguous", XLOOKUP(key, ids, regions, "Unmatched"))."""
    # TODO: AMBIGUOUS if the cleaned id appears more than once, else xlookup with UNMATCHED
    raise NotImplementedError


def region_totals(orders, customers):
    """The fixed sheet: clean both keys, then look up. Every order lands in exactly one
    bucket: a region, AMBIGUOUS or UNMATCHED. The buckets add up to finance_total."""
    # TODO: assign_region(normalize_key(...)) for every order, then sumifs for every bucket
    raise NotImplementedError


def main():
    orders, customers = read_sheet("orders.csv"), read_sheet("customers.csv")
    print("finance total:", format(finance_total(orders), ",.2f"))
    naive = naive_region_totals(orders, customers)
    print("old sheet, exact match:", {r: format(v, ",.2f") for r, v in naive.items()})
    print("old sheet adds up to:", format(sum(naive.values()), ",.2f"))
    fixed = region_totals(orders, customers)
    print("fixed sheet:", {r: format(v, ",.2f") for r, v in fixed.items()})
    print("fixed sheet adds up to:", format(sum(fixed.values()), ",.2f"))
    print("listed twice in the master:", duplicate_keys(customers))


if __name__ == "__main__":
    main()
