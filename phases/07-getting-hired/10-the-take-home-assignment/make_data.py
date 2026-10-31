"""Build the take-home dataset and three sample submissions for the take-home lesson.

The story: Kestrel Home, a fictional online furniture shop, gives analyst candidates a
four-hour take-home. data/takehome/ is what a candidate receives; data/submissions/ holds
three answers to grade.

data/takehome/BRIEF.md     the questions, as the candidate sees them
data/takehome/orders.csv   order_id, customer_id, customer_email, order_date, region, amount, status
    September and October 2026. Like most real exports, it has three problems the brief
    does not mention: some orders were exported twice (identical rows), some orders are
    internal test orders (email ending in @kestrelhome.test), and some orders were refunded
    (status "refunded").
data/submissions/<name>/   README.md (the write-up), answers.csv (question, answer) and,
    for two of them, the code. "strong" handles the data problems and leads with the answer.
    "weak_fast" skips the data checks, so its numbers are wrong. "weak_buried" has the right
    numbers but hides the answer under the method, has no assumptions and no code.

The data is synthetic and deterministic (fixed seed). Kestrel Home, its customers and the
candidates are invented.
Run from the lesson folder: python3 make_data.py
In code: build(seed) returns {relative path: file text} without writing files, and
write_files(files, root) writes them under root.
"""
import csv
import io
import os
import random

SEED = 21
HERE = os.path.dirname(os.path.abspath(__file__))
REGIONS = ("East", "North", "South", "West")
HEADER = ["order_id", "customer_id", "customer_email", "order_date", "region", "amount", "status"]
TEST_DOMAIN = "@kestrelhome.test"

BRIEF = """# Kestrel Home analyst take-home

Synthetic data for a course exercise. Kestrel Home is a fictional company.

You have four hours. Use any tool you like. `orders.csv` has every web order from
September and October 2026, one row per order.

Please answer:

1. `oct_revenue`: net revenue in October 2026, in dollars.
2. `top_growth_region`: the region whose revenue grew the most, in dollars, from September to October.
3. `top_growth_amount`: how much that region grew, in dollars.
4. `repeat_rate_pct`: of the customers who ordered in October, the percentage who ordered two or more times in October.

Send a folder with:

- `answers.csv` with columns `question,answer`, one row per question above.
- `README.md`: a one-page write-up for Hana, our head of growth, who will decide which region gets next quarter's marketing budget.
- The code or queries you used.
"""

STRONG_CODE = '''"""Kestrel Home take-home: answers from orders.csv. Run: python3 analysis.py [path/to/orders.csv]"""
import csv
import os
import sys

path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "takehome", "orders.csv")
with open(path, newline="") as f:
    rows = list(csv.DictReader(f))

seen, orders = set(), []
for r in rows:
    if r["order_id"] in seen:
        continue  # exported twice
    seen.add(r["order_id"])
    orders.append(r)
real = [r for r in orders if not r["customer_email"].endswith("@kestrelhome.test")]
paid = [r for r in real if r["status"] == "paid"]
print("rows", len(rows), "duplicates", len(rows) - len(orders), "test orders", len(orders) - len(real),
      "refunded", len(real) - len(paid))

revenue = {}
for r in paid:
    key = (r["order_date"][:7], r["region"])
    revenue[key] = revenue.get(key, 0.0) + float(r["amount"])
oct_revenue = sum(v for (m, _), v in revenue.items() if m == "2026-10")
growth = {reg: revenue.get(("2026-10", reg), 0.0) - revenue.get(("2026-09", reg), 0.0) for _, reg in revenue}
top = sorted(growth, key=lambda reg: (-growth[reg], reg))[0]
per_customer = {}
for r in paid:
    if r["order_date"].startswith("2026-10"):
        per_customer[r["customer_id"]] = per_customer.get(r["customer_id"], 0) + 1
repeat = 100 * sum(1 for n in per_customer.values() if n >= 2) / len(per_customer)

print("question,answer")
print("oct_revenue,%.2f" % oct_revenue)
print("top_growth_region,%s" % top)
print("top_growth_amount,%.2f" % growth[top])
print("repeat_rate_pct,%.1f" % repeat)
'''

FAST_CODE = '''# Kestrel Home take-home (pasted from my notebook)
import csv
rows = list(csv.DictReader(open("orders.csv")))
octo = [r for r in rows if r["order_date"].startswith("2026-10")]
print(sum(float(r["amount"]) for r in octo))
'''


def build_orders(rng):
    """Unique orders, then the planted problems. Returns (rows as written, the hidden facts)."""
    growth = {reg: rng.uniform(-0.10, 0.25) for reg in REGIONS}
    weight = {"East": 1.0, "North": 1.3, "South": 0.8, "West": 1.1}
    customers = ["K%04d" % i for i in range(1, 361)]
    home = {c: rng.choice(REGIONS) for c in customers}
    orders = []
    oid = 1000
    for month, days in (("2026-09", 30), ("2026-10", 31)):
        for c in customers:
            active = rng.random() < 0.55
            if not active:
                continue
            n = 1 + (rng.random() < 0.25) + (rng.random() < 0.08)
            for _ in range(n):
                oid += rng.randint(1, 3)
                reg = home[c]
                scale = weight[reg] * (1 + growth[reg] if month == "2026-10" else 1)
                amount = round(rng.uniform(40, 420) * scale, 2)
                status = "refunded" if rng.random() < 0.06 else "paid"
                day = "%s-%02d" % (month, rng.randint(1, days))
                orders.append([str(oid), c, c.lower() + "@mail.example", day, reg, "%.2f" % amount, status])
    # True growth by region, to pick where the test orders go.
    true = {}
    for r in orders:
        if r[6] == "paid":
            key = (r[3][:7], r[4])
            true[key] = true.get(key, 0.0) + float(r[5])
    ranked = sorted(REGIONS, key=lambda reg: -(true.get(("2026-10", reg), 0) - true.get(("2026-09", reg), 0)))
    target = ranked[1]  # the internal team tested checkout in the runner-up region
    for i in range(rng.randint(12, 16)):
        oid += 1
        day = "2026-10-%02d" % rng.randint(1, 31)
        orders.append([str(oid), "K9%03d" % i, "qa%d%s" % (i, TEST_DOMAIN), day, target,
                       "%.2f" % round(rng.uniform(600, 1500), 2), "paid"])
    rows = list(orders)
    for r in rng.sample(orders, rng.randint(18, 26)):
        rows.append(list(r))  # exported twice
    rng.shuffle(rows)
    return rows


def compute(rows, careful):
    """The four answers and the data-check counts. careful=False is what a rushed candidate does."""
    if careful:
        seen, unique = set(), []
        for r in rows:
            if r[0] not in seen:
                seen.add(r[0])
                unique.append(r)
        real = [r for r in unique if not r[2].endswith(TEST_DOMAIN)]
        paid = [r for r in real if r[6] == "paid"]
        counts = {"duplicates": len(rows) - len(unique), "test_orders": len(unique) - len(real),
                  "refunded": len(real) - len(paid)}
    else:
        paid, counts = rows, None
    rev = {}
    for r in paid:
        key = (r[3][:7], r[4])
        rev[key] = rev.get(key, 0.0) + float(r[5])
    oct_rev = sum(v for (m, _), v in rev.items() if m == "2026-10")
    growth = {reg: rev.get(("2026-10", reg), 0.0) - rev.get(("2026-09", reg), 0.0) for reg in REGIONS}
    top = sorted(REGIONS, key=lambda reg: (-growth[reg], reg))[0]
    per = {}
    for r in paid:
        if r[3].startswith("2026-10"):
            per[r[1]] = per.get(r[1], 0) + 1
    repeat = 100 * sum(1 for n in per.values() if n >= 2) / len(per)
    answers = {"oct_revenue": "%.2f" % oct_rev, "top_growth_region": top,
               "top_growth_amount": "%.2f" % growth[top], "repeat_rate_pct": "%.1f" % repeat}
    return answers, counts


def money(text):
    return "${:,.2f}".format(float(text))


def answers_csv(a):
    out = ["question,answer"] + ["%s,%s" % (k, a[k]) for k in ("oct_revenue", "top_growth_region", "top_growth_amount", "repeat_rate_pct")]
    return "\n".join(out) + "\n"


def strong_readme(a, c):
    return """# Where to put next quarter's marketing budget

{region} grew the most from September to October: revenue up {growth}. October net revenue was {rev}, and {rep}% of October customers ordered two or more times.

Recommendation: start the budget conversation with {region}, and confirm with November before moving money, because one month of growth can be noise.

Synthetic data from a course exercise. Kestrel Home is a fictional company.

## Answers

| Question | Answer |
|---|---|
| October net revenue | {rev} |
| Region that grew the most | {region} |
| Its growth, September to October | {growth} |
| October customers with 2+ orders | {rep}% |

## Data checks

- {dup} rows were duplicates: exact repeats of an earlier order_id (exported twice). Kept one of each.
- {test} orders came from internal test accounts (email ending in @kestrelhome.test), all in October. Removed.
- {ref} real orders were refunded. Left out of revenue and of the order counts.

Without these checks October revenue and the top region both come out different.

## Assumptions

- Net revenue means paid orders only, without tax or shipping (the file has one amount per order).
- A month is the calendar month of order_date.
- A customer is a customer_id.

## Limits and next steps

- Two months is one change, not a trend. Check November before moving budget.
- Growth is in dollars, so a large region can lead on a small percentage change. A percentage view is a quick follow-up if Hana prefers it.
- Next: split the growth into more customers versus bigger orders.

Code: `analysis.py` reproduces every number above from orders.csv in one command.
""".format(region=a["top_growth_region"], growth=money(a["top_growth_amount"]), rev=money(a["oct_revenue"]),
           rep=a["repeat_rate_pct"], dup=c["duplicates"], test=c["test_orders"], ref=c["refunded"])


def fast_readme(a):
    return """# Take-home answers

{region} is the region to back: revenue grew {growth} from September to October. October revenue was {rev}, and {rep}% of October customers ordered more than once.

Synthetic data from a course exercise. Kestrel Home is a fictional company.

## Data checks

The file looked clean. No duplicates, test orders or refunds needed removing.

## Assumptions

- Revenue is the sum of the amount column.
- A customer is a customer_id.

## Next steps

- Put the extra budget into {region}.
""".format(region=a["top_growth_region"], growth=money(a["top_growth_amount"]), rev=money(a["oct_revenue"]),
           rep=a["repeat_rate_pct"])


def buried_readme(a, c):
    method = ("I started by opening the file in a spreadsheet and reading the columns one by one, "
              "to understand what each one meant and how the orders were recorded. ")
    para = ("Then I built a pivot table of amount by month and region, and checked each total against "
            "a second pivot built a different way, to make sure nothing was double counted along the way. ")
    return """# Kestrel Home take-home

Synthetic data from a course exercise. Kestrel Home is a fictional company.

## Approach

{method}{method2}

{para}{para}{para}

I also looked at the customers, and counted how many orders each one placed in each month, then
grouped them into one order and two or more orders. {para}{para}

## Data checks

I found {dup} duplicated rows, {test} internal test orders and {ref} refunded orders, and removed all of them before
computing anything.

## Detailed working

{work}

## Results

In the end, the region that grew the most was {region}, by {growth}. October net revenue was {rev}.
The repeat rate in October was {rep}%.

Screenshots of my spreadsheet are available on request.
""".format(method=method, method2=method.replace("I started", "After that I went back"), para=para,
           work=(para + method) * 6, region=a["top_growth_region"], growth=money(a["top_growth_amount"]),
           rev=money(a["oct_revenue"]), rep=a["repeat_rate_pct"], dup=c["duplicates"], test=c["test_orders"],
           ref=c["refunded"])


def build(seed=SEED):
    rng = random.Random(seed)
    rows = build_orders(rng)
    good, counts = compute(rows, careful=True)
    rushed, _ = compute(rows, careful=False)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HEADER)
    w.writerows(rows)
    return {
        "takehome/BRIEF.md": BRIEF,
        "takehome/orders.csv": buf.getvalue(),
        "submissions/strong/README.md": strong_readme(good, counts),
        "submissions/strong/answers.csv": answers_csv(good),
        "submissions/strong/analysis.py": STRONG_CODE,
        "submissions/weak_fast/README.md": fast_readme(rushed),
        "submissions/weak_fast/answers.csv": answers_csv(rushed),
        "submissions/weak_fast/notebook_export.py": FAST_CODE,
        "submissions/weak_buried/README.md": buried_readme(good, counts),
        "submissions/weak_buried/answers.csv": answers_csv(good),
    }


def write_files(files, root):
    for rel, text in sorted(files.items()):
        path = os.path.join(root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="") as f:
            f.write(text)


def main():
    files = build(SEED)
    write_files(files, os.path.join(HERE, "data"))
    n = files["takehome/orders.csv"].count("\n") - 1
    print("wrote %d files, orders.csv has %d rows (synthetic, seed %d)" % (len(files), n, SEED))


if __name__ == "__main__":
    main()
