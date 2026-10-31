"""Tests for lesson 12: publish your portfolio.

python3 test_lesson.py                    checks exercise.py
CHECK_SOLUTION=1 python3 test_lesson.py   checks solution/solution.py

The committed projects are checked against problems written out by hand. Projects from other
seeds are built in memory, written to a temporary folder, and checked against the problems the
generator put in them, which a reference checker written separately below confirms. Small
hand-made projects cover the edge cases. Running a project uses this Python and a temporary copy.
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(HERE, "solution", "solution.py") if os.environ.get("CHECK_SOLUTION") == "1" else os.path.join(HERE, "exercise.py")
spec = importlib.util.spec_from_file_location("lesson", TARGET)
lesson = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lesson)

sys.path.insert(0, HERE)
import make_data  # noqa: E402

COMMITTED = {
    "churn-ready": set(),
    "churn-no-answer": {"question", "answer"},
    "churn-leaked-key": {"secret", "network"},
    "churn-my-laptop": {"runs"},
    "churn-two-commands": {"run_command", "unpinned"},
}
ALL_CODES = {"question", "answer", "provenance", "run_command", "secret", "large_file",
             "requirements", "unpinned", "network", "runs"}
STD = {"argparse", "ast", "collections", "csv", "datetime", "decimal", "functools", "glob", "hashlib",
       "html", "http", "io", "itertools", "json", "logging", "math", "os", "pathlib", "random", "re",
       "shutil", "sqlite3", "statistics", "string", "subprocess", "sys", "tempfile", "textwrap", "time",
       "typing", "unittest", "urllib", "uuid", "xml", "zipfile"}


def files_of(folder):
    out = {}
    for d, subdirs, names in os.walk(folder):
        subdirs[:] = [x for x in subdirs if x not in ("__pycache__", ".git")]
        for n in names:
            full = os.path.join(d, n)
            out[os.path.relpath(full, folder).replace(os.sep, "/")] = full
    return out


def ref_check(folder):
    """Reference checker: the README's rules, written a second time."""
    files = files_of(folder)
    text = {}
    for p, full in files.items():
        with open(full, encoding="utf-8", errors="replace") as f:
            text[p] = f.read()
    found = set()
    command = None
    if "README.md" not in files:
        found.add("readme")
    else:
        parts = re.split(r"^## (.+)$", text["README.md"], flags=re.M)
        sec = {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
        if "?" not in sec.get("Question", ""):
            found.add("question")
        if not any(ch.isdigit() for ch in sec.get("Answer", "")):
            found.add("answer")
        d = sec.get("Data", "").lower()
        if not ("licen" in d and ("http" in d or "synthetic" in d)):
            found.add("provenance")
        fences = sec.get("How to run", "").split("```")
        blocks = fences[1:-1:2] if len(fences) >= 3 else []
        lines = [x.strip() for x in blocks[0].split("\n")[1:] if x.strip()] if len(blocks) == 1 else []
        words = lines[0].split() if len(lines) == 1 else []
        if (len(words) >= 2 and words[0] in ("python", "python3") and words[1].endswith(".py")
                and words[1] in files):
            command = words
        else:
            found.add("run_command")
    mods = set()
    for p, full in files.items():
        name = p.split("/")[-1]
        if (name.startswith(".env") and name != ".env.example"):
            found.add("secret")
        if os.path.getsize(full) > 1000000:
            found.add("large_file")
        for line in text[p].splitlines():
            if re.search(r"(?i)(api_?key|secret|token|password)\w*\s*[:=]\s*[\"']?[A-Za-z0-9_-]{16}", line):
                found.add("secret")
            if p.endswith(".py") and not line.lstrip().startswith("#"):
                if any(h in line for h in ("http://", "https://", "urlopen(", "requests.", "socket.")):
                    found.add("network")
        if p.endswith(".py"):
            for m in re.finditer(r"^\s*(?:import|from)\s+([A-Za-z_]\w*)", text[p], re.M):
                mods.add(m.group(1))
    local = {p.split("/")[-1][:-3] for p in files if p.endswith(".py")}
    outside = mods - STD - local
    if outside and "requirements.txt" not in files:
        found.add("requirements")
    if "requirements.txt" in files:
        if any(x.strip() and not x.strip().startswith("#") and "==" not in x for x in text["requirements.txt"].splitlines()):
            found.add("unpinned")
    if command and not outside and not found & {"network", "requirements", "unpinned"}:
        with tempfile.TemporaryDirectory() as tmp:
            for p, full in files.items():
                dest = os.path.join(tmp, *p.split("/"))
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(full, "rb") as src, open(dest, "wb") as out:
                    out.write(src.read())
            proc = subprocess.run([sys.executable] + command[1:], cwd=tmp, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=60)
            if proc.returncode != 0:
                found.add("runs")
    return found


def write(root, files):
    for path, body in files.items():
        full = os.path.join(root, *path.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(body)
    return root


GOOD_README = ("# Title\n\n## Question\n\nDoes it work?\n\n## Answer\n\nYes, 3 of 4 times.\n\n"
               "## Data\n\nSynthetic. Licence: MIT.\n\n## How to run\n\n```\npython3 main.py\n```\n")


class TestCommittedProjects(unittest.TestCase):
    def test_each_project(self):
        root = os.path.join(HERE, "data", "projects")
        for name, want in sorted(COMMITTED.items()):
            got = lesson.check_project(os.path.join(root, name))
            self.assertIsInstance(got, dict, "check_project returns a dict of {code: detail}")
            self.assertEqual(set(got), want, "%s: expected the problems %s" % (name, sorted(want) or "none"))
            for code, detail in got.items():
                self.assertTrue(isinstance(detail, str) and detail, "%s: give a one-line detail for %s" % (name, code))
            self.assertEqual(ref_check(os.path.join(root, name)), want, "the reference agrees for %s" % name)


class TestSecondDataset(unittest.TestCase):
    def test_other_seeds(self):
        seen = set()
        for seed in (5, 23, 101):
            data = make_data.build(seed=seed)
            with tempfile.TemporaryDirectory() as tmp:
                make_data.write_projects(data["projects"], tmp)
                for name, want in sorted(data["truth"].items()):
                    folder = os.path.join(tmp, name)
                    self.assertEqual(ref_check(folder), want, "reference check, seed %d %s" % (seed, name))
                    self.assertEqual(set(lesson.check_project(folder)), want,
                                     "seed %d, %s: expected %s" % (seed, name, sorted(want) or "no problems"))
                    seen |= want
        self.assertEqual(seen, ALL_CODES, "the seeds should cover every problem code")


class TestEdgeCases(unittest.TestCase):
    def check(self, files, want, why):
        with tempfile.TemporaryDirectory() as tmp:
            folder = write(os.path.join(tmp, "p"), files) if files else os.path.join(tmp, "p")
            os.makedirs(folder, exist_ok=True)
            self.assertEqual(set(lesson.check_project(folder)), want, why)

    def test_empty_folder(self):
        self.check({}, {"readme"}, "an empty folder has no README, and nothing to run")

    def test_minimal_good(self):
        self.check({"README.md": GOOD_README, "main.py": "print(3)\n"}, set(), "a README with the four sections and a script that runs")

    def test_command_names_a_missing_file(self):
        self.check({"README.md": GOOD_README, "analysis.py": "print(3)\n"}, {"run_command"},
                   "the README says python3 main.py, but the file is analysis.py")

    def test_not_a_python_command(self):
        self.check({"README.md": GOOD_README.replace("python3 main.py", "bash run.sh"), "run.sh": "echo 3\n"},
                   {"run_command"}, "the one command should be python3 <file>.py")

    def test_script_that_fails(self):
        self.check({"README.md": GOOD_README, "main.py": "import sys\nsys.exit(1)\n"}, {"runs"},
                   "a script that exits with code 1 does not run")

    def test_safe_patterns(self):
        files = {"README.md": GOOD_README,
                 "main.py": ("# data from https://example.org/open-data, read on 1 October 2026\n"
                             "import os\nimport helpers\nAPI_KEY = os.environ.get(\"API_KEY_FOR_LATER_USE_ONLY\")\n"
                             "print(helpers.three())\n"),
                 "helpers.py": "def three():\n    return 3\n",
                 ".env.example": "API_KEY=\n",
                 "requirements.txt": "# standard library only\n",
                 "data/empty.csv": ""}
        self.check(files, set(), "a URL in a comment, a key read from the environment, a local module, "
                                 ".env.example, a comment-only requirements file and an empty file are all fine")

    def test_pinned_requirements(self):
        files = {"README.md": GOOD_README, "main.py": "import pandas\nprint(3)\n", "requirements.txt": "pandas==2.2.3\n"}
        self.check(files, set(), "pinned requirements are fine (the project is not run, because it needs packages)")

    def test_large_file(self):
        files = {"README.md": GOOD_README, "main.py": "print(3)\n", "data/big.csv": "x\n" * 600000}
        self.check(files, {"large_file"}, "a 1.2 MB file is over the 1,000,000 byte limit")

    def test_secret_in_code(self):
        files = {"README.md": GOOD_README, "main.py": "token = 'abcd1234abcd1234abcd'\nprint(3)\n"}
        self.check(files, {"secret"}, "a 20 character token in the code is a secret, even if it is fake")


if __name__ == "__main__":
    unittest.main()
