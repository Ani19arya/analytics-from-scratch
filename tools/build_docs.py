"""Render the lesson lists in README.md, LEARNING_ROADMAP.md and phases/README.md from curriculum.json.

curriculum.json is the single source of truth for lesson order, level and status.
Each document marks a generated region with
    <!-- generated:NAME -->  ...  <!-- /generated:NAME -->
and this script replaces only what sits between those markers.

    python3 tools/build_docs.py          # rewrite the generated regions
    python3 tools/build_docs.py --check  # exit 1 if any region is out of date (used in CI)
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVEL_NAME = {"beginner": "Level 1", "intermediate": "Level 2", "advanced": "Level 3"}
LEVEL_ORDER = ["beginner", "intermediate", "advanced"]


def load():
    with open(os.path.join(ROOT, "curriculum.json"), encoding="utf-8") as f:
        return json.load(f)


def lesson_line(lesson, link_prefix=""):
    title = lesson["title"]
    if lesson["status"] == "live":
        title = f"[{title}]({link_prefix}{lesson['path']})"
    else:
        title = f"{title} *(planned)*"
    kind = " Guide, no test." if lesson["kind"] == "guide" else ""
    return f"{lesson['id']} {title}: {lesson['question']}{kind}"


def render_phase_table(cur):
    rows = ["| Phase | What you learn | Lessons live | Planned |", "|---|---|---|---|"]
    for p in cur["phases"]:
        live = sum(1 for l in p["lessons"] if l["status"] == "live")
        rows.append(f"| [{p['slug'][:2]} {p['title']}](phases/{p['slug']}) | {p['summary']} | {live} | {len(p['lessons']) - live} |")
    total = sum(len(p["lessons"]) for p in cur["phases"])
    live = sum(1 for p in cur["phases"] for l in p["lessons"] if l["status"] == "live")
    rows.append(f"| **All** | | **{live}** | **{total - live}** |")
    return "\n".join(rows)


def render_phase_lessons(cur):
    out = []
    for p in cur["phases"]:
        out.append(f"### {p['slug'][:2]} {p['title']}\n")
        for i, l in enumerate(p["lessons"], 1):
            out.append(f"{i}. {lesson_line(l)} ({LEVEL_NAME[l['level']]})")
        out.append("")
    return "\n".join(out).rstrip()


def render_by_level(cur, level):
    out = []
    for p in cur["phases"]:
        items = [l for l in p["lessons"] if l["level"] == level]
        if not items:
            continue
        out.append(f"**{p['slug'][:2]} {p['title']}**\n")
        for l in items:
            mark = "x" if l["status"] == "live" else " "
            out.append(f"- [{mark}] {lesson_line(l)} About {l['hours']:g} h.")
        out.append("")
    hours = sum(l["hours"] for p in cur["phases"] for l in p["lessons"] if l["level"] == level)
    out.append(f"Level total: about {hours:g} hours of focused work.")
    return "\n".join(out)


def render_phase_index(cur):
    rows = ["| # | Phase | Lessons live | Planned |", "|---|---|---|---|"]
    for p in cur["phases"]:
        live = sum(1 for l in p["lessons"] if l["status"] == "live")
        rows.append(f"| {p['slug'][:2]} | [{p['title']}]({p['slug']}) | {live} | {len(p['lessons']) - live} |")
    return "\n".join(rows)


def regions(cur):
    r = {"phase-table": render_phase_table(cur), "phase-lessons": render_phase_lessons(cur),
         "phase-index": render_phase_index(cur)}
    for level in LEVEL_ORDER:
        r[f"level-{level}"] = render_by_level(cur, level)
    return r


def apply(text, rendered):
    def sub(m):
        name = m.group(1)
        if name not in rendered:
            raise SystemExit(f"unknown generated region: {name}")
        return f"<!-- generated:{name} -->\n{rendered[name]}\n<!-- /generated:{name} -->"
    return re.sub(r"<!-- generated:([\w-]+) -->.*?<!-- /generated:\1 -->", sub, text, flags=re.S)


def main():
    check = "--check" in sys.argv
    rendered = regions(load())
    stale = []
    for name in ["README.md", "LEARNING_ROADMAP.md", "phases/README.md"]:
        path = os.path.join(ROOT, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            old = f.read()
        new = apply(old, rendered)
        if new != old:
            stale.append(name)
            if not check:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new)
    if check and stale:
        print("Out of date (run python3 tools/build_docs.py):", ", ".join(stale))
        sys.exit(1)
    print("docs up to date" if not stale else "rewrote: " + ", ".join(stale))


if __name__ == "__main__":
    main()
