# Clean a messy CSV

Which rows of this export can we trust, and what did we change to get there?

## The problem

Kestrel Home, a fictional online furniture shop, sells in the US and India. Every month the ops team exports September orders from two systems and pastes them into one CSV. Priya, the head of finance, needs the September order table cleaned by Thursday so she can total revenue by currency. She has asked for a short note of what was fixed and what was dropped, because last month a duplicated order went into the board numbers.

The file `data/orders_raw.csv` (106 rows) is synthetic, built by `make_data.py` with a fixed random seed. The mess was added on purpose and is the same every time you rebuild it.

## What you will build from scratch

- `parse_date`: turns four different date formats into one, `YYYY-MM-DD`.
- `parse_amount`: turns `$1,200.50`, `USD 75`, `INR 45,000`, `INR 1,20,000` and `Rs 999` into a number plus a currency code.
- `clean_rows`: normalizes spaces, drops bad rows with a reason, removes duplicates, and returns a report of everything it did.

## The idea

Cleaning is a list of small, explicit decisions. Write each one down as code so the next person can see it.

**Spaces.** `"  Asha  Rao "` and `"Asha Rao"` are the same customer. `" ".join(value.split())` strips both ends and collapses inner runs of spaces. Do this to every cell first, because every later check depends on it.

**Dates.** The export has `2026-09-14`, `14/09/2026`, `Sep 14, 2026` and `14-Sep-2026`. Try each format in a fixed order and keep the first one that parses. The order matters for slashes: `03/04/2026` is 3 April if the file is day first and 4 March if it is month first. No code can guess that. You have to know where the file came from. Here the slash dates come from the India office, so they are day first, and that rule is written in `DATE_FORMATS`, not hidden in your head.

**Money.** A money string is a marker, optional spaces, then digits:

```
^(\$|USD|INR|RS\.?)\s*([\d,]+(?:\.\d+)?)$
```

Group 1 says the currency, group 2 is the number. Strip the commas from group 2 and convert. Removing commas instead of checking where they sit means `1,20,000` (Indian lakh grouping) and `120,000` both become 120000. Keep the currency next to the amount. Adding rupees to dollars is the most expensive mistake in this file.

**Drop or fill.** A row with no date or no amount cannot be counted in monthly revenue, so it is dropped. A row with no city still has a valid order, so the city becomes `Unknown` and the row stays. Every drop gets a reason.

**Duplicates last.** Compare rows after cleaning, not before. Order 1028 appears once as `Sep 20, 2026` and once as `2026-09-20`. As text the two rows differ. As data they are the same order. Dedupe on the raw text and you keep both.

## Walk through

Collapse spaces:

```python
print(repr(" ".join("  Asha  Rao ".split())))
```

This prints `'Asha Rao'`.

Try date formats in order:

```python
from datetime import datetime
FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y", "%d-%b-%Y"]
for s in ["Sep 20, 2026", "17/09/2026", "TBD"]:
    out = None
    for fmt in FORMATS:
        try:
            out = datetime.strptime(s, fmt).strftime("%Y-%m-%d")
            break
        except ValueError:
            pass
    print(s, "->", out)
```

`TBD` fits no format and comes back as `None`, so the row is dropped as `bad_date`.

Pull the currency and number out of a money string:

```python
import re
AMOUNT = re.compile(r"^(\$|USD|INR|RS\.?)\s*([\d,]+(?:\.\d+)?)$", re.IGNORECASE)
m = AMOUNT.match("INR 1,20,000")
print(m.group(1), float(m.group(2).replace(",", "")))
```

This prints `INR 120000.0`.

Run the worked answer on the whole file:

```
python3 solution/solution.py
```

106 rows go in and 91 come out. 35 cells had stray spaces, 3 blank cities became `Unknown`, and 15 rows were dropped: 3 with no date, 2 with the date `TBD`, 4 with no amount and 6 duplicates. Only 3 of the 6 duplicates are exact copies of the text. The other 3 differ in spacing or date format and are caught only because the check runs after cleaning.

## Your turn

Open `exercise.py`. Write the `AMOUNT` pattern, then fill in `parse_date`, `parse_amount` and `clean_rows`. Check the reasons in this order: `blank_date`, `bad_date`, `blank_amount`, `bad_amount`, `duplicate`. Then run, from this folder:

```
python3 test_lesson.py
```

## Check yourself

1. Why must duplicates be removed after the other cleaning steps, not before?
2. A date reads `03/04/2026`. What do you need to know before you parse it?
3. Why keep a currency column instead of converting everything to dollars during cleaning?
4. Two rows have the same order ID but different amounts. Is that a duplicate?

<details>
<summary>Answers</summary>

1. Two rows can be the same order written differently, for example one date as `Sep 20, 2026` and one as `2026-09-20`. Only after both are normalized do they compare as equal.
2. Which system wrote it, and whether that system writes day first or month first. The string alone cannot tell you.
3. Conversion needs an exchange rate and a date for that rate, which is a business decision. Cleaning should keep the facts in the file and leave that choice visible to whoever totals the money.
4. No. It is a conflict. Do not silently keep one. Report both to the owner of the data, because one of the amounts is wrong and you do not know which.

</details>

## In real job postings

Most of an analyst's Python is this kind of work. On the Real Analyst Jobs live feed read on 25 October 2026, 48% of the 2,102 US analyst postings that list tools ask for Python, and 49% of the 914 such India postings do. See the [Python skills page](https://realanalystjobs.com/skills/python), or try the free [CSV cleaner](https://realanalystjobs.com/tools/csv-cleaner) on a file of your own.

## Next

[02 Reshape wide and long](../02-reshape-wide-and-long/)
