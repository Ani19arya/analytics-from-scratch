"""Build data/projects/: five small portfolio project folders to check before publishing.

Each project is the same kind of analysis (trial against paid churn on a small synthetic
table), published five ways. One is ready to publish. The others each break a rule that
stops a hiring manager running the project, or that should never be on a public page.

The committed projects are seed 0. Any other seed builds five projects with different
numbers and a random mix of problems, for the second-dataset test. The problems injected
are returned as "truth", so the test can confirm its own checker finds exactly those.
Every project, number and key is invented. The keys are fake strings that only look like keys.
Run from the lesson folder: python3 make_data.py
In code: build(seed) returns {"projects": {name: {path: text}}, "truth": {name: set of codes}}.
write_projects(projects, root) writes them under root.
"""
import os
import random
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = 0
LARGE_BYTES = 1100000  # just over the checker's 1,000,000 byte limit

ANALYSIS = '''"""Trial against paid churn within 90 days. Python 3.9+, standard library only."""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
{extra_import}

def main():
    with open({data_path}, newline="") as f:
        rows = list(csv.DictReader(f))
    for start in ("trial", "paid"):
        group = [r for r in rows if r["start_type"] == start]
        churned = sum(r["churned"] == "1" for r in group)
        print("%s: %d of %d churned (%.1f%%)" % (start, churned, len(group), 100.0 * churned / len(group)))
{extra_code}

if __name__ == "__main__":
    main()
'''
GOOD_PATH = 'os.path.join(HERE, "data", "customers.csv")'
LOCAL_PATH = '"/Users/maya/Downloads/customers.csv"'
SECRET_LINE = 'API_KEY = "demo{key}"  # pasted while testing, never removed'
NETWORK_CODE = '''

def fetch_holidays():
    from urllib.request import urlopen
    return urlopen("https://api.example.com/holidays?key=" + API_KEY).read()
'''


def customers(rng):
    """Synthetic customers: customer_id, start_type, churned (1 or 0)."""
    rows = []
    trial_rate, paid_rate = rng.uniform(0.25, 0.4), rng.uniform(0.12, 0.25)
    for cid in range(1, rng.randint(50, 80) + 1):
        start = "trial" if rng.random() < 0.5 else "paid"
        churned = rng.random() < (trial_rate if start == "trial" else paid_rate)
        rows.append((cid, start, int(churned)))
    return rows


def answer_line(rows):
    parts = []
    for start in ("trial", "paid"):
        group = [r for r in rows if r[1] == start]
        c = sum(r[2] for r in group)
        parts.append("%.1f%% of %s starters (%d of %d)" % (100.0 * c / len(group), start, c, len(group)))
    return "Within 90 days, %s churned, against %s." % tuple(parts)


def readme(rows, breaks):
    lines = ["# Do trial customers churn more?", ""]
    if "question" not in breaks:
        lines += ["## Question", "",
                  "Do customers who start on a free trial cancel within 90 days more often than customers who pay from day one?", ""]
    lines += ["## Method", "",
              "I counted churned customers by start type and compared the two rates. "
              "The comparison is observational: customers chose how to start.", ""]
    if "answer" not in breaks:
        lines += ["## Answer", "", answer_line(rows), ""]
    lines += ["## Data", ""]
    if "provenance" in breaks:
        lines += ["`data/customers.csv`, one row per customer.", ""]
    else:
        lines += ["`data/customers.csv`, one row per customer. Synthetic data made for this course. "
                  "Licence: MIT, the same as the code.", ""]
    if "run_command" in breaks:
        lines += ["## How to run", "", "```", "pip install -r requirements.txt", "python3 analysis.py", "```", ""]
    else:
        lines += ["## How to run", "", "```", "python3 analysis.py", "```", "",
                  "Python 3.9 or later. It prints the two churn rates.", ""]
    return "\n".join(lines)


def project(rng, breaks):
    """{path: text} for one project with the given problems."""
    rows = customers(rng)
    key = "".join(rng.choice("abcdefghjkmnpqrstuvwxyz0123456789") for _ in range(24))
    extra_import = ""
    extra_code = ""
    if "secret" in breaks or "network" in breaks:
        extra_import = SECRET_LINE.format(key=key) if "secret" in breaks else 'API_KEY = os.environ.get("API_KEY", "")'
    if "network" in breaks:
        extra_code = NETWORK_CODE
    if "requirements" in breaks:
        extra_import = (extra_import + "\nimport pandas as pd").strip()
    if extra_import:
        extra_import += "\n"
    files = {
        "README.md": readme(rows, breaks),
        "analysis.py": ANALYSIS.format(extra_import=extra_import, extra_code=extra_code,
                                       data_path=LOCAL_PATH if "runs" in breaks else GOOD_PATH),
        "data/customers.csv": "customer_id,start_type,churned\n" + "".join("%d,%s,%d\n" % r for r in rows),
    }
    if "secret" in breaks:
        files[".env"] = "API_KEY=demo%s\n" % key
    if "unpinned" in breaks:
        files["requirements.txt"] = "pandas\nmatplotlib>=3.0\n"
    if "large_file" in breaks:
        files["data/raw_export.csv"] = "customer_id,start_type,churned\n" + "1,trial,0\n" * (LARGE_BYTES // 10)
    return files


# The committed projects: one ready to publish and four with one or two problems each.
COMMITTED = {
    "churn-ready": set(),
    "churn-no-answer": {"question", "answer"},
    "churn-leaked-key": {"secret", "network"},
    "churn-my-laptop": {"runs"},
    "churn-two-commands": {"run_command", "unpinned"},
}
# A project that cannot be run by the checker cannot also show a failed run.
BLOCKS_RUN = {"run_command", "network", "requirements", "unpinned"}
RANDOM_BREAKS = ["question", "answer", "provenance", "run_command", "secret", "large_file",
                 "requirements", "unpinned", "network", "runs"]


def build(seed=SEED):
    rng = random.Random(seed)
    if seed == SEED:
        plan = COMMITTED
    else:
        plan = {"project-a": set()}
        for name in ("project-b", "project-c", "project-d", "project-e"):
            breaks = set(rng.sample(RANDOM_BREAKS, rng.randint(1, 3)))
            if "runs" in breaks and breaks & BLOCKS_RUN:
                breaks.discard("runs")
            plan[name] = breaks
    projects = {name: project(rng, breaks) for name, breaks in plan.items()}
    return {"projects": projects, "truth": {name: set(b) for name, b in plan.items()}}


def write_projects(projects, root):
    for name, files in projects.items():
        for path, text in files.items():
            full = os.path.join(root, name, *path.split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", newline="") as f:
                f.write(text)


def main():
    root = os.path.join(HERE, "data", "projects")
    shutil.rmtree(root, ignore_errors=True)
    data = build()
    write_projects(data["projects"], root)
    print("wrote %d projects to data/projects/" % len(data["projects"]))


if __name__ == "__main__":
    main()
