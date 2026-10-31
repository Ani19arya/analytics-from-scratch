# Pivot tables and Power Query steps

Can next month's file be cleaned and merged with one click?

## Before you start

- **Level:** 1 (beginner). About 2 hours.
- **You need:** Python 3.9 or newer. Nothing to install. Excel or Power BI only if you want to compare with the reference at the end of the walk through.
- **Builds on:** [01 Clean a messy CSV](../../05-python-for-analysts/01-clean-a-messy-csv/) (trimming, date formats, money strings, duplicates), [02 Reshape wide and long](../../05-python-for-analysts/02-reshape-wide-and-long/) (stores down the side, months across the top) and [05 Lookups and SUMIFS](../05-lookups-and-sumifs/) (checking a total against its source).

## The problem

Tidewater Outdoor, a fictional camping gear shop, has four stores. Every month Marcus, the operations manager, downloads the sales export from the tills and builds a pivot table of revenue by store and month for the owners' Monday call. September took him an afternoon of deleting lines and fixing store names by hand. October's file arrived with two title lines on top, different column names and dates written day first, so the afternoon started again. Marcus asks for a way to drop November's file in a folder on 1 December and click Refresh.

The two files in `data/` are synthetic, built by `make_data.py` with a fixed seed: `sales_2026-09.csv` (129 lines) and `sales_2026-10.csv` (126 lines). Their mess was added on purpose and differs between the months.

## In plain words

Think of a recipe card. "Wash the rice, soak it 20 minutes, cook it with twice the water" works on any bag of rice. "Pick out the third and fifth grains" works on one bag only. A cleaning recipe for a monthly file should be the first kind: rules that describe what to do, not edits to particular cells.

- **Power Query** is the data cleaning tool built into Excel and Power BI. You click through cleaning actions once, it records each one as a **step**, and it replays all of them when you click Refresh.
- **Applied Steps** is the list of recorded steps, in order, each with a name such as "Promoted Headers" or "Filtered Rows". Microsoft's page on it is [Applied Steps](https://learn.microsoft.com/en-us/power-query/applied-steps) (read 31 October 2026).
- **M** is the formula language Power Query writes each step in. You never have to type it, but you can read it.
- To **append** is to stack one table under another, like sticking October's rows under September's.
- A **pivot table** summarises rows into a grid: one row per store, one column per month, and the sum of revenue where they cross, with totals.
- A **refresh** reruns the steps on whatever files are there now.

## What you will build from scratch

- Nine named steps, each a small function that takes a table and returns a new one: `removed_top_rows`, `promoted_headers`, `renamed_columns`, `trimmed_text`, `capitalized_each_word`, `filtered_rows`, `changed_type`, `removed_duplicates` and `added_custom`.
- `apply_steps`: runs the list in order and logs how many rows are left after each step.
- `appended` and `combine`: stack the months and remove repeated receipts.
- `pivot`: revenue by store and month, with row, column and grand totals.
- `refresh`: every monthly file in a folder, cleaned and stacked: the one click.

## The idea

A step is a function from a table to a table. A query is a list of steps. Because each step is a rule ("drop rows whose Receipt is Total"), not an edit ("delete line 137"), the same list works on a file it has never seen.

```mermaid
flowchart LR
    subgraph month["Each monthly file, the same nine steps"]
        direction TB
        A["Source: lines of text"] --> B["Removed Top Rows<br/>until the line that starts Receipt"]
        B --> C["Promoted Headers"]
        C --> D["Renamed Columns<br/>Qty to Units, Sales to Revenue"]
        D --> E["Trimmed Text<br/>Capitalized Each Word"]
        E --> F["Filtered Rows<br/>no blanks, no Total"]
        F --> G["Changed Type<br/>dates, whole numbers, money"]
        G --> H["Removed Duplicates<br/>one row per receipt"]
        H --> I["Added Custom: Month"]
    end
    I --> J["Appended: Sep + Oct + Nov ..."]
    J --> K["Removed Duplicates again"]
    K --> L["Pivot: Store by Month"]
```

Three rules make a step list survive next month:

1. **Find things by rule, not by position.** "Skip lines until the one whose first cell is Receipt" works with zero, one or two title lines. "Skip 2 lines" works for October only. Power Query's `Table.Skip` takes either a count or a condition, and with a condition it skips rows while the condition holds ([Table.Skip](https://learn.microsoft.com/en-us/powerquery-m/table-skip), read 31 October 2026).
2. **Make every month look the same before you stack them.** September says Units and Revenue, October says Qty and Sales. Rename first. When Power Query appends tables whose columns differ, it keeps every column and fills the gaps with null ([Table.Combine](https://learn.microsoft.com/en-us/powerquery-m/table-combine), read 31 October 2026), so an unrenamed column does not fail loudly, it just goes empty.
3. **Remove what is not a receipt, then count each receipt once.** Exports add blank lines, a Total line and repeated lines. A Total line that survives into the pivot doubles the grand total, because the pivot adds it to the receipts it already summed.

The pivot itself is a grouped sum written out:

```
cell(store, month)  = sum of Revenue over rows with that Store and that Month
row total(store)    = sum over all months      column total(month) = sum over all stores
grand total         = sum of every Revenue     = sum of the row totals = sum of the column totals
```

A store and month with no sales has no cell: a blank, not a zero. A real receipt with zero revenue (a warranty swap) is kept and adds 0.

## Walk through

Run each block from this folder, in order, in one Python session (type `python3`, then paste). The block under each one is what it prints.

Step 1. Look at the raw files. `csv.reader` gives each line as a list of text cells. `raw[:4] + raw[-1:]` is the first four lines and the last one.

```python
import csv

def read_raw(path):
    with open(path, newline="") as f:
        return list(csv.reader(f))

sep, oct_ = read_raw("data/sales_2026-09.csv"), read_raw("data/sales_2026-10.csv")
for name, raw in (("September", sep), ("October", oct_)):
    print(name, len(raw), "lines")
    for line in raw[:4] + raw[-1:]:
        print("   ", line)
```

```text
September 129 lines
    ['Receipt', 'Date', 'Store', 'Product', 'Units', 'Revenue']
    ['R2609-0001', '2026-09-08', 'Riverside', 'Tents', '1', '$442.99']
    ['R2609-0002', '2026-09-14', 'Riverside', 'Sleeping Bags', '1', '$103.99']
    ['R2609-0003', '2026-09-24', 'Old Town', 'Jackets', '2', '$191.98']
    ['Total', '', '', '', '212', '$30,613.97']
October 126 lines
    ['Tidewater Outdoor point of sale export']
    ['Generated automatically, do not edit']
    ['Receipt', 'Date', 'Store name', 'Product', 'Qty', 'Sales']
    ['R2610-0001', '31/10/2026', 'harbor point', 'Sleeping Bags', '3', '332.97']
    ['Total', '', '', '', '185', '30815.24']
```

Same shop, same tills, two different files: October has title lines, three renamed columns, day-first dates, no dollar sign and lowercase store names. Both end with a Total line.

Step 2. The first two steps. `removed_top_rows` returns the file from the header line down, wherever the header is. `promoted_headers` pairs the header with each later line using `zip`, padding short lines (such as a one-cell title) with empty cells.

```python
def removed_top_rows(raw):
    for i, row in enumerate(raw):
        if row and row[0].strip() == "Receipt":
            return raw[i:]
    raise ValueError("no header row")

def promoted_headers(raw):
    header = raw[0]
    return [dict(zip(header, row + [""] * (len(header) - len(row)))) for row in raw[1:]]

table = promoted_headers(removed_top_rows(oct_))
print(len(table), "rows")
print(table[0])
```

```text
123 rows
{'Receipt': 'R2610-0001', 'Date': '31/10/2026', 'Store name': 'harbor point', 'Product': 'Sleeping Bags', 'Qty': '3', 'Sales': '332.97'}
```

Step 3. Rename and trim. `RENAMES.get(k, k)` returns the new name if there is one and the old name otherwise, so September's file passes through untouched. `" ".join(v.split())` trims the ends and collapses inner spaces.

```python
RENAMES = {"Qty": "Units", "Sales": "Revenue", "Store name": "Store"}

def renamed_columns(table):
    return [{RENAMES.get(k, k): v for k, v in row.items()} for row in table]

def trimmed_text(table):
    return [{k: " ".join(v.split()) for k, v in row.items()} for row in table]

table = trimmed_text(renamed_columns(table))
print(table[0])
print(sorted({row["Store"] for row in table}))
```

```text
{'Receipt': 'R2610-0001', 'Date': '31/10/2026', 'Store': 'harbor point', 'Product': 'Sleeping Bags', 'Units': '3', 'Revenue': '332.97'}
['', 'HARBOR POINT', 'Harbor Point', 'NORTH MALL', 'North Mall', 'OLD TOWN', 'Old Town', 'RIVERSIDE', 'Riverside', 'harbor point', 'old town', 'riverside']
```

Four stores are spelled twelve ways, counting the empty store of the blank and Total lines. A pivot would give each spelling its own row. The next step, Capitalized Each Word (`str.title()` in Python, `Text.Proper` in M), turns them into four.

Step 4. Filter, and look for repeats. A list comprehension with `if` keeps only the rows that pass.

```python
def filtered_rows(table):
    return [row for row in table if row["Receipt"] not in ("", "Total")]

before = len(table)
table = filtered_rows(table)
print(before, "->", len(table), "rows")
receipts = [row["Receipt"] for row in table]
print("receipts that appear twice:", sorted({r for r in receipts if receipts.count(r) > 1}))
```

```text
123 -> 120 rows
receipts that appear twice: ['R2610-0038', 'R2610-0107', 'R2610-0111']
```

Two blank lines and the Total line are gone. Three receipts are in the file twice: the export repeated them.

Step 5. The whole step list on both months. The worked answer in `solution/solution.py` holds all nine steps in a list called `STEPS`, and `apply_steps` runs them in order and records the row count after each one, the way you click down Applied Steps to see what each one did.

```python
import sys
sys.path.insert(0, "solution")
import solution as s

for path in ("data/sales_2026-09.csv", "data/sales_2026-10.csv"):
    clean, log = s.apply_steps(s.read_raw(path))
    print(path)
    for step, rows in log:
        print("   %-22s %4d" % (step, rows))
print(clean[0])
```

```text
data/sales_2026-09.csv
   Removed Top Rows        129
   Promoted Headers        128
   Renamed Columns         128
   Trimmed Text            128
   Capitalized Each Word   128
   Filtered Rows           126
   Changed Type            126
   Removed Duplicates      123
   Added Custom            123
data/sales_2026-10.csv
   Removed Top Rows        124
   Promoted Headers        123
   Renamed Columns         123
   Trimmed Text            123
   Capitalized Each Word   123
   Filtered Rows           120
   Changed Type            120
   Removed Duplicates      117
   Added Custom            117
{'Receipt': 'R2610-0001', 'Date': '2026-10-31', 'Month': '2026-10', 'Store': 'Harbor Point', 'Product': 'Sleeping Bags', 'Units': 3, 'Revenue': 332.97}
```

The same nine steps clean both files, although the files share almost nothing in format. September keeps 123 receipts and October 117. The last row is fully typed: a real date, a whole number of units, revenue as a number.

Step 6. Append and pivot. `combine` stacks the cleaned months and removes repeated receipts once more, in case the same month was appended twice. `render_pivot` prints the grid.

```python
months = [s.apply_steps(s.read_raw(p))[0] for p in ("data/sales_2026-09.csv", "data/sales_2026-10.csv")]
rows = s.combine(months)
print(len(rows), "receipts")
print(s.render_pivot(s.pivot(rows)))
```

```text
240 receipts
Store           2026-09    2026-10      Total
Harbor Point   6,209.55   7,594.53  13,804.08
North Mall     6,339.57   8,153.57  14,493.14
Old Town       8,795.43   6,123.66  14,919.09
Riverside      9,269.42   8,943.48  18,212.90
Total         30,613.97  30,815.24  61,429.21
```

The column totals, 30,613.97 and 30,815.24, equal the Total lines the tills printed at the bottom of each file. That is the check: the tills' own total, which the steps removed, agrees with the sum of the receipts they kept.

Step 7. The one click. Put September, October and a November file in a folder and call `refresh`. November is new to the steps: `make_data.month_raw` writes it in yet another style (Qty, but Revenue, dollar signs, dates year first).

```python
import os, tempfile, shutil
import make_data

folder = tempfile.mkdtemp()
for name in ("sales_2026-09.csv", "sales_2026-10.csv"):
    shutil.copy(os.path.join("data", name), folder)
with open(os.path.join(folder, "sales_2026-11.csv"), "w", newline="") as f:
    csv.writer(f).writerows(make_data.month_raw(make_data.DEFAULT_SEED, 2026, 11))

print(read_raw(os.path.join(folder, "sales_2026-11.csv"))[0])
print(s.render_pivot(s.pivot(s.refresh(folder))))
shutil.rmtree(folder)
```

```text
['Receipt', 'Date', 'Store', 'Product', 'Qty', 'Revenue']
Store           2026-09    2026-10    2026-11      Total
Harbor Point   6,209.55   7,594.53   6,676.63  20,480.71
North Mall     6,339.57   8,153.57   7,905.58  22,398.72
Old Town       8,795.43   6,123.66   8,745.51  23,664.60
Riverside      9,269.42   8,943.48   9,006.48  27,219.38
Total         30,613.97  30,815.24  32,334.20  93,763.41
```

No code changed. The new month got its own column. That is Marcus's 1 December.

Step 8. The same query in Power Query (reference only, not run in this course). In Excel: Data > Get Data > From File > From Folder, pick the folder, then Combine and Transform. Power Query asks for a sample file, records your steps on it, and replays them on every file in the folder before appending. The steps for one file, recorded as M, look like this:

```text
let
    Source = Csv.Document(File.Contents("C:\Tidewater\sales_2026-10.csv"), [Delimiter = ","]),
    #"Removed Top Rows" = Table.Skip(Source, each [Column1] <> "Receipt"),
    #"Promoted Headers" = Table.PromoteHeaders(#"Removed Top Rows"),
    #"Renamed Columns" = Table.RenameColumns(#"Promoted Headers",
        {{"Qty", "Units"}, {"Sales", "Revenue"}, {"Store name", "Store"}}, MissingField.Ignore),
    #"Trimmed Text" = Table.TransformColumns(#"Renamed Columns", {{"Store", Text.Trim}, {"Product", Text.Trim}}),
    #"Capitalized Each Word" = Table.TransformColumns(#"Trimmed Text", {{"Store", Text.Proper}}),
    #"Filtered Rows" = Table.SelectRows(#"Capitalized Each Word", each [Receipt] <> "" and [Receipt] <> "Total"),
    #"Changed Type" = Table.TransformColumnTypes(#"Filtered Rows",
        {{"Date", type date}, {"Units", Int64.Type}, {"Revenue", Currency.Type}}, "en-GB"),
    #"Removed Duplicates" = Table.Distinct(#"Changed Type", {"Receipt"}),
    #"Added Custom" = Table.AddColumn(#"Removed Duplicates", "Month", each Date.ToText([Date], "yyyy-MM"))
in
    #"Added Custom"

Pivot: Insert > PivotTable from the query's table. Rows = Store, Columns = Month,
Values = Sum of Revenue. Data > Refresh All reruns the query, then the pivot.
```

`MissingField.Ignore` lets the rename step skip a column the file does not have, so September's file passes through it ([Table.RenameColumns](https://learn.microsoft.com/en-us/powerquery-m/table-renamecolumns), read 31 October 2026). `"en-GB"` tells the type step to read slash dates day first. One difference from our Python: `Text.Trim` removes spaces at the ends only ([Text.Trim](https://learn.microsoft.com/en-us/powerquery-m/text-trim), read 31 October 2026), so a store typed as `North  Mall` with two inner spaces needs one more step, such as Replace Values of a double space with a single one.

## Common mistakes

**1. Fixing September by hand (the trap).** Deleting the three repeated lines by their line numbers works for September. Recorded as a macro, or remembered as "delete lines 26, 58 and 85", it does something else to October:

```python
import sys
sys.path.insert(0, "solution")
import solution as s

sep = s.read_raw("data/sales_2026-09.csv")
oct_ = s.read_raw("data/sales_2026-10.csv")

# September, fixed by hand: delete the repeated lines you spotted, by their line number.
repeats = [i for i in range(1, len(sep)) if sep[i] == sep[i - 1] and sep[i][0]]
print("lines deleted by hand in September:", repeats)

# November's analyst replays the same edits on October's file.
replayed = [line for i, line in enumerate(oct_) if i not in repeats]
print("October lines those numbers hit:", [oct_[i][0] or "(blank)" for i in repeats])

no_dedupe = [step for step in s.STEPS if step[0] != "Removed Duplicates"]
by_hand, _ = s.apply_steps(replayed, no_dedupe)
by_rule, _ = s.apply_steps(oct_)
print("October revenue, replayed edits:", round(sum(r["Revenue"] for r in by_hand), 2), "on", len(by_hand), "rows")
print("October revenue, the steps:     ", round(sum(r["Revenue"] for r in by_rule), 2), "on", len(by_rule), "rows")
```

```text
lines deleted by hand in September: [26, 58, 85]
October lines those numbers hit: ['R2610-0024', '(blank)', 'R2610-0080']
October revenue, replayed edits: 30946.23 on 118 rows
October revenue, the steps:      30815.24 on 117 rows
```

The replayed edits delete two real October receipts and a blank line, and leave October's own three repeats in. Revenue comes out 130.99 too high on 118 rows, and nothing looks wrong. A rule ("keep the first row of each receipt") is right on both files.

**2. A pivot that double counts after an append.** Two ways, both silent:

```python
import sys
sys.path.insert(0, "solution")
import solution as s

paths = ["data/sales_2026-09.csv", "data/sales_2026-10.csv"]
months = [s.apply_steps(s.read_raw(p))[0] for p in paths]
print("the steps:", s.pivot(s.combine(months))["grand_total"])

# Without Filtered Rows, each file's Total line lands in the pivot as a store with no name.
totals = [{"Store": "(blank)", "Month": m[0]["Month"], "Revenue": s.parse_money(s.read_raw(p)[-1][5])}
          for p, m in zip(paths, months)]
print("Total lines kept:", s.pivot(s.appended(months + [totals]))["grand_total"])

# Refresh appends October again (a copy of the file sits in the folder) and nothing removes repeats.
print("October appended twice:", s.pivot(s.appended(months + months[1:]))["grand_total"])
```

```text
the steps: 61429.21
Total lines kept: 122858.42
October appended twice: 92244.45
```

Keep the Total lines and the grand total is exactly double: every receipt plus a line that already summed them. Leave a copy such as `sales_2026-10 (1).csv` in the folder and October counts twice. Filtered Rows and the second Removed Duplicates in `combine` stop both, and comparing each month's column total with the file's own Total line catches anything else.

**3. Appending before renaming.** If October's column is still called Qty when the months are stacked, the append keeps both columns and fills the gaps with nothing:

```python
import sys
sys.path.insert(0, "solution")
import solution as s

sep = s.apply_steps(s.read_raw("data/sales_2026-09.csv"))[0]
oct_ = s.apply_steps(s.read_raw("data/sales_2026-10.csv"))[0]
oct_qty = [{("Qty" if k == "Units" else k): v for k, v in r.items()} for r in oct_]   # no Renamed Columns
both = s.appended([sep, oct_qty])
print(both[-1])
print("Units by month:", s.pivot(both, "Store", "Month", "Units")["column_totals"])
```

```text
{'Receipt': 'R2610-0117', 'Date': '2026-10-13', 'Month': '2026-10', 'Store': 'Old Town', 'Product': 'Sleeping Bags', 'Units': None, 'Revenue': 105.99, 'Qty': 1}
Units by month: {'2026-09': 212}
```

October vanishes from a units pivot. No error, just a missing column of numbers.

**4. Guessing the date order.** `31/10/2026` can only be day first, but `05/10/2026` reads as 5 October or 10 May. Decide the order once for each source, write it in the step (`DATE_FORMATS` here, the `"en-GB"` culture in M), and check a day above 12.

## Your turn

Open `exercise.py` and fill in `removed_top_rows`, `promoted_headers`, `renamed_columns`, `trimmed_text`, `filtered_rows`, `changed_type`, `removed_duplicates`, `apply_steps`, `appended`, `combine`, `pivot` and `refresh`. The date and money parsers, `capitalized_each_word`, `added_custom`, the `STEPS` list and `render_pivot` are done for you. Then run, from this folder:

```
python3 test_lesson.py
```

The test runs each step on small hand-made tables (no title lines and three, a header with no rows, a missing cell, a zero revenue, an unreadable date), then runs your whole step list on the committed September and October files and on two months that `make_data.build(seed=2031)` makes in memory in other styles: other column names, another date format, and one month with no Total line. It checks every cleaned row against the generator's record of the true receipts, that appending a month twice adds nothing, and that `refresh` reads a folder. A step that only works on the committed files fails the second set.

Stretch: add a step that refuses a file whose Total line disagrees with the sum of its receipts, and name it the way Power Query would.

## Check yourself

1. Why does "skip the first 2 rows" break next month while "skip rows until Receipt" does not?
2. Your pivot's grand total is exactly double what finance expects. What is the first thing you look for?
3. Two monthly files call the same column Qty and Units. What happens if you append them before renaming?
4. Why remove duplicates both inside each month and after the append?

<details>
<summary>Answers</summary>

1. The number of title lines is a property of one file. The header's first cell is a property of every file. A rule tied to content keeps working when the layout moves; a count tied to positions does not.
2. A total line that survived into the data, such as the export's own Total row or a subtotal pasted under the table. Exactly double means every value was counted once as itself and once inside a total.
3. The appended table keeps both columns. Rows from one month have the number under Qty and nothing under Units, and the other month the reverse, so a pivot on either column misses a month without any error.
4. Inside a month, the export repeats lines. After the append, the same month can arrive twice, for example from a copied file in the folder. Each check catches a different accident, and a receipt id makes both cheap.

</details>

## What to tell the stakeholder

"Marcus, September and October now come from the same nine cleaning steps instead of hand edits: September is 30,613.97 on 123 receipts and October 30,815.24 on 117, and both match the Total line the tills print. The steps already handle October's title lines, renamed columns and day-first dates, so for November you drop the file in the folder and click Refresh. If a new export changes a column name we have not seen, the refresh will stop with an error instead of showing a wrong number, and that is the moment to call me."

## In real job postings

In the Real Analyst Jobs data drop of 25 October 2026 ([data/job-market/2026-10](../../../data/job-market/2026-10/)), 411 of the 900 India analyst postings that list tools ask for Excel (45.7%) and 350 ask for Power BI (38.9%), the two tools Power Query lives in. In the US the figures are 860 and 492 of 2,056. See [Power BI skills for analysts](https://realanalystjobs.com/skills/power-bi) and [Excel skills for analysts](https://realanalystjobs.com/skills/excel).

## Next

[07 Dashboard design and KPI cards](../07-dashboard-design-and-kpi-cards/)
