#!/usr/bin/env python3
"""Placement check: a short quiz that tells you where to start in the course.

    python3 tools/placement.py                        # interactive: asks your goal, then 13 short questions
    python3 tools/placement.py --answers answers.json # grade answers saved in a file
    python3 tools/placement.py --answers answers.json --json   # machine-readable result
    python3 tools/placement.py --track bi-analyst     # skip the goal question
    python3 tools/placement.py --template             # print an answers file to fill in
    python3 tools/placement.py --markdown             # print the Fast track section of LEARNING_ROADMAP.md

An answers file looks like this (missing answers count as wrong):

    {"track": "data-analyst", "answers": {"q01": "6", "q02": "SELECT ...", "q03": "b"}}

Nothing is shown as right or wrong until the end. Then you get a score per area,
every answer with a one-line explanation, a start lesson and the lessons you can
skip for your role.

FAST_TRACK below is the one table behind both this script's recommendation and the
"Fast track" sections in LEARNING_ROADMAP.md and README.md. Those sections are the
output of render_roadmap_markdown() and render_readme_markdown(); test_placement.py
fails if the documents drift from this table. Edit the table, then paste the new
output of --markdown into the documents.

Standard library only, offline, Python 3.9 or later.
"""
import argparse
import json
import os
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AREAS = ["sql", "statistics", "metrics", "dashboards", "python", "ai"]
AREA_NAMES = {
    "sql": "SQL",
    "statistics": "Statistics",
    "metrics": "Metrics",
    "dashboards": "Dashboard logic",
    "python": "Python",
    "ai": "AI evaluation",
}

# --------------------------------------------------------------------------
# The questions
# --------------------------------------------------------------------------

SALES_TABLE = [
    ("North", "Ana", 60.0),
    ("North", "Ben", 50.0),
    ("South", "Cy", 40.0),
    ("South", "Dee", 60.0),
    ("East", "Eli", 30.0),
    ("East", "Fay", None),
    ("West", "Gus", 120.0),
]
SALES_REFERENCE_SQL = "SELECT region, SUM(amount) FROM sales GROUP BY region HAVING SUM(amount) > 100"

JOIN_SETUP = [
    "CREATE TABLE customers (customer_id INTEGER, name TEXT)",
    "INSERT INTO customers VALUES (1, 'Ana'), (2, 'Ben'), (3, 'Cy'), (4, 'Dee')",
    "CREATE TABLE orders (order_id INTEGER, customer_id INTEGER)",
    "INSERT INTO orders VALUES (10, 1), (11, 1), (12, 1), (13, 2), (14, 3)",
]
JOIN_SQL = "SELECT COUNT(*) FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id"

PYTHON_SNIPPET = """rows = [{"city": "Oslo", "sales": "120"},
        {"city": "oslo ", "sales": "80"},
        {"city": "Bergen", "sales": ""}]
totals = {}
for r in rows:
    key = r["city"].strip().title()
    if r["sales"]:
        totals[key] = totals.get(key, 0) + int(r["sales"])
print(len(totals), totals.get("Oslo"))"""


def _sales_text():
    lines = ["  region | rep | amount", "  -------+-----+-------"]
    for region, rep, amount in SALES_TABLE:
        lines.append("  %-6s | %-3s | %s" % (region, rep, "NULL" if amount is None else "%g" % amount))
    return "\n".join(lines)


# Each question: id, area, kind, prompt, answer, explanation, lessons (curriculum ids that teach it).
# kind is "choice" (a letter), "number" (with tolerance; percent=True also accepts 0.3 for 30),
# "text" (compared after collapsing spaces) or "sql" (run on sqlite3, compared by result).
QUESTIONS = [
    {
        "id": "q01", "area": "sql", "kind": "number", "tolerance": 0,
        "prompt": "customers has 4 rows: Ana (id 1), Ben (2), Cy (3), Dee (4).\n"
                  "orders has 5 rows. Ana has 3 orders, Ben 1, Cy 1, Dee none.\n"
                  "How many does this return?\n  " + JOIN_SQL,
        "answer": 6,
        "explanation": "A join returns one row per match: Ana 3, Ben 1, Cy 1, and Dee keeps 1 row with NULLs, so 6.",
        "lessons": ["01-02", "00-03"],
    },
    {
        "id": "q02", "area": "sql", "kind": "sql",
        "prompt": "Table sales(region, rep, amount):\n" + _sales_text() + "\n"
                  "Type one SQL query, on one line, that returns each region and its total amount,\n"
                  "keeping only regions whose total is above 100. Names and order of columns and rows do not matter.",
        "answer": SALES_REFERENCE_SQL,
        "explanation": "GROUP BY region, then HAVING SUM(amount) > 100: North 110 and West 120. South is exactly 100, so it is out.",
        "lessons": ["01-01", "01-07"],
    },
    {
        "id": "q03", "area": "statistics", "kind": "choice",
        "prompt": "Five orders: 20, 22, 25, 30 and 400. The manager asks for the typical order value.\n"
                  "  a) The mean, 99.4\n  b) The median, 25\n  c) The largest, 400\n  d) The mean of the two middle values, 23.5",
        "answer": "b",
        "explanation": "One large order drags the mean to 99.4. The median, 25, is what a typical order looks like.",
        "lessons": ["02-01", "02-06"],
    },
    {
        "id": "q04", "area": "statistics", "kind": "choice",
        "prompt": "An A/B test on checkout gives p = 0.03 for the gap in conversion. What does that mean?\n"
                  "  a) There is a 97% chance the new checkout is better\n"
                  "  b) If there were no real difference, a gap this big or bigger would show up about 3% of the time\n"
                  "  c) The new checkout lifts conversion by 3%\n"
                  "  d) 3% of users saw the wrong version",
        "answer": "b",
        "explanation": "A p-value is how surprising the data would be if nothing changed. It is not the chance that B is better.",
        "lessons": ["02-03", "02-08"],
    },
    {
        "id": "q05", "area": "metrics", "kind": "number", "tolerance": 0.1, "percent": True,
        "prompt": "Three stores last week:\n"
                  "  store | visits | orders\n  A     |    100 |     10\n  B     |     10 |      5\n  C     |    890 |     45\n"
                  "What is the overall conversion rate (orders / visits), in percent?",
        "answer": 6.0,
        "explanation": "Ratio of sums: 60 orders / 1000 visits = 6%. Averaging the three store rates gives 21.7%, which is wrong.",
        "lessons": ["03-06", "03-05"],
    },
    {
        "id": "q06", "area": "metrics", "kind": "choice",
        "prompt": "Conversion went from 4% to 5%. Which sentence is right?\n"
                  "  a) Conversion rose 1%\n  b) Conversion rose 1 percentage point, a 25% relative rise\n"
                  "  c) Conversion rose 25 percentage points\n  d) Conversion rose 5%",
        "answer": "b",
        "explanation": "5 - 4 = 1 point; 1 / 4 = 25% relative. Saying 1% mixes the two up.",
        "lessons": ["03-06"],
    },
    {
        "id": "q07", "area": "dashboards", "kind": "choice",
        "prompt": "order_lines has one row per product in an order. A KPI card labelled Orders counts rows.\n"
                  "  a) That is right: one row is one order\n"
                  "  b) It overcounts: count distinct order_id instead\n"
                  "  c) It undercounts: sum the quantity instead\n"
                  "  d) It is right as long as a date filter is on",
        "answer": "b",
        "explanation": "The grain is order line, not order. An order with 3 products counts 3 times unless you count distinct order_id.",
        "lessons": ["00-03", "04-01"],
    },
    {
        "id": "q08", "area": "dashboards", "kind": "number", "tolerance": 0.1, "percent": True,
        "prompt": "Table sales(region, amount): North 40, North 20, South 30, South 60, East 50.\n"
                  "A visual filtered to region = North shows this measure:\n"
                  "  DAX:     Share = SUM(sales[amount]) / CALCULATE(SUM(sales[amount]), ALL(sales))\n"
                  "  Tableau: SUM([amount]) / SUM({FIXED : SUM([amount])})\n"
                  "What does it show, in percent?",
        "answer": 30.0,
        "explanation": "The filter keeps North (60) on top, but ALL and FIXED ignore it below (200): 60 / 200 = 30%.",
        "lessons": ["04-02", "04-03"],
    },
    {
        "id": "q09", "area": "python", "kind": "text",
        "prompt": "What does this print?\n\n" + "\n".join("    " + line for line in PYTHON_SNIPPET.splitlines()),
        "answer": "1 200",
        "explanation": "strip and title turn both Oslo rows into one key (120 + 80), and Bergen has no sales so it is skipped.",
        "lessons": ["00-06", "05-01"],
    },
    {
        "id": "q10", "area": "python", "kind": "choice",
        "prompt": "A CSV is read with csv.DictReader. What does sorted([\"9\", \"10\", \"100\"]) return?\n"
                  "  a) ['9', '10', '100']\n  b) ['10', '100', '9']\n  c) An error\n  d) ['100', '10', '9']",
        "answer": "b",
        "explanation": "CSV values are text, and text sorts letter by letter: '1' comes before '9'. Convert with int() first.",
        "lessons": ["05-01", "05-05"],
    },
    {
        "id": "q11", "area": "ai", "kind": "number", "tolerance": 0.5, "percent": True,
        "prompt": "An LLM flags 20 support tickets as urgent. 15 of them really are urgent.\n"
                  "There are 30 really urgent tickets in all. What is the recall, in percent?",
        "answer": 50.0,
        "explanation": "Recall = found / all real = 15 / 30 = 50%. Precision is 15 / 20 = 75%.",
        "lessons": ["06-01", "06-08"],
    },
    {
        "id": "q12", "area": "ai", "kind": "choice",
        "prompt": "On the same 50 examples, prompt v1 gets 45 right (90%) and prompt v2 gets 46 right (92%).\n"
                  "  a) v2 is better: ship it\n"
                  "  b) The gap is one example. With 50 examples the margin is about 8 points, so you cannot tell yet\n"
                  "  c) v1 is better because it is simpler\n"
                  "  d) Run v2 on the same 50 again and average the two runs",
        "answer": "b",
        "explanation": "50 examples cannot separate 90% from 92%. You need a much bigger eval set, or a paired comparison.",
        "lessons": ["06-07", "06-05"],
    },
    {
        "id": "q13", "area": "ai", "kind": "choice",
        "prompt": "An LLM turns questions into SQL that runs on the sales database.\n"
                  "Which guard actually stops it from deleting data?\n"
                  "  a) Tell the model in the prompt to write only SELECT\n"
                  "  b) Run the SQL on a read-only connection that sees only the allowed tables\n"
                  "  c) Read the SQL when it looks long\n"
                  "  d) Lower the temperature",
        "answer": "b",
        "explanation": "A prompt is a request, not a guard. Only the database permissions make a delete impossible.",
        "lessons": ["06-10", "06-02"],
    },
]

# --------------------------------------------------------------------------
# The Fast track table: one source for the recommendation and the docs
# --------------------------------------------------------------------------

# "do": lessons in order. area None means do it whatever you scored.
# "skip": lessons safe to skip, but only when you are strong in that area.
FAST_TRACK = {
    "data-analyst": {
        "title": "Working data analyst",
        "who": "You write SQL at work and want experiments, metric judgment, data quality and AI checks.",
        "do": [
            ("01-03", "sql", "Windows are the most asked SQL skill after joins."),
            ("01-08", "sql", "Find duplicates and reconcile two sources before you trust a total."),
            ("01-12", "sql", "The daily job now that AI writes much of the SQL."),
            ("02-03", "statistics", "Run an A/B test from raw counts and make the call."),
            ("02-04", "statistics", "Size a test before it starts."),
            ("03-06", "metrics", "Percent vs points and ratio of sums, the most common metric slip."),
            ("03-10", "metrics", "Diagnose a metric drop in a fixed order."),
            ("05-05", "python", "Row counts, keys and NULLs before any analysis."),
            ("05-09", "python", "Turn your checks into data quality tests."),
            ("06-01", "ai", "Grade an LLM classifier with precision and recall."),
            ("06-10", "ai", "Guard natural-language-to-SQL with code, not prompts."),
            ("10-01", None, "A capstone you can show."),
        ],
        "skip": [
            ("00-04", "sql", "You write SELECT, WHERE and ORDER BY every day."),
            ("01-01", "sql", "GROUP BY and HAVING are routine for you."),
            ("01-07", "sql", "You already use subqueries and CTEs."),
            ("02-01", "statistics", "You already pick median over mean for skewed numbers."),
            ("00-06", "python", "You already read files and loop in Python."),
            ("05-01", "python", "You already clean CSVs in code."),
            ("04-05", "dashboards", "Lookups and SUMIFS are spreadsheet basics you know."),
            ("04-06", "dashboards", "You already build pivots."),
        ],
    },
    "bi-analyst": {
        "title": "BI analyst",
        "who": "You build dashboards and want the model, the measures and the SQL behind them right.",
        "do": [
            ("00-03", "dashboards", "Grain decides every count on a dashboard."),
            ("04-01", "dashboards", "Model the star schema a dashboard needs."),
            ("04-02", "dashboards", "DAX filter context, built from scratch."),
            ("04-03", "dashboards", "Tableau LOD expressions, rebuilt in SQL."),
            ("04-08", "dashboards", "Dates and many-to-many without double counting."),
            ("04-09", "dashboards", "Define each metric once so dashboards agree."),
            ("04-11", "dashboards", "Row-level security that holds."),
            ("01-03", "sql", "Window functions behind running totals and ranks."),
            ("01-08", "sql", "Reconcile the dashboard to the source."),
            ("03-05", "metrics", "Write a metric definition people cannot misread."),
            ("03-06", "metrics", "Percent vs points on every KPI card."),
            ("08-01", None, "Where the tables you report on come from."),
            ("10-05", None, "An executive dashboard capstone."),
        ],
        "skip": [
            ("04-04", "dashboards", "You build charts every day; drawing one from scratch is optional."),
            ("04-05", "dashboards", "You already use lookups and SUMIFS."),
            ("04-06", "dashboards", "You already build pivots and Power Query steps."),
            ("04-07", "dashboards", "You already design KPI cards."),
            ("00-04", "sql", "You already write basic SELECT queries."),
            ("01-01", "sql", "GROUP BY and HAVING are routine for you."),
        ],
    },
    "business-analyst": {
        "title": "Business analyst",
        "who": "You work in spreadsheets and with stakeholders and want SQL, sharper metrics and clear answers.",
        "do": [
            ("00-05", "sql", "Why a blank is not a zero."),
            ("01-02", "sql", "Joins without losing or doubling rows."),
            ("01-07", "sql", "Subqueries and CTEs for multi-step questions."),
            ("03-05", "metrics", "Numerator, denominator, window and exclusions, written down."),
            ("03-06", "metrics", "The two slips behind most wrong KPI numbers."),
            ("03-09", "metrics", "Mix effects: when every segment rises and the total falls."),
            ("03-10", "metrics", "A fixed order of checks when a number falls."),
            ("02-01", "statistics", "Pick the number that describes a typical value."),
            ("06-03", "ai", "Catch made-up numbers in AI summaries."),
            ("07-06", None, "Lead with the decision, not the method."),
            ("09-09", None, "A process-heavy case study."),
        ],
        "skip": [
            ("00-04", "sql", "You already write basic SELECT queries."),
            ("01-01", "sql", "GROUP BY and HAVING are routine for you."),
            ("04-05", "dashboards", "Lookups and SUMIFS are your daily tools."),
            ("04-06", "dashboards", "You already build pivots."),
            ("00-06", "python", "You already read files and loop in Python."),
            ("06-04", "ai", "You already know what tokens and temperature do."),
        ],
    },
    "interview-prep": {
        "title": "Interview prep",
        "who": "You have an analyst interview soon and want the rounds they actually run.",
        "do": [
            ("01-02", "sql", "Joins and fan-out, the first SQL screen question."),
            ("01-03", "sql", "Window functions, the second."),
            ("01-11", "sql", "Gaps and islands, the classic hard question."),
            ("07-02", None, "SQL interview questions under time."),
            ("02-03", "statistics", "The experiment question in most statistics rounds."),
            ("02-10", "statistics", "The causation trap interviewers love."),
            ("07-09", None, "Practise the statistics round."),
            ("03-01", "metrics", "Metric trees, the frame for every case."),
            ("03-10", "metrics", "Diagnose a metric drop, the most common case."),
            ("07-08", None, "Practise the case out loud."),
            ("07-10", None, "Scope, check and present a take-home."),
            ("07-11", None, "Stories with a number and a decision."),
        ],
        "skip": [
            ("00-04", "sql", "You already write basic SELECT queries."),
            ("01-01", "sql", "GROUP BY and HAVING are routine for you."),
            ("02-01", "statistics", "You already pick median over mean for skewed numbers."),
            ("03-02", "metrics", "You can already compute a funnel."),
            ("05-01", "python", "Interviews rarely ask you to clean a CSV."),
            ("04-05", "dashboards", "Interviews rarely test spreadsheet lookups."),
        ],
    },
}
TRACK_ORDER = ["data-analyst", "bi-analyst", "business-analyst", "interview-prep"]
BEGINNER_START = "00-01"

# Thresholds, as integer ratios so the boundaries are exact.
STRONG_NUM, STRONG_DEN = 2, 3     # an area is strong at 2/3 correct or more
BEGINNER_NUM, BEGINNER_DEN = 2, 5  # below 40% overall, start at the beginning


# --------------------------------------------------------------------------
# Curriculum checks
# --------------------------------------------------------------------------

def load_curriculum(root=ROOT):
    with open(os.path.join(root, "curriculum.json"), encoding="utf-8") as f:
        cur = json.load(f)
    return {l["id"]: l for p in cur["phases"] for l in p["lessons"]}


def referenced_ids():
    ids = {BEGINNER_START}
    for q in QUESTIONS:
        ids.update(q["lessons"])
    for track in FAST_TRACK.values():
        ids.update(i for i, _, _ in track["do"])
        ids.update(i for i, _, _ in track["skip"])
    return ids


def validate(lessons, root=ROOT):
    """Raise ValueError if a referenced lesson is missing, not live, or has no folder."""
    problems = []
    for lid in sorted(referenced_ids()):
        lesson = lessons.get(lid)
        if lesson is None:
            problems.append("%s is not in curriculum.json" % lid)
        elif lesson["status"] != "live":
            problems.append("%s is %s, not live" % (lid, lesson["status"]))
        elif not os.path.isdir(os.path.join(root, lesson["path"])):
            problems.append("%s folder %s is missing" % (lid, lesson["path"]))
    for key, track in FAST_TRACK.items():
        dos = [i for i, _, _ in track["do"]]
        skips = [i for i, _, _ in track["skip"]]
        both = set(dos) & set(skips)
        if both:
            problems.append("%s lists %s as both do and skip" % (key, ", ".join(sorted(both))))
        for area in [a for _, a, _ in track["do"] + track["skip"] if a is not None]:
            if area not in AREAS:
                problems.append("%s uses unknown area %s" % (key, area))
    for q in QUESTIONS:
        if q["area"] not in AREAS:
            problems.append("%s uses unknown area %s" % (q["id"], q["area"]))
    if problems:
        raise ValueError("placement.py references bad lessons:\n  " + "\n  ".join(problems))


# --------------------------------------------------------------------------
# Grading (pure functions)
# --------------------------------------------------------------------------

def _parse_number(text):
    text = str(text).strip().replace(",", "")
    if text.endswith("%"):
        text = text[:-1].strip()
    return float(text)


def _norm_cell(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), 2)
    return value


def run_sql(query, step_limit=200000):
    """Run one SELECT on a fresh in-memory sales table. Return sorted rows, or raise ValueError."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE TABLE sales (region TEXT, rep TEXT, amount REAL)")
        conn.executemany("INSERT INTO sales VALUES (?, ?, ?)", SALES_TABLE)
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
                   getattr(sqlite3, "SQLITE_RECURSIVE", 33)}
        conn.set_authorizer(lambda action, *args: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
        steps = [0]

        def guard():
            steps[0] += 1
            return 1 if steps[0] > step_limit else 0
        conn.set_progress_handler(guard, 1000)
        try:
            rows = conn.execute(query).fetchall()
        except (sqlite3.Error, sqlite3.Warning, ValueError) as exc:
            raise ValueError(str(exc))
    finally:
        conn.close()
    # Neither row order nor column order matters: compare each row as a sorted set of cells.
    return sorted((tuple(sorted((_norm_cell(v) for v in row), key=repr)) for row in rows), key=repr)


def check_answer(question, given):
    """Return True if the given answer is right. Blank or unparseable answers are wrong."""
    if given is None:
        return False
    text = str(given).strip()
    if not text:
        return False
    kind = question["kind"]
    if kind == "choice":
        text = text.lower().lstrip("(")
        return text[:1] == question["answer"] and not text[1:2].isalpha()
    if kind == "number":
        try:
            value = _parse_number(text)
        except ValueError:
            return False
        expected = question["answer"]
        if question.get("percent") and 0 < abs(value) <= 1 and abs(expected) > 1:
            value = value * 100
        return abs(value - expected) <= question.get("tolerance", 0) + 1e-9
    if kind == "text":
        return " ".join(text.split()) == " ".join(str(question["answer"]).split())
    if kind == "sql":
        try:
            return run_sql(text) == run_sql(question["answer"])
        except ValueError:
            return False
    raise ValueError("unknown question kind %s" % kind)


def grade(answers):
    """answers: {question id: answer}. Return {"areas": {area: {correct, total}}, "correct", "total", "results"}."""
    areas = dict((a, {"correct": 0, "total": 0}) for a in AREAS)
    results = []
    for q in QUESTIONS:
        given = answers.get(q["id"])
        ok = check_answer(q, given)
        areas[q["area"]]["total"] += 1
        areas[q["area"]]["correct"] += 1 if ok else 0
        results.append({"id": q["id"], "area": q["area"], "correct": ok, "given": given,
                        "answer": q["answer"], "explanation": q["explanation"], "lessons": list(q["lessons"])})
    correct = sum(a["correct"] for a in areas.values())
    total = sum(a["total"] for a in areas.values())
    return {"areas": areas, "correct": correct, "total": total, "results": results}


def is_strong(area_score):
    return area_score["total"] > 0 and area_score["correct"] * STRONG_DEN >= area_score["total"] * STRONG_NUM


def is_beginner(scores):
    return scores["correct"] * BEGINNER_DEN < scores["total"] * BEGINNER_NUM


def _lesson_ref(lid, lessons, why=None, area=None):
    l = lessons[lid]
    out = {"id": lid, "title": l["title"], "path": l["path"]}
    if area is not None or why is not None:
        out["area"] = area
        out["why"] = why
    return out


def recommend(scores, track, lessons=None):
    """Pure: scores from grade() (only "areas", "correct", "total" are read) and a track key -> dict."""
    if track not in FAST_TRACK:
        raise ValueError("unknown track %s; pick one of %s" % (track, ", ".join(TRACK_ORDER)))
    if lessons is None:
        lessons = load_curriculum()
    t = FAST_TRACK[track]
    strong = [a for a in AREAS if is_strong(scores["areas"][a])]
    path = []
    for lid, area, why in t["do"]:
        item = _lesson_ref(lid, lessons, why, area)
        item["strong_area"] = area in strong
        path.append(item)
    beginner = is_beginner(scores)
    if beginner:
        start = _lesson_ref(BEGINNER_START, lessons)
        start["why"] = "Your score suggests the full path. Start at phase 00 and follow Level 1 in LEARNING_ROADMAP.md."
        skip = []
    else:
        first_gap = next((p for p in path if not p["strong_area"]), path[-1])
        start = {"id": first_gap["id"], "title": first_gap["title"], "path": first_gap["path"],
                 "why": first_gap["why"]}
        skip = [_lesson_ref(lid, lessons, why, area) for lid, area, why in t["skip"] if area in strong]
    keep = [_lesson_ref(lid, lessons, why, area) for lid, area, why in t["skip"] if area not in strong or beginner]
    return {"track": track, "track_title": t["title"], "beginner": beginner, "strong_areas": strong,
            "start": start, "path": path, "skip": skip, "do_not_skip_yet": keep}


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------

def _pct(c, t):
    return int(round(100.0 * c / t)) if t else 0


def _show(value):
    return "%g" % value if isinstance(value, float) else str(value)


def format_report(scores, rec):
    out = ["", "=" * 60, "Placement result (%s)" % rec["track_title"], "=" * 60, "", "Score per area:"]
    for a in AREAS:
        s = scores["areas"][a]
        mark = "strong" if a in rec["strong_areas"] else "work on it"
        out.append("  %-16s %d / %d  %s" % (AREA_NAMES[a], s["correct"], s["total"], mark))
    out.append("  %-16s %d / %d  (%d%%)" % ("Total", scores["correct"], scores["total"],
                                           _pct(scores["correct"], scores["total"])))
    out += ["", "Answers:"]
    for r in scores["results"]:
        given = "(blank)" if r["given"] in (None, "") else str(r["given"])
        if len(given) > 50:
            given = given[:47] + "..."
        out.append("  %s %-5s %s  you: %s  answer: %s" % (r["id"], "right" if r["correct"] else "wrong",
                                                       AREA_NAMES[r["area"]], given, _show(r["answer"])))
        out.append("      %s Lessons: %s" % (r["explanation"], ", ".join(r["lessons"])))
    s = rec["start"]
    out += ["", "Start here: %s %s" % (s["id"], s["title"]), "  %s/" % s["path"], "  %s" % s["why"]]
    out += ["", "Your path, in order:"]
    for p in rec["path"]:
        note = "  (you scored well here: skim it, do the Check yourself)" if p["strong_area"] else ""
        out.append("  %s %s%s" % (p["id"], p["title"], note))
    out += ["", "Safe to skip:"]
    if rec["skip"]:
        for k in rec["skip"]:
            out.append("  %s %s: %s" % (k["id"], k["title"], k["why"]))
    else:
        out.append("  Nothing yet. Skip a lesson only when its area scores strong here.")
    if rec["do_not_skip_yet"]:
        out += ["", "Do not skip these yet (your score in their area was low):"]
        for k in rec["do_not_skip_yet"]:
            out.append("  %s %s" % (k["id"], k["title"]))
    out += ["", "Skip only if this check or the lesson's own Check yourself is easy for you.",
            "First time here? Run 00-01 once to check Python works. The full list: LEARNING_ROADMAP.md#fast-track", ""]
    return "\n".join(out)


def render_roadmap_markdown(lessons=None, prefix=""):
    """The Fast track section of LEARNING_ROADMAP.md, rendered from FAST_TRACK."""
    if lessons is None:
        lessons = load_curriculum()
    link = lambda lid: "[%s %s](%s%s)" % (lid, lessons[lid]["title"], prefix, lessons[lid]["path"])
    out = [
        "## Fast track",
        "",
        "Already working with data, or preparing for interviews? You do not have to start at phase 00. "
        "Run the placement check from the repo root first. It asks your goal and 13 short questions, "
        "then prints a start lesson and the lessons you can skip:",
        "",
        "```",
        "python3 tools/placement.py",
        "```",
        "",
        "Be honest with yourself: skip a lesson only if the placement check or the lesson's own "
        "**Check yourself** questions are easy for you. If you are unsure, do the lesson; a skipped gap "
        "costs more later than two hours now. Everyone should run "
        + link("00-01") + " once to check that Python works.",
        "",
        "These paths come from one table in `tools/placement.py`, so the script and this page always agree.",
    ]
    for key in TRACK_ORDER:
        t = FAST_TRACK[key]
        out += ["", "### %s" % t["title"], "", t["who"], "", "Do these, in order:", ""]
        for n, (lid, _, why) in enumerate(t["do"], 1):
            out.append("%d. %s: %s" % (n, link(lid), why))
        out += ["", "Safe to skip, if the Check yourself is easy for you:", ""]
        for lid, _, why in t["skip"]:
            out.append("- %s: %s" % (link(lid), why))
    return "\n".join(out)


def render_readme_markdown(lessons=None):
    """The short Fast track block in README.md, rendered from FAST_TRACK."""
    if lessons is None:
        lessons = load_curriculum()
    out = [
        "**Fast track.** Already working with data, or preparing for interviews? Run "
        "`python3 tools/placement.py` from the repo root. It asks your goal and 13 short questions, "
        "then prints where to start and what you can skip. The full paths are in the "
        "[learning roadmap](LEARNING_ROADMAP.md#fast-track). Skip a lesson only if the placement check "
        "or the lesson's own Check yourself is easy for you.",
        "",
    ]
    for key in TRACK_ORDER:
        t = FAST_TRACK[key]
        first = t["do"][0][0]
        skips = ", ".join(lid for lid, _, _ in t["skip"])
        out.append("- **%s**: the path opens with [%s %s](%s). Safe to skip if easy for you: %s."
                   % (t["title"], first, lessons[first]["title"], lessons[first]["path"], skips))
    return "\n".join(out)


def to_json(scores, rec):
    return json.dumps({"scores": scores, "recommendation": rec}, indent=2)


# --------------------------------------------------------------------------
# Interactive loop and CLI
# --------------------------------------------------------------------------

def _ask(prompt, read):
    try:
        return read(prompt)
    except EOFError:
        return ""


def ask_track(read=input, write=print):
    write("What is your goal?")
    for n, key in enumerate(TRACK_ORDER, 1):
        write("  %d) %s: %s" % (n, FAST_TRACK[key]["title"], FAST_TRACK[key]["who"]))
    while True:
        reply = _ask("Pick 1 to %d: " % len(TRACK_ORDER), read).strip().lower()
        if reply in TRACK_ORDER:
            return reply
        if reply.isdigit() and 1 <= int(reply) <= len(TRACK_ORDER):
            return TRACK_ORDER[int(reply) - 1]
        if reply == "":
            write("No answer, so using %s." % FAST_TRACK[TRACK_ORDER[0]]["title"])
            return TRACK_ORDER[0]
        write("Please type a number from 1 to %d." % len(TRACK_ORDER))


def ask_questions(read=input, write=print):
    answers = {}
    write("\n%d questions. Answer each one; you see the results at the end." % len(QUESTIONS))
    write("Press Enter to skip a question you do not know (it counts as wrong).")
    hints = {"choice": "Your answer (a, b, c or d): ", "number": "Your answer (a number): ",
             "text": "Your answer (the printed line): ", "sql": "Your query: "}
    for n, q in enumerate(QUESTIONS, 1):
        write("\n[%d/%d] %s\n%s" % (n, len(QUESTIONS), AREA_NAMES[q["area"]], q["prompt"]))
        answers[q["id"]] = _ask(hints[q["kind"]], read).strip()
        write("Recorded.")
    return answers


def template():
    return {"track": TRACK_ORDER[0], "answers": dict((q["id"], "") for q in QUESTIONS)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Placement check for Analytics from Scratch.")
    parser.add_argument("--answers", help="JSON file with {\"track\": ..., \"answers\": {\"q01\": ...}}")
    parser.add_argument("--track", choices=TRACK_ORDER, help="your goal; skips the goal question")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--template", action="store_true", help="print an empty answers file and exit")
    parser.add_argument("--markdown", action="store_true", help="print the Fast track docs sections and exit")
    args = parser.parse_args(argv)

    lessons = load_curriculum()
    try:
        validate(lessons)
    except ValueError as exc:
        sys.stderr.write(str(exc) + "\n")
        return 2

    if args.template:
        print(json.dumps(template(), indent=2))
        return 0
    if args.markdown:
        print("<!-- LEARNING_ROADMAP.md -->\n")
        print(render_roadmap_markdown(lessons))
        print("\n<!-- README.md -->\n")
        print(render_readme_markdown(lessons))
        return 0

    if args.answers:
        with open(args.answers, encoding="utf-8") as f:
            data = json.load(f)
        answers = data.get("answers", {})
        track = args.track or data.get("track") or TRACK_ORDER[0]
        if track not in FAST_TRACK:
            sys.stderr.write("unknown track %s; pick one of %s\n" % (track, ", ".join(TRACK_ORDER)))
            return 2
    else:
        print("Analytics from Scratch placement check. About 10 minutes, nothing to install.\n")
        track = args.track or ask_track()
        answers = ask_questions()

    scores = grade(answers)
    rec = recommend(scores, track, lessons)
    print(to_json(scores, rec) if args.json else format_report(scores, rec))
    return 0


if __name__ == "__main__":
    sys.exit(main())
