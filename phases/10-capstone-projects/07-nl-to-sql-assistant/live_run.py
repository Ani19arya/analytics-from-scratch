"""Optional: re-record the replies with a real model, using your own key. The test never runs this.

This file holds no key and opens no network connection itself. You give it a command that sends
one prompt to the model of your choice and prints the reply; that command (your own script or a
provider's command-line tool) holds your key in its own environment. For every question and both
prompt versions, this script builds the prompt with build_prompt(), pipes it to your command on
stdin, and saves the reply.

    LLM_COMMAND="python3 my_model_call.py" LLM_MODEL_NAME="the model you used" \
        python3 live_run.py --out live_runs

It writes live_runs/model_runs.csv (same columns as data/model_runs.csv) and live_runs/fixture.json
(model, date, prompt, temperature). Nothing in data/ changes. Then grade the new replies:

    python3 live_run.py --grade live_runs

By default build_prompt() comes from your exercise.py; add --use-solution to use the worked answer.
Recorded replies cost money and change between model versions: record once, grade many times.
"""
import argparse
import csv
import datetime
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def load_submission(use_solution):
    path = os.path.join(HERE, "solution", "solution.py") if use_solution else os.path.join(HERE, "exercise.py")
    spec = importlib.util.spec_from_file_location("submission", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record(sub, out, command):
    data = sub.load()
    os.makedirs(out, exist_ok=True)
    rows = []
    for q in data["eval_set"]:
        for version in ("v1", "v2"):
            prompt = sub.build_prompt(q["question"], version, data["glossary"])
            done = subprocess.run(command, shell=True, input=prompt, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
            if done.returncode != 0:
                sys.exit("LLM_COMMAND failed on %s %s: %s" % (q["question_id"], version, done.stderr.strip()[:300]))
            rows.append({"question_id": q["question_id"], "prompt_version": version, "reply": done.stdout.strip()})
            print(q["question_id"], version, done.stdout.strip()[:70].replace("\n", " "))
    with open(os.path.join(out, "model_runs.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["question_id", "prompt_version", "reply"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    fixture = {
        "file": "model_runs.csv",
        "reply_source": "recorded",
        "model": os.environ.get("LLM_MODEL_NAME", "not given: set LLM_MODEL_NAME"),
        "temperature": os.environ.get("LLM_TEMPERATURE", "not given: set LLM_TEMPERATURE"),
        "date": datetime.date.today().isoformat(),
        "prompt": "build_prompt() from %s, versions v1 and v2" % ("solution" if sub.__file__.endswith("solution.py") else "exercise.py"),
        "how": "live_run.py piped each prompt to LLM_COMMAND and saved its stdout",
    }
    with open(os.path.join(out, "fixture.json"), "w") as f:
        json.dump(fixture, f, indent=2, sort_keys=True)
        f.write("\n")
    print("wrote", os.path.join(out, "model_runs.csv"))


def grade(sub, folder):
    data = sub.load()
    with open(os.path.join(folder, "model_runs.csv"), newline="") as f:
        runs = list(csv.DictReader(f))
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "copperwren.db")
        sub.build_db(path, data)
        outcomes = sub.grade_all(path, data["eval_set"], runs)
    cards = [sub.scorecard(outcomes, data["eval_set"], v) for v in ("v1", "v2")]
    for c in cards:
        print("%s correct %d of %d (95%% %.2f to %.2f), wrong %d, asked back %d of %d, unsafe %d" % (
            c["version"], c["correct"], c["answerable"], c["wilson_low"], c["wilson_high"], c["wrong"],
            c["clarified"], c["ambiguous"], c["unsafe"]))
    comp = sub.compare(outcomes, data["eval_set"])
    print("v2:", sub.recommend(cards[1], comp))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default="live_runs", help="folder for the recorded replies")
    parser.add_argument("--grade", metavar="FOLDER", help="grade replies already recorded in FOLDER")
    parser.add_argument("--use-solution", action="store_true", help="use solution/solution.py instead of exercise.py")
    args = parser.parse_args()
    sub = load_submission(args.use_solution)
    if args.grade:
        grade(sub, args.grade)
        return
    command = os.environ.get("LLM_COMMAND")
    if not command:
        sys.exit("Set LLM_COMMAND to a command that reads a prompt on stdin and prints the model's reply.")
    record(sub, args.out, command)


if __name__ == "__main__":
    main()
