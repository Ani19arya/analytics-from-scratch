#!/usr/bin/env python3
"""Course-wide checks that the lesson tests cannot do on their own.

    python3 tools/lint.py            # errors fail, version-2 section gaps are warnings
    python3 tools/lint.py --strict   # version-2 section gaps fail too

Checks:
1. Style: no em dashes, en dashes or curly quotes in any text file.
2. curriculum.json matches the folders: every live lesson exists with its files,
   every lesson folder is listed, planned lessons have no folder yet, ids are unique.
3. Every relative link in every Markdown file points at a file or folder that exists.
4. Live lesson READMEs have the version 2 sections from LESSON_TEMPLATE.md.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_EXT = {".md", ".py", ".sql", ".json", ".csv", ".txt", ".yml", ".yaml", ".svg"}
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}
BAD_CHARS = {chr(0x2014): "em dash", chr(0x2013): "en dash", chr(0x201C): "curly quote", chr(0x201D): "curly quote",
             chr(0x2018): "curly quote", chr(0x2019): "curly quote"}
V2_SECTIONS = ["## Before you start", "## The problem", "## In plain words", "## What you will build from scratch",
               "## The idea", "## Walk through", "## Common mistakes", "## Your turn", "## Check yourself",
               "## What to tell the stakeholder", "## In real job postings", "## Next"]
GUIDE_SECTIONS = ["## Before you start", "## In plain words", "## Check yourself", "## Next"]


def walk_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            yield os.path.join(dirpath, name)


def rel(path):
    return os.path.relpath(path, ROOT)


def check_style(errors):
    for path in walk_files():
        if os.path.splitext(path)[1] not in TEXT_EXT:
            continue
        with open(path, encoding="utf-8", errors="replace") as f:
            for n, line in enumerate(f, 1):
                for ch, label in BAD_CHARS.items():
                    if ch in line:
                        errors.append(f"{rel(path)}:{n}: {label}")


def check_curriculum(errors, warnings, strict):
    with open(os.path.join(ROOT, "curriculum.json"), encoding="utf-8") as f:
        cur = json.load(f)
    ids, listed = set(), set()
    for phase in cur["phases"]:
        for lesson in phase["lessons"]:
            if lesson["id"] in ids:
                errors.append(f"curriculum.json: duplicate id {lesson['id']}")
            ids.add(lesson["id"])
            path = os.path.join(ROOT, lesson["path"])
            listed.add(os.path.normpath(path))
            exists = os.path.isdir(path)
            if lesson["status"] == "planned" and exists:
                errors.append(f"{lesson['path']}: folder exists but curriculum.json says planned")
            if lesson["status"] == "live":
                if not exists:
                    errors.append(f"{lesson['path']}: listed as live but missing")
                    continue
                need = ["README.md"] if lesson["kind"] == "guide" else ["README.md", "test_lesson.py", "make_data.py"]
                for name in need:
                    if not os.path.isfile(os.path.join(path, name)):
                        errors.append(f"{lesson['path']}: missing {name}")
                with open(os.path.join(path, "README.md"), encoding="utf-8") as f:
                    text = f.read()
                wanted = GUIDE_SECTIONS if lesson["kind"] == "guide" else V2_SECTIONS
                missing = [s for s in wanted if s not in text]
                if missing:
                    (errors if strict else warnings).append(f"{lesson['path']}: missing sections {', '.join(missing)}")
                for word in ("coming soon", "lorem ipsum"):
                    if word.lower() in text.lower():
                        errors.append(f"{lesson['path']}/README.md: placeholder text '{word}'")
    phases = os.path.join(ROOT, "phases")
    for phase in sorted(os.listdir(phases)):
        pdir = os.path.join(phases, phase)
        if not os.path.isdir(pdir):
            continue
        for lesson in sorted(os.listdir(pdir)):
            ldir = os.path.join(pdir, lesson)
            if os.path.isdir(ldir) and lesson[:2].isdigit() and os.path.normpath(ldir) not in listed:
                errors.append(f"{rel(ldir)}: lesson folder not listed in curriculum.json")


LINK = re.compile(r"\]\(([^)\s]+)\)")


def check_links(errors):
    for path in walk_files():
        if not path.endswith(".md"):
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`\n]*`", "", text)
        for target in LINK.findall(text):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            target = target.split("#")[0]
            if not target:
                continue
            resolved = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.exists(resolved):
                errors.append(f"{rel(path)}: broken link {target}")


def main():
    strict = "--strict" in sys.argv
    errors, warnings = [], []
    check_style(errors)
    check_curriculum(errors, warnings, strict)
    check_links(errors)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("error:", e)
    print(f"lint: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
