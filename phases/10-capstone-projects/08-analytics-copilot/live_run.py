"""Optional: run the planner and recommender agents against a real model, using your own key.

The test never runs this. This file holds no key and opens no network connection itself. You give
it a command that sends one prompt to the model of your choice and prints the reply; that command
(your own script or a provider's command-line tool) holds your key in its own environment.

1. Plan:       LLM_COMMAND="python3 my_model_call.py" python3 live_run.py plan --out live_session
   Sends the planner prompt and saves live_session/plan.json (the reply must be a JSON list of
   steps shaped like data/plan.json). Then write live_session/approvals.csv yourself: you are the reviewer.
2. Draft:      LLM_COMMAND=... python3 live_run.py draft --out live_session
   Runs the approved query and check steps with your run_plan (no draft yet), sends the results to
   the recommender prompt, and saves live_session/draft.json (JSON shaped like data/draft.json).
3. Replay:     python3 live_run.py replay --out live_session
   Replays the whole session with your run_plan and prints the log and the release decision.

Each step also writes live_session/fixture.json (model, date, temperature, prompts). Nothing in data/
changes. By default the code comes from your exercise.py; add --use-solution to use the worked answer.
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
PLANNER = """You are the planner and query agent of an analytics copilot for Bramblequay Bikes.
Question: Weekend rentals fell in September 2026 compared with August. Why?
You may query only these SQLite tables (weekend means Saturday and Sunday):
  rentals(rental_id, station_id, start_date, start_hour, duration_min, rider_type, rider_id)
  stations(station_id, name, zone, docks)
  station_events(station_id, event, start_date, end_date, note)
  riders(rider_id, plan, signup_date)
Reply with JSON only: a list of steps, each {"step": "S1", "kind": "query" | "check" | "recommend",
"agent": ..., "depends_on": [...], "purpose": ..., "sql": ... for a query, "check": "reconcile" | "noise"
for a check}. reconcile compares zone rows (columns zone, month, rentals) with monthly totals (month,
rentals, days); noise compares daily rows (start_date, month, rentals) for August and September.
End with one recommend step."""
RECOMMENDER = """You are the recommender of an analytics copilot for Bramblequay Bikes.
Question: Weekend rentals fell in September 2026 compared with August. Why, and what should we do?
Here are the results of the steps that ran, as JSON:
{results}
Reply with JSON only: {{"text": your recommendation, "claims": [...]}}. Every number in the text must
have a claim: {{"id": "C1", "text": the number exactly as written, "kind": "value" | "count" | "pct_change"
| "pct_fall" | "assumption", "step": ..., "where": {{column: value}}, "expr": "column" or "column / column"}};
pct_change and pct_fall take "from" and "to", each {{"step", "where", "expr"}}. Label proposals as assumption."""


def load_submission(use_solution):
    path = os.path.join(HERE, "solution", "solution.py") if use_solution else os.path.join(HERE, "exercise.py")
    spec = importlib.util.spec_from_file_location("submission", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ask(prompt):
    command = os.environ.get("LLM_COMMAND")
    if not command:
        sys.exit("Set LLM_COMMAND to a command that reads a prompt on stdin and prints the model's reply.")
    done = subprocess.run(command, shell=True, input=prompt, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=300)
    if done.returncode != 0:
        sys.exit("LLM_COMMAND failed: " + done.stderr.strip()[:300])
    text = done.stdout.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except ValueError:
        sys.exit("The reply was not JSON:\n" + text[:500])


def write_fixture(out, role, prompt):
    path = os.path.join(out, "fixture.json")
    fixture = json.load(open(path)) if os.path.exists(path) else {"source": "recorded"}
    fixture.update({"model": os.environ.get("LLM_MODEL_NAME", "not given: set LLM_MODEL_NAME"),
                    "temperature": os.environ.get("LLM_TEMPERATURE", "not given: set LLM_TEMPERATURE"),
                    "date_" + role: datetime.date.today().isoformat(), "prompt_" + role: prompt})
    with open(path, "w") as f:
        json.dump(fixture, f, indent=2, sort_keys=True)
        f.write("\n")


def read_approvals(out):
    path = os.path.join(out, "approvals.csv")
    if not os.path.exists(path):
        sys.exit("Write %s first (columns step, decision, edited_sql, reviewer, note): you are the reviewer." % path)
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def replay(sub, out, draft):
    data = sub.load()
    plan = json.load(open(os.path.join(out, "plan.json")))
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "bramblequay.db")
        sub.build_db(path, data)
        return sub.run_plan(plan, read_approvals(out), path, draft)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("action", choices=["plan", "draft", "replay"])
    parser.add_argument("--out", default="live_session")
    parser.add_argument("--use-solution", action="store_true")
    args = parser.parse_args()
    sub = load_submission(args.use_solution)
    os.makedirs(args.out, exist_ok=True)
    if args.action == "plan":
        plan = ask(PLANNER)
        sub.validate_plan(plan)
        json.dump(plan, open(os.path.join(args.out, "plan.json"), "w"), indent=2)
        write_fixture(args.out, "planner", PLANNER)
        print("saved the plan; now write", os.path.join(args.out, "approvals.csv"))
    elif args.action == "draft":
        run = replay(sub, args.out, {"text": "", "claims": []})
        results = {k: v for k, v in run["results"].items() if isinstance(v, list)}
        prompt = RECOMMENDER.format(results=json.dumps(results, indent=1, default=str))
        draft = ask(prompt)
        json.dump(draft, open(os.path.join(args.out, "draft.json"), "w"), indent=2)
        write_fixture(args.out, "recommender", RECOMMENDER)
        print("saved the draft")
    else:
        run = replay(sub, args.out, json.load(open(os.path.join(args.out, "draft.json"))))
        for e in run["log"]:
            print(e["step"], e["status"], e["detail"])
        final = [v for v in run["results"].values() if isinstance(v, dict)]
        if final:
            print(final[-1]["release"])


if __name__ == "__main__":
    main()
