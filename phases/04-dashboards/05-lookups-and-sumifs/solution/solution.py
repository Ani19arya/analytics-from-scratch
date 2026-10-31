"""Lesson 05: lookups and SUMIFS like Excel. Worked answer.

Run from the lesson folder: python3 solution/solution.py"""
import csv
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
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
    if table and not 1 <= col_index <= len(table[0]):
        raise ValueError("col_index %r is outside the table (#REF!)" % col_index)
    if exact:
        for row in table:
            if same_kind(row[0], key) and row[0] == key:
                return row[col_index - 1]
        return NA
    found = NA
    for row in table:
        if not same_kind(row[0], key):
            continue
        if row[0] > key:
            break
        found = row[col_index - 1]
    return found


def xlookup(key, lookup_array, return_array, if_not_found=NA):
    """XLOOKUP(key, lookup_array, return_array, if_not_found): exact match, first to last."""
    if len(lookup_array) != len(return_array):
        raise ValueError("lookup_array and return_array must be the same length")
    for k, v in zip(lookup_array, return_array):
        if same_kind(k, key) and k == key:
            return v
    return if_not_found


def normalize_key(value):
    """The Excel fix =VALUE(TRIM(cell)), written in Python.
    None or a blank cell -> None. 1042.0 -> 1042. ' 1042 ' -> 1042. 'C-7 ' -> 'C-7'."""
    if value is None:
        return None
    if is_number(value):
        return int(value) if float(value).is_integer() else value
    text = " ".join(str(value).split())
    if text == "":
        return None
    if text.isdigit():
        return int(text)
    return text


OPERATORS = (">=", "<=", "<>", ">", "<", "=")


def _matches(cell, criterion):
    """Does one cell pass one criterion? A number or a number after an operator
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
    if len(pairs) % 2:
        raise ValueError("criteria come in pairs: a range, then a criterion")
    ranges, criteria = pairs[0::2], pairs[1::2]
    for r in ranges:
        if len(r) != len(sum_range):
            raise ValueError("every criteria range must be as long as sum_range (#VALUE!)")
    total = 0.0
    for i, value in enumerate(sum_range):
        if not is_number(value):
            continue
        if all(_matches(r[i], c) for r, c in zip(ranges, criteria)):
            total += value
    return round(total, 2)


def finance_total(orders):
    """What finance reports: every order's amount, no lookup involved."""
    return round(sum(o["amount"] for o in orders), 2)


def customer_table(customers):
    """The master as a VLOOKUP range: [customer_id, customer_name, region] rows."""
    return [[c["customer_id"], c["customer_name"], c["region"]] for c in customers]


def naive_region_totals(orders, customers, exact=True):
    """What the old sheet did: =VLOOKUP(customer_id, Customers, 3, exact) on the raw key,
    then =SUMIFS(amount, region, "North") for each region. Rows that return #N/A fall out."""
    table = customer_table(customers)
    region_col = [vlookup(o["customer_id"], table, 3, exact) for o in orders]
    amounts = [o["amount"] for o in orders]
    return {r: sumifs(amounts, region_col, r) for r in REGIONS}


def duplicate_keys(customers):
    """Cleaned customer ids that appear more than once in the master, sorted."""
    seen, dups = set(), set()
    for c in customers:
        k = normalize_key(c["customer_id"])
        if k in seen:
            dups.add(k)
        seen.add(k)
    return sorted(dups, key=str)


def assign_region(key, customers):
    """Region for one cleaned key: the region, AMBIGUOUS if the master lists it twice,
    UNMATCHED if it is not there. Same as
    =IF(COUNTIF(ids, key) > 1, "Ambiguous", XLOOKUP(key, ids, regions, "Unmatched"))."""
    ids = [normalize_key(c["customer_id"]) for c in customers]
    if key is not None and ids.count(key) > 1:
        return AMBIGUOUS
    return xlookup(key, ids, [c["region"] for c in customers], UNMATCHED)


def region_totals(orders, customers):
    """The fixed sheet: clean both keys, then look up. Every order lands in exactly one
    bucket: a region, AMBIGUOUS or UNMATCHED. The buckets add up to finance_total."""
    region_col = [assign_region(normalize_key(o["customer_id"]), customers) for o in orders]
    amounts = [o["amount"] for o in orders]
    return {r: sumifs(amounts, region_col, r) for r in REGIONS + [AMBIGUOUS, UNMATCHED]}


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
