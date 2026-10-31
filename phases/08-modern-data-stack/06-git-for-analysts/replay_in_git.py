"""Optional: replay the recorded history in data/ into a real git repository.

    python3 replay_in_git.py /tmp/brightcart-sql

It makes a NEW folder (it refuses to use one that already exists, or any
folder inside this course), runs git init there, and makes one real commit
per row of data/commits.csv, with the recorded author, date and message.
The commits use fixed names, emails and dates, so with git's default SHA-1
format everyone gets the same commit hashes.

Then try, inside that folder: git log --oneline, git blame revenue.sql,
git show <commit>, git revert <commit>. Delete the folder when you are done.

Needs git on your PATH. Python 3.9+ standard library only.
"""
import csv
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COURSE = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def git(target, *args, env=None):
    return subprocess.run(["git", "-C", target] + list(args), check=True, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True).stdout


def clean_env(target):
    """An environment that ignores the user's own git settings (hooks, signing, templates)."""
    env = dict(os.environ)
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "HOME": target,
                "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"})
    return env


def replay(target, data_dir=os.path.join(HERE, "data")):
    """Create target and replay the history into it. Returns {recorded commit_id: real git hash}."""
    target = os.path.abspath(target)
    if os.path.exists(target):
        raise SystemExit("%s already exists: pick a new folder" % target)
    if os.path.realpath(target).startswith(os.path.realpath(COURSE) + os.sep):
        raise SystemExit("pick a folder outside the course repository, for example /tmp/brightcart-sql")
    with open(os.path.join(data_dir, "commits.csv"), newline="") as f:
        commits = list(csv.DictReader(f))
    files = {}
    with open(os.path.join(data_dir, "file_versions.csv"), newline="") as f:
        for r in csv.DictReader(f):
            files.setdefault((r["commit_id"], r["path"]), []).append((int(r["line_no"]), r["line"]))
    os.makedirs(target)
    env = clean_env(target)
    git(target, "init", "-q", env=env)
    git(target, "symbolic-ref", "HEAD", "refs/heads/main", env=env)
    # Settings for this throwaway repository only, so that your own commits here
    # (a revert, say) work even if git does not know your name yet.
    git(target, "config", "user.name", "Analyst", env=env)
    git(target, "config", "user.email", "analyst@brightcart.example", env=env)
    git(target, "config", "commit.gpgsign", "false", env=env)
    hashes = {}
    for c in commits:
        for (cid, path), lines in sorted(files.items()):
            if cid == c["commit_id"]:
                with open(os.path.join(target, path), "w", newline="\n") as out:
                    out.write("\n".join(text for _, text in sorted(lines)) + "\n")
        email = c["author"].lower() + "@brightcart.example"
        stamp = c["committed_at"].replace(" ", "T") + "+0000"
        env_c = dict(env, GIT_AUTHOR_NAME=c["author"], GIT_AUTHOR_EMAIL=email, GIT_AUTHOR_DATE=stamp,
                     GIT_COMMITTER_NAME=c["author"], GIT_COMMITTER_EMAIL=email, GIT_COMMITTER_DATE=stamp)
        git(target, "add", "-A", env=env_c)
        git(target, "commit", "-q", "-m", c["message"], env=env_c)
        hashes[c["commit_id"]] = git(target, "rev-parse", "HEAD", env=env_c).strip()
    return hashes


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    hashes = replay(argv[1])
    print("replayed %d commits into %s" % (len(hashes), os.path.abspath(argv[1])))
    for recorded, real in hashes.items():
        print("  recorded %s is git commit %s" % (recorded, real[:7]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
