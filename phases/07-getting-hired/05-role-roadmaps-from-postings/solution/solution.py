"""Solution: skill shares by role family, the skills that differ most between two groups,
and a short roadmap per role. The same functions run on the real data drop by country."""
import csv
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
DROP = os.path.join(HERE, "..", "..", "..", "data", "job-market", "2026-10", "by_country_skill.csv")
SKILLS = ["SQL", "Python", "Excel", "Tableau", "Power BI", "Looker", "R", "dbt"]
MIN_N = 30

# Checked in this order. The first rule that matches wins.
FAMILY_RULES = [
    ("bi", re.compile(r"\bbusiness intelligence\b|\bbi\b", re.I)),
    ("product", re.compile(r"\bproduct\b", re.I)),
    ("business", re.compile(r"\bbusiness\b", re.I)),
    ("data", re.compile(r"\bdata\b|\banalytics\b", re.I)),
]


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_postings():
    return load_csv(os.path.join(DATA, "postings.csv"))


def load_drop(path=DROP):
    """The data drop's skill counts in the same shape as count_by_group: {country: {"n", "skills"}}."""
    counts = {}
    for r in load_csv(path):
        g = counts.setdefault(r["country"], {"n": int(r["postings_listing_any_tool"]), "skills": {s: 0 for s in SKILLS}})
        g["skills"][r["skill"]] = int(r["postings_listing_skill"])
    return counts


def title_family(title):
    """bi, product, business, data or other. BI is checked before business on purpose."""
    for family, pattern in FAMILY_RULES:
        if pattern.search(title):
            return family
    return "other"


def parse_tools(cell):
    """(set of the eight skills listed, True if the posting lists any tool at all).

    Items are split on commas and compared whole and without case, as the data drop does,
    so "RStudio" is not R and "power bi" is Power BI."""
    items = [x.strip() for x in cell.split(",") if x.strip()]
    lookup = {s.lower(): s for s in SKILLS}
    return {lookup[x.lower()] for x in items if x.lower() in lookup}, bool(items)


def count_by_group(postings, group_of):
    """{group: {"n": postings that list any tool, "skills": {skill: postings listing it}}}.

    A posting counts once per skill. Postings that list no tool are left out of n, like the drop."""
    counts = {}
    for p in postings:
        skills, any_tool = parse_tools(p["tools"])
        if not any_tool:
            continue
        g = counts.setdefault(group_of(p), {"n": 0, "skills": {s: 0 for s in SKILLS}})
        g["n"] += 1
        for s in skills:
            g["skills"][s] += 1
    return counts


def share(counts, group, skill):
    """Percent of the group's postings (that list a tool) that list the skill. None if n is 0."""
    g = counts.get(group)
    if not g or g["n"] == 0:
        return None
    return 100.0 * g["skills"][skill] / g["n"]


def pool(counts, groups):
    """Add up the counts of several groups. Shares of the pool are a ratio of sums."""
    out = {"n": 0, "skills": {s: 0 for s in SKILLS}}
    for name in groups:
        g = counts.get(name)
        if not g:
            continue
        out["n"] += g["n"]
        for s in SKILLS:
            out["skills"][s] += g["skills"][s]
    return out


def gaps(counts, a, b, min_n=MIN_N):
    """[(skill, share in a, share in b, a minus b in points)], biggest difference first.

    Ties go to the skill name in alphabetical order. None when either group has fewer than
    min_n postings that list a tool: too few to compare."""
    for g in (a, b):
        if g not in counts or counts[g]["n"] < min_n:
            return None
    rows = []
    for s in SKILLS:
        sa, sb = share(counts, a, s), share(counts, b, s)
        rows.append((s, sa, sb, sa - sb))
    return sorted(rows, key=lambda r: (-abs(r[3]), r[0]))


def roadmap(counts, family, others, min_n=MIN_N, core_at=50.0, top=2):
    """{"core": skills at or above core_at percent in the family, highest first,
        "stands_out": up to `top` skills with the biggest positive gap against the POOLED others}.
    None if the family or the pooled others have fewer than min_n postings."""
    rest = pool(counts, [o for o in others if o != family])
    if family not in counts or counts[family]["n"] < min_n or rest["n"] < min_n:
        return None
    both = {family: counts[family], "rest": rest}
    core = [s for s in SKILLS if share(both, family, s) >= core_at]
    core.sort(key=lambda s: (-share(both, family, s), s))
    diff = [(s, share(both, family, s) - share(both, "rest", s)) for s in SKILLS]
    diff = [d for d in diff if d[1] > 0]
    diff.sort(key=lambda d: (-d[1], d[0]))
    return {"core": core, "stands_out": [s for s, _ in diff[:top]]}


FAMILIES = ["data", "business", "bi", "product"]


def main():
    postings = load_postings()
    counts = count_by_group(postings, lambda p: title_family(p["title"]))
    print("family     n   " + "".join(s.rjust(9) for s in SKILLS))
    for fam in FAMILIES + ["other"]:
        print("%-8s %4d   " % (fam, counts[fam]["n"]) + "".join(("%.0f%%" % share(counts, fam, s)).rjust(9) for s in SKILLS))
    for fam in FAMILIES:
        print(fam, roadmap(counts, fam, FAMILIES))
    drop = load_drop()
    print("US vs IN, 25 Oct 2026 drop:", [(s, round(d, 1)) for s, _, _, d in gaps(drop, "US", "IN")[:3]])


if __name__ == "__main__":
    main()
