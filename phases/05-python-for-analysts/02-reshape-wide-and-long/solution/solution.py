"""Solution: pivot a long table to wide and back with csv and dict only."""
import csv
import os

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def load_csv(name, data_dir=DATA):
    with open(os.path.join(data_dir, name), newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def pivot_wider(rows, index, columns, values):
    """Long to wide. Returns (header, wide_rows).

    One output row per distinct value of `index`, one column per distinct value of
    `columns`, both in order of first appearance. A missing pair becomes "".
    Two input rows for the same pair raise ValueError instead of overwriting.
    """
    row_keys, col_keys, cells = [], [], {}
    for r in rows:
        i, c = r[index], r[columns]
        if i not in row_keys:
            row_keys.append(i)
        if c not in col_keys:
            col_keys.append(c)
        if (i, c) in cells:
            raise ValueError("two rows for %s=%s, %s=%s" % (index, i, columns, c))
        cells[(i, c)] = r[values]
    header = [index] + col_keys
    wide = []
    for i in row_keys:
        out = {index: i}
        for c in col_keys:
            out[c] = cells.get((i, c), "")
        wide.append(out)
    return header, wide


def pivot_longer(wide_rows, id_col, var_name, value_name):
    """Wide to long. Every non-id column becomes a row; empty cells are skipped."""
    long_rows = []
    for r in wide_rows:
        for col, val in r.items():
            if col == id_col or val == "":
                continue
            long_rows.append({id_col: r[id_col], var_name: col, value_name: val})
    return long_rows


def total_by(long_rows, key, value):
    """Sum `value` for each distinct `key`. One loop, whatever the key is."""
    out = {}
    for r in long_rows:
        out[r[key]] = out.get(r[key], 0) + int(r[value])
    return out


def main():
    long_rows = load_csv("sales_long.csv")
    header, wide = pivot_wider(long_rows, "region", "month", "revenue")
    print(",".join(header))
    for r in wide:
        print(",".join(str(r[h]) for h in header))
    back = pivot_longer(wide, "region", "month", "revenue")
    print("long rows in:", len(long_rows), " long rows back:", len(back), " same:", back == long_rows)
    print("total by month:", total_by(long_rows, "month", "revenue"))


if __name__ == "__main__":
    main()
