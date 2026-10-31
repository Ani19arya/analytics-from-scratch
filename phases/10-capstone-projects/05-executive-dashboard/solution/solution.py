"""Capstone 10-05: the Kettlemoor executive dashboard. Worked solution.

Read DELIVERABLES.md for what each function must return, and solution/WRITEUP.md
for the reasoning. Run it from the capstone folder:

    python3 solution/solution.py

It prints the KPIs, writes solution/dashboard.svg (the dashboard, drawn with
the standard library) and solution/model/*.csv (the clean star schema, ready
to load into Power BI, Tableau or Looker Studio if you want to rebuild the
dashboard there).
"""
import csv
import datetime as dt
import os
import sqlite3

SWITCH = "2026-07-01"
REPORT_MONTH = "2026-09"


# ---- given ----------------------------------------------------------------------

def load(folder):
    """The four raw CSVs as {"daily_sales", "stores", "store_closures", "targets"}: lists of dicts of text."""
    out = {}
    for name in ("daily_sales", "stores", "store_closures", "targets"):
        with open(os.path.join(folder, name + ".csv"), newline="") as f:
            out[name] = list(csv.DictReader(f))
    return out


def query(con, sql, params=()):
    """Run sql and return a list of dicts, one per row."""
    cur = con.execute(sql, params)
    names = [d[0] for d in cur.description]
    return [dict(zip(names, row)) for row in cur.fetchall()]


def add_months(month, n):
    i = int(month[:4]) * 12 + int(month[5:7]) - 1 + n
    return "%04d-%02d" % (i // 12, i % 12 + 1)


def status(vs_target_pct):
    """green at or above 100% of target, amber from 95% up to 100%, red below 95%, None without a target."""
    if vs_target_pct is None:
        return None
    if vs_target_pct >= 100:
        return "green"
    return "amber" if vs_target_pct >= 95 else "red"


# ---- yours: the model -------------------------------------------------------------

def clean_sales(rows):
    """One row per (sales_date, store_id): the load with the latest loaded_at.
    net_revenue = gross_sales - discounts before 2026-07-01, gross_sales from then on.
    Returns dicts with sales_date, store_id, orders (int), net_revenue, cogs (floats),
    sorted by (sales_date, store_id)."""
    latest = {}
    for r in rows:
        key = (r["sales_date"], r["store_id"])
        if key not in latest or r["loaded_at"] >= latest[key]["loaded_at"]:
            latest[key] = r
    out = []
    for (d, s), r in sorted(latest.items()):
        gross, disc = float(r["gross_sales"]), float(r["discounts"])
        out.append({"sales_date": d, "store_id": s, "orders": int(r["orders"]),
                    "net_revenue": gross - disc if d < SWITCH else gross, "cogs": float(r["cogs"])})
    return out


def build_model(raw):
    """An in-memory SQLite star schema:
    dim_date(date_key, month, year, day_of_week 0 = Monday, is_weekend 0/1): every day from
        the first to the last sales_date, with no gaps;
    dim_store(store_id, store_name, city, opened_on);
    store_closure(store_id, closed_from, closed_to);
    fact_sales(date_key, store_id, orders, net_revenue, cogs): one row per day and store, clean;
    fact_target(month, store_id, revenue_target)."""
    con = sqlite3.connect(":memory:")
    con.executescript("""
        CREATE TABLE dim_date (date_key TEXT PRIMARY KEY, month TEXT, year INTEGER, day_of_week INTEGER,
                               is_weekend INTEGER);
        CREATE TABLE dim_store (store_id TEXT PRIMARY KEY, store_name TEXT, city TEXT, opened_on TEXT);
        CREATE TABLE store_closure (store_id TEXT, closed_from TEXT, closed_to TEXT);
        CREATE TABLE fact_sales (date_key TEXT, store_id TEXT, orders INTEGER, net_revenue REAL, cogs REAL);
        CREATE TABLE fact_target (month TEXT, store_id TEXT, revenue_target REAL);
    """)
    sales = clean_sales(raw["daily_sales"])
    if sales:
        d = dt.date.fromisoformat(sales[0]["sales_date"])
        last = dt.date.fromisoformat(sales[-1]["sales_date"])
        while d <= last:
            con.execute("INSERT INTO dim_date VALUES (?, ?, ?, ?, ?)",
                        (d.isoformat(), d.isoformat()[:7], d.year, d.weekday(), int(d.weekday() >= 5)))
            d += dt.timedelta(days=1)
    con.executemany("INSERT INTO dim_store VALUES (?, ?, ?, ?)",
                    [(r["store_id"], r["store_name"], r["city"], r["opened_on"]) for r in raw["stores"]])
    con.executemany("INSERT INTO store_closure VALUES (?, ?, ?)",
                    [(r["store_id"], r["closed_from"], r["closed_to"]) for r in raw["store_closures"]])
    con.executemany("INSERT INTO fact_sales VALUES (?, ?, ?, ?, ?)",
                    [(r["sales_date"], r["store_id"], r["orders"], r["net_revenue"], r["cogs"]) for r in sales])
    con.executemany("INSERT INTO fact_target VALUES (?, ?, ?)",
                    [(r["month"], r["store_id"], float(r["revenue_target"])) for r in raw["targets"]])
    return con


def check_model(con):
    """Tests a dashboard model must pass before anyone sees a number. Returns a list of
    problems (empty when the model is sound), one short sentence each:
    duplicate (date_key, store_id) in fact_sales; a fact_sales date_key not in dim_date;
    a fact_sales or fact_target store_id not in dim_store; a negative orders, net_revenue
    or cogs; sales on a day the store was closed or before it opened; a gap in dim_date."""
    problems = []
    for r in query(con, "SELECT date_key, store_id, COUNT(*) AS n FROM fact_sales GROUP BY 1, 2 HAVING n > 1"):
        problems.append("duplicate fact_sales row for %s %s" % (r["store_id"], r["date_key"]))
    for r in query(con, "SELECT DISTINCT f.date_key FROM fact_sales f LEFT JOIN dim_date d USING (date_key) "
                        "WHERE d.date_key IS NULL"):
        problems.append("fact_sales date %s is not in dim_date" % r["date_key"])
    for table in ("fact_sales", "fact_target"):
        for r in query(con, "SELECT DISTINCT f.store_id FROM %s f LEFT JOIN dim_store s USING (store_id) "
                            "WHERE s.store_id IS NULL" % table):
            problems.append("%s store %s is not in dim_store" % (table, r["store_id"]))
    for r in query(con, "SELECT date_key, store_id FROM fact_sales WHERE orders < 0 OR net_revenue < 0 OR cogs < 0"):
        problems.append("negative value on %s %s" % (r["store_id"], r["date_key"]))
    for r in query(con, """SELECT f.date_key, f.store_id FROM fact_sales f JOIN dim_store s USING (store_id)
                           WHERE f.date_key < s.opened_on
                              OR EXISTS (SELECT 1 FROM store_closure c WHERE c.store_id = f.store_id
                                         AND f.date_key BETWEEN c.closed_from AND c.closed_to)"""):
        problems.append("sales on a closed day: %s %s" % (r["store_id"], r["date_key"]))
    dates = [r["date_key"] for r in query(con, "SELECT date_key FROM dim_date ORDER BY date_key")]
    for a, b in zip(dates, dates[1:]):
        if (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days != 1:
            problems.append("dim_date has a gap after %s" % a)
    return problems


def missing_days(con, month):
    """(store_id, date_key) pairs in `month` where the store was open (opened, not in a
    closure) but fact_sales has no row: data that never arrived. Sorted."""
    rows = query(con, """
        SELECT s.store_id, d.date_key
        FROM dim_date d CROSS JOIN dim_store s
        WHERE d.month = ? AND d.date_key >= s.opened_on
          AND NOT EXISTS (SELECT 1 FROM store_closure c WHERE c.store_id = s.store_id
                          AND d.date_key BETWEEN c.closed_from AND c.closed_to)
          AND NOT EXISTS (SELECT 1 FROM fact_sales f WHERE f.store_id = s.store_id AND f.date_key = d.date_key)
        ORDER BY s.store_id, d.date_key""", (month,))
    return [(r["store_id"], r["date_key"]) for r in rows]


def lfl_stores(con, month):
    """Like-for-like stores for `month`: opened on or before the first day of the same month a
    year earlier, and with no closure day in either month. Sorted store_ids."""
    ly = add_months(month, -12)
    rows = query(con, """
        SELECT store_id FROM dim_store s
        WHERE opened_on <= ? || '-01'
          AND NOT EXISTS (SELECT 1 FROM store_closure c WHERE c.store_id = s.store_id
                          AND (substr(c.closed_from, 1, 7) <= ? AND substr(c.closed_to, 1, 7) >= ?
                               OR substr(c.closed_from, 1, 7) <= ? AND substr(c.closed_to, 1, 7) >= ?))
        ORDER BY store_id""", (ly, month, month, ly, ly))
    return [r["store_id"] for r in rows]


def _totals(con, month, stores=None):
    sql = "SELECT COALESCE(SUM(orders), 0) AS orders, COALESCE(SUM(net_revenue), 0) AS rev, " \
          "COALESCE(SUM(cogs), 0) AS cogs FROM fact_sales WHERE substr(date_key, 1, 7) = ?"
    params = [month]
    if stores is not None:
        sql += " AND store_id IN (%s)" % ",".join("?" * len(stores))
        params += list(stores)
    return query(con, sql, params)[0]


def _pct(a, b):
    return round(100.0 * a / b, 2) if b else None


def monthly_kpis(con, month):
    """The CEO cards for `month`. Keys:
    net_revenue, orders, aov (net_revenue / orders), gross_margin_pct (100 x (net_revenue - cogs)
    / net_revenue), target (sum of fact_target), vs_target_pct (100 x net_revenue / target),
    status (from vs_target_pct), net_revenue_ly (same month a year earlier), yoy_pct
    (100 x (net_revenue / net_revenue_ly - 1)), lfl_stores, lfl_growth_pct (the same over
    like-for-like stores only), missing_days (count from missing_days).
    Money and percentages rounded to 2 decimals; a ratio with a zero or missing denominator is None."""
    t = _totals(con, month)
    ly = _totals(con, add_months(month, -12))
    target = query(con, "SELECT SUM(revenue_target) AS t FROM fact_target WHERE month = ?", (month,))[0]["t"]
    stores = lfl_stores(con, month)
    lfl_now = _totals(con, month, stores)["rev"] if stores else 0
    lfl_ly = _totals(con, add_months(month, -12), stores)["rev"] if stores else 0
    vs = _pct(t["rev"], target)
    return {
        "month": month,
        "net_revenue": round(t["rev"], 2),
        "orders": t["orders"],
        "aov": round(t["rev"] / t["orders"], 2) if t["orders"] else None,
        "gross_margin_pct": _pct(t["rev"] - t["cogs"], t["rev"]),
        "target": round(target, 2) if target else None,
        "vs_target_pct": vs,
        "status": status(vs),
        "net_revenue_ly": round(ly["rev"], 2),
        "yoy_pct": round(100.0 * (t["rev"] / ly["rev"] - 1), 2) if ly["rev"] else None,
        "lfl_stores": stores,
        "lfl_growth_pct": round(100.0 * (lfl_now / lfl_ly - 1), 2) if lfl_ly else None,
        "missing_days": len(missing_days(con, month)),
    }


def store_table(con, month):
    """One row per store with sales or a target in `month`, sorted by store_id: store_id,
    net_revenue, target, vs_target_pct, status, gross_margin_pct. Same rounding as monthly_kpis."""
    rows = query(con, """
        WITH s AS (SELECT store_id, SUM(net_revenue) AS rev, SUM(cogs) AS cogs FROM fact_sales
                   WHERE substr(date_key, 1, 7) = ? GROUP BY store_id),
             t AS (SELECT store_id, SUM(revenue_target) AS target FROM fact_target WHERE month = ? GROUP BY store_id)
        SELECT d.store_id, s.rev, s.cogs, t.target
        FROM dim_store d LEFT JOIN s USING (store_id) LEFT JOIN t USING (store_id)
        WHERE s.rev IS NOT NULL OR t.target IS NOT NULL
        ORDER BY d.store_id""", (month, month))
    out = []
    for r in rows:
        rev = r["rev"] or 0.0
        vs = _pct(rev, r["target"])
        out.append({"store_id": r["store_id"], "net_revenue": round(rev, 2),
                    "target": r["target"], "vs_target_pct": vs, "status": status(vs),
                    "gross_margin_pct": _pct(rev - (r["cogs"] or 0.0), rev)})
    return out


def trend(con, end_month, n=13):
    """[(month, net_revenue rounded to 2 decimals)] for the n months ending with end_month,
    oldest first; 0.0 for a month with no sales."""
    out = []
    for k in range(n - 1, -1, -1):
        m = add_months(end_month, -k)
        out.append((m, round(_totals(con, m)["rev"], 2)))
    return out


# ---- the deliverable: printed numbers, the dashboard, the model export ---------------

def money_short(x):
    return "GBP %.1fk" % (x / 1000.0) if x is not None else "n/a"


def render_svg(k, stores, series, title):
    """The dashboard: four cards, a 13-month bar trend from zero, a store table."""
    colours = {"green": "#2e7d32", "amber": "#b26a00", "red": "#c62828", None: "#555555"}
    w, h = 760, 470
    p = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" font-family="sans-serif">' % (w, h),
         '<rect width="100%" height="100%" fill="#ffffff"/>',
         '<text x="20" y="30" font-size="18" fill="#222">%s</text>' % title]
    cards = [
        ("Net revenue", money_short(k["net_revenue"]),
         "%.1f%% of target (%s)" % (k["vs_target_pct"], k["status"]) if k["vs_target_pct"] is not None else "no target",
         colours[k["status"]]),
        ("Like-for-like growth", "%+.1f%%" % k["lfl_growth_pct"] if k["lfl_growth_pct"] is not None else "n/a",
         "%d shops, vs same month last year" % len(k["lfl_stores"]), "#555555"),
        ("Gross margin", "%.1f%%" % k["gross_margin_pct"] if k["gross_margin_pct"] is not None else "n/a",
         "net revenue minus cost of goods", "#555555"),
        ("Average order", "GBP %.2f" % k["aov"] if k["aov"] is not None else "n/a",
         "%s orders" % "{:,}".format(k["orders"]), "#555555"),
    ]
    for i, (label, value, note, colour) in enumerate(cards):
        x = 20 + i * 182
        p.append('<rect x="%d" y="48" width="170" height="92" rx="6" fill="#f5f5f5" stroke="#ddd"/>' % x)
        p.append('<text x="%d" y="70" font-size="12" fill="#555">%s</text>' % (x + 10, label))
        p.append('<text x="%d" y="102" font-size="24" fill="#222">%s</text>' % (x + 10, value))
        p.append('<text x="%d" y="126" font-size="10" fill="%s">%s</text>' % (x + 10, colour, note))
    top = max(v for _, v in series) or 1.0
    ymax = (int(top // 50000) + 1) * 50000
    x0, y0, ph, bw = 60, 330, 150, 34
    p.append('<text x="20" y="165" font-size="12" fill="#555">Net revenue by month, GBP (axis from zero)</text>')
    for i in range(3):
        v = ymax * i / 2.0
        y = y0 - ph * i / 2.0
        p.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#e0e0e0"/>' % (x0, x0 + 13 * bw, y, y))
        p.append('<text x="%d" y="%.1f" font-size="9" text-anchor="end" fill="#777">%dk</text>' % (x0 - 4, y + 3, v / 1000))
    for i, (m, v) in enumerate(series):
        bh = ph * v / ymax
        p.append('<rect x="%.1f" y="%.1f" width="%d" height="%.1f" fill="%s"/>'
                 % (x0 + i * bw + 3, y0 - bh, bw - 6, bh, "#1f77b4" if i == len(series) - 1 else "#9ecae1"))
        if i % 2 == 0 or i == len(series) - 1:
            p.append('<text x="%.1f" y="%d" font-size="9" text-anchor="middle" fill="#777">%s</text>'
                     % (x0 + i * bw + bw / 2.0, y0 + 13, m))
    tx = 530
    p.append('<text x="%d" y="165" font-size="12" fill="#555">Shops this month</text>' % tx)
    for i, s in enumerate(stores):
        y = 190 + i * 22
        vs = "%.1f%%" % s["vs_target_pct"] if s["vs_target_pct"] is not None else "n/a"
        p.append('<text x="%d" y="%d" font-size="11" fill="%s">%s  %s  %s of target</text>'
                 % (tx, y, colours[s["status"]], s["store_id"], money_short(s["net_revenue"]), vs))
    note = "Synthetic data. Status: green 100%+ of target, amber 95 to 100%, red below 95%."
    if k["missing_days"]:
        note += " %d shop-day(s) of sales missing this month: totals are low by that much." % k["missing_days"]
    p.append('<text x="20" y="%d" font-size="10" fill="#555">%s</text>' % (h - 20, note))
    p.append("</svg>")
    return "\n".join(p) + "\n"


def export_model(con, folder):
    """Write each model table to folder/<table>.csv for a BI tool."""
    os.makedirs(folder, exist_ok=True)
    for table in ("dim_date", "dim_store", "store_closure", "fact_sales", "fact_target"):
        rows = query(con, "SELECT * FROM %s ORDER BY 1, 2" % table)
        with open(os.path.join(folder, table + ".csv"), "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(list(rows[0].keys()) if rows else [])
            for r in rows:
                w.writerow([("%.2f" % v) if isinstance(v, float) else v for v in r.values()])


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    con = build_model(load(os.path.join(here, "data")))
    print("model checks:", check_model(con) or "all pass")
    k = monthly_kpis(con, REPORT_MONTH)
    for key, v in k.items():
        print("  %-17s %s" % (key, v))
    for s in store_table(con, REPORT_MONTH):
        print(" ", s)
    print("missing:", missing_days(con, REPORT_MONTH))
    series = trend(con, REPORT_MONTH)
    print("trend:", series)
    with open(os.path.join(here, "solution", "dashboard.svg"), "w") as f:
        f.write(render_svg(k, store_table(con, REPORT_MONTH), series, "Kettlemoor, September 2026"))
    export_model(con, os.path.join(here, "solution", "model"))


if __name__ == "__main__":
    main()
