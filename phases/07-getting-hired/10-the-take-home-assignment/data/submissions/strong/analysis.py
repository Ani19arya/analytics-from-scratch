"""Kestrel Home take-home: answers from orders.csv. Run: python3 analysis.py [path/to/orders.csv]"""
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
