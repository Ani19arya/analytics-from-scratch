"""Exercise: check a portfolio project folder before you publish it.

The helpers, third_party, check_project and main are done for you. Fill in readme_problems,
file_problems, dependency_problems and run_problems. Then run: python3 test_lesson.py

check_project(folder) returns {problem code: one-line detail}. An empty dict means a hiring
manager can read the README, see where the data came from, and run the project in one
command, offline, with nothing secret in it.
"""
import ast
import os
import re
import shutil
import subprocess
import sys
import tempfile

PROJECTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "projects")
MAX_BYTES = 1000000
RUN_TIMEOUT = 30
TEXT_EXT = {".py", ".md", ".txt", ".csv", ".json", ".cfg", ".toml", ".yml", ".yaml", ".ini", ".sql", ".env"}
# The standard library modules a small analysis is likely to use. The list is fixed so the
# checker gives the same answer on every Python version.
STDLIB = {"argparse", "ast", "collections", "csv", "datetime", "decimal", "functools", "glob", "hashlib",
          "html", "http", "io", "itertools", "json", "logging", "math", "os", "pathlib", "random", "re",
          "shutil", "sqlite3", "statistics", "string", "subprocess", "sys", "tempfile", "textwrap", "time",
          "typing", "unittest", "urllib", "uuid", "xml", "zipfile"}
SECRET = re.compile(r"(?i)\b\w*(api_?key|secret|token|password)\w*\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}")
NETWORK_HINTS = ("http://", "https://", "urlopen(", "requests.", "socket.")
RUN_LINE = re.compile(r"^python3? (\S+\.py)( .*)?$")


# ---- helpers (done for you) ---------------------------------------------------

def project_files(folder):
    """Every file in the folder as a path relative to it, with "/" separators, sorted.
    __pycache__ and .git are skipped."""
    out = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if d not in ("__pycache__", ".git"))
        for name in filenames:
            out.append(os.path.relpath(os.path.join(dirpath, name), folder).replace(os.sep, "/"))
    return sorted(out)


def read_text(folder, path):
    with open(os.path.join(folder, *path.split("/")), encoding="utf-8", errors="replace") as f:
        return f.read()


def is_text(path):
    name = path.rsplit("/", 1)[-1]
    return os.path.splitext(name)[1] in TEXT_EXT or name.startswith(".env")


def sections(markdown):
    """{heading: body} for every "## heading" in the markdown."""
    out, current = {}, None
    for line in markdown.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def imports(source):
    """Top-level module names a Python file imports. A file that does not parse gives an empty set."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def run_command(folder):
    """The one line in the fenced block under "## How to run", or None if there is not exactly one."""
    if not os.path.isfile(os.path.join(folder, "README.md")):
        return None
    body = sections(read_text(folder, "README.md")).get("How to run", "")
    blocks = re.findall(r"```[^\n]*\n(.*?)```", body, re.S)
    if len(blocks) != 1:
        return None
    lines = [x.strip() for x in blocks[0].splitlines() if x.strip()]
    return lines[0] if len(lines) == 1 else None


# ---- the checks ---------------------------------------------------------------

def readme_problems(folder):
    """readme, question, answer, provenance, run_command."""
    # TODO: no README.md -> return {"readme": detail} and nothing else.
    # Otherwise, with s = sections(read_text(folder, "README.md")):
    #   "question"     s["Question"] is missing or has no "?"
    #   "answer"       s["Answer"] is missing or has no digit
    #   "provenance"   s["Data"] (lower case) lacks "licence" or "license", or lacks both "http" and "synthetic"
    #   "run_command"  run_command(folder) is None, or it does not match RUN_LINE,
    #                  or the .py file it names is not in the folder
    # Each value is a one-line detail saying what to fix.
    raise NotImplementedError


def file_problems(folder):
    """secret, large_file, network."""
    # TODO: for each path in project_files(folder):
    #   "secret"      the file name starts with ".env" (but is not ".env.example"),
    #                 or a line of a text file (is_text) matches SECRET
    #   "large_file"  the file is over MAX_BYTES bytes (os.path.getsize)
    #   "network"     a line of a .py file that is not a comment contains one of NETWORK_HINTS
    # The "secret" detail lists every place (".env, analysis.py line 6"); for the others,
    # the first place found is enough (dict.setdefault).
    raise NotImplementedError


def third_party(folder):
    """Imported modules that are neither in STDLIB nor a .py file in the project."""
    files = project_files(folder)
    local = {p.rsplit("/", 1)[-1][:-3] for p in files if p.endswith(".py")}
    found = set()
    for p in files:
        if p.endswith(".py"):
            found |= imports(read_text(folder, p))
    return sorted(found - STDLIB - local)


def dependency_problems(folder):
    """requirements, unpinned."""
    # TODO: "requirements"  third_party(folder) is not empty and there is no requirements.txt
    #       "unpinned"      requirements.txt has a line that is not blank, not a comment and has no "=="
    raise NotImplementedError


def run_problems(folder, command):
    """runs: the command, run on a copy of the folder, must exit with code 0."""
    # TODO: build the arguments from RUN_LINE: [sys.executable, the .py file, any extra words].
    # Copy the folder into a tempfile.TemporaryDirectory() with shutil.copytree, so the run
    # cannot depend on files that are not in the project and leaves nothing behind.
    # subprocess.run(args, cwd=copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    #                universal_newlines=True, timeout=RUN_TIMEOUT)
    # Return {"runs": detail} if it times out or the return code is not 0, else {}.
    raise NotImplementedError


def check_project(folder, run=True):
    """Every problem in one dict. The project is run only when it can be run safely and
    offline: one valid command, no network use, and no packages to install."""
    problems = {}
    problems.update(readme_problems(folder))
    problems.update(file_problems(folder))
    problems.update(dependency_problems(folder))
    blocked = {"readme", "run_command", "network", "requirements", "unpinned"} & set(problems)
    if run and not blocked and not third_party(folder):
        problems.update(run_problems(folder, run_command(folder)))
    return problems


def main(root=PROJECTS):
    for name in sorted(os.listdir(root)):
        problems = check_project(os.path.join(root, name))
        print(name + ":", "ready to publish" if not problems else ", ".join(sorted(problems)))
        for code in sorted(problems):
            print("    %s: %s" % (code, problems[code]))


if __name__ == "__main__":
    main()
