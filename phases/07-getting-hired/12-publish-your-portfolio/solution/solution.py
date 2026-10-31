"""Solution: check a portfolio project folder before you publish it.

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

PROJECTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "projects")
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


# ---- helpers (done for you in the exercise) ---------------------------------

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
    if not os.path.isfile(os.path.join(folder, "README.md")):
        return {"readme": "there is no README.md, so nobody knows what the project answers"}
    s = sections(read_text(folder, "README.md"))
    out = {}
    if "?" not in s.get("Question", ""):
        out["question"] = "add a ## Question section that asks one question, with a question mark"
    if not re.search(r"\d", s.get("Answer", "")):
        out["answer"] = "add a ## Answer section that gives the answer as a number"
    data = s.get("Data", "").lower()
    if not (("licence" in data or "license" in data) and ("http" in data or "synthetic" in data)):
        out["provenance"] = "the ## Data section must say where the data came from (a link, or synthetic) and its licence"
    cmd = run_command(folder)
    if cmd is None:
        out["run_command"] = "## How to run needs exactly one fenced block with exactly one command"
    else:
        m = RUN_LINE.match(cmd)
        if not m:
            out["run_command"] = "the run command should be python3 <file>.py, not %r" % cmd
        elif not os.path.isfile(os.path.join(folder, m.group(1))):
            out["run_command"] = "the run command names %s, which is not in the project" % m.group(1)
    return out


def file_problems(folder):
    """secret, large_file, network."""
    out, secrets = {}, []
    for path in project_files(folder):
        name = path.rsplit("/", 1)[-1]
        if name.startswith(".env") and name != ".env.example":
            secrets.append(path)
        size = os.path.getsize(os.path.join(folder, *path.split("/")))
        if size > MAX_BYTES:
            out.setdefault("large_file", "%s is %d bytes; keep data files under %d, or link to the source" % (path, size, MAX_BYTES))
        if not is_text(path):
            continue
        text = read_text(folder, path)
        for n, line in enumerate(text.splitlines(), 1):
            if SECRET.search(line):
                secrets.append("%s line %d" % (path, n))
            if path.endswith(".py") and not line.strip().startswith("#") and any(h in line for h in NETWORK_HINTS):
                out.setdefault("network", "%s line %d reaches the internet; the project must run offline" % (path, n))
    if secrets:
        out["secret"] = "remove it, and replace the key if it was ever pushed: %s" % ", ".join(secrets)
    return out


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
    out = {}
    req = os.path.join(folder, "requirements.txt")
    needed = third_party(folder)
    if needed and not os.path.isfile(req):
        out["requirements"] = "the code imports %s but there is no requirements.txt" % ", ".join(needed)
    if os.path.isfile(req):
        loose = [x.strip() for x in read_text(folder, "requirements.txt").splitlines()
                 if x.strip() and not x.strip().startswith("#") and "==" not in x]
        if loose:
            out["unpinned"] = "pin every version with ==, for example pandas==2.2.3: %s" % ", ".join(loose)
    return out


def run_problems(folder, command):
    """runs: the command, run on a copy of the folder, must exit with code 0."""
    m = RUN_LINE.match(command)
    args = [sys.executable, m.group(1)] + (m.group(2) or "").split()
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, "project")
        shutil.copytree(folder, copy)
        try:
            proc = subprocess.run(args, cwd=copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True, timeout=RUN_TIMEOUT)
        except subprocess.TimeoutExpired:
            return {"runs": "%s did not finish in %d seconds" % (command, RUN_TIMEOUT)}
    if proc.returncode != 0:
        last = (proc.stderr.strip().splitlines() or ["no error message"])[-1]
        return {"runs": "%s failed on a clean copy: %s" % (command, last)}
    return {}


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
