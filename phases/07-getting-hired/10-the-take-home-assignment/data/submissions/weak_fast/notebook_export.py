# Kestrel Home take-home (pasted from my notebook)
import csv
rows = list(csv.DictReader(open("orders.csv")))
octo = [r for r in rows if r["order_date"].startswith("2026-10")]
print(sum(float(r["amount"]) for r in octo))
