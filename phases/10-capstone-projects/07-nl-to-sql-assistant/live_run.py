"""Optional LIVE mode for capstone 10-07: ask a real model, record its replies, grade them offline.

The capstone works without this file and the test never calls a real model: it drives this code
with FakeAdapter, with no network and no key. Use it when you want to see how a real model does on
the same 42 questions, and what calling an API properly involves: retries, a budget, structured
output, a safety gateway and a record of exactly what was run.

Three ways to reach a model (adapters), all in the standard library, no provider SDK:

  openai   any "OpenAI-compatible chat completions" endpoint. Set LLM_BASE_URL (the part before
           /chat/completions), LLM_API_KEY and LLM_MODEL in your environment.
  command  a command you supply in LLM_COMMAND that reads a prompt on stdin and prints the reply.
           That command holds its own key. Set LLM_MODEL to the model name for the record.
  fake     replays the simulated replies in data/model_runs.csv as JSON. No key, no network, no
           cost: use it to try the whole pipeline first (--dry-run).

    python3 live_run.py --dry-run --use-solution          # free rehearsal with the fake adapter
    python3 live_run.py --use-solution --limit 4          # a small live run: 4 questions, 8 calls
    python3 live_run.py --use-solution                    # every question, both prompt versions
    python3 live_run.py --use-solution --grade data/live_runs/<folder>

Each run writes data/live_runs/<UTC time>/ (git-ignored): model_runs.csv with the same columns
as data/model_runs.csv, calls.csv with one row per question and version (tokens, retries,
gateway result), and fixture.json with the provenance (model, date, prompt version, temperature,
tokens, cost, budget). --grade scores it with the same offline grader and puts the simulated
scorecards next to it.

The key is read only from the environment, sent only in the Authorization header over HTTPS
(plain http only to localhost), never printed, and every file is checked before it is written:
if the key would end up in one, nothing is written and the run stops.

Prices: the rate card below is FICTIONAL. Set LLM_PRICE_IN and LLM_PRICE_OUT (price per million
tokens, from your provider's own price page) for a real estimate. Live replies cost money and
change between model versions and from run to run: record once, grade many times.
"""
import argparse
import csv
import datetime
import hashlib
import importlib.util
import io
import json
import math
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LIVE_ROOT = os.path.join(HERE, "data", "live_runs")
STRUCTURED_VERSION = "json-1"
KINDS = ("sql", "clarify", "refuse")
MAX_REASON = 300
CALL_FIELDS = ["question_id", "prompt_version", "status", "kind", "calls", "retries", "schema_error",
               "gateway_status", "gateway_reason", "rows", "prompt_tokens", "completion_tokens",
               "token_source", "cost", "seconds"]

# FICTIONAL example rates, for practice only. They are not any provider's price. Replace them with
# your provider's published rates (LLM_PRICE_IN, LLM_PRICE_OUT) before you trust a cost figure.
FICTIONAL_RATE_CARD = {
    "label": "FICTIONAL example rate card: not a real price from any provider",
    "currency": "fictional dollars",
    "input_per_million_tokens": 1.00,
    "output_per_million_tokens": 5.00,
}


# ---------- errors ----------

class TransientError(Exception):
    """Worth retrying: 429 (rate limit), 5xx (server trouble) or a timeout."""

    def __init__(self, message, status=None, retry_after=None):
        Exception.__init__(self, message)
        self.status = status
        self.retry_after = retry_after


class PermanentError(Exception):
    """Not worth retrying: a bad key, a bad request, an unknown model."""


class SecretLeak(Exception):
    """The key would have been written to a file, printed, or sent somewhere it should not go."""


# ---------- the key ----------

def read_key(env=None):
    """The API key, from the environment only. There is deliberately no command-line flag."""
    env = os.environ if env is None else env
    return env.get("LLM_API_KEY", "")


def scrub(text, secrets):
    """text with every secret replaced by [redacted]."""
    text = str(text)
    for s in secrets:
        if s:
            text = text.replace(s, "[redacted]")
    return text


def check_no_secret(text, secrets, where):
    for s in secrets:
        if s and s in text:
            raise SecretLeak("the API key would have been written to %s; nothing was written" % where)


def write_safely(path, text, secrets):
    """Write text to path, unless a secret is in it: then raise SecretLeak and write nothing."""
    check_no_secret(text, secrets, os.path.basename(path))
    check_no_secret(path, secrets, "a file name")
    with open(path, "w", newline="") as f:
        f.write(text)


def check_config(settings, secrets):
    """Refuse to run if the key sits in any setting that gets recorded or printed."""
    for name, value in settings.items():
        for s in secrets:
            if s and value and s in str(value):
                raise SecretLeak("the API key is inside %s, which is recorded in fixture.json; "
                                 "keep it only in LLM_API_KEY" % name)


# ---------- adapters ----------

class Reply(object):
    """What any adapter returns: the text, and the provider's token usage if it gave one."""

    def __init__(self, text, usage=None):
        self.text = text
        self.usage = usage


class Adapter(object):
    """Plug in a provider by writing complete(); raise TransientError or PermanentError on failure."""
    name = "adapter"
    model = "unknown"
    endpoint = ""

    def complete(self, messages, temperature, max_tokens, timeout, meta=None):
        raise NotImplementedError


class OpenAICompatibleAdapter(Adapter):
    """POST {base_url}/chat/completions with a bearer key. Works with any provider or local server
    that speaks this format. urlopen is a parameter so the test can stand in for the network."""
    name = "openai-compatible chat completions"

    def __init__(self, base_url, api_key, model, urlopen=None):
        if not base_url or not model:
            raise PermanentError("set LLM_BASE_URL and LLM_MODEL")
        if not api_key:
            raise PermanentError("set LLM_API_KEY in your environment (never on the command line)")
        parts = urllib.parse.urlsplit(base_url)
        local = parts.hostname in ("localhost", "127.0.0.1", "::1")
        if parts.scheme != "https" and not (parts.scheme == "http" and local):
            raise SecretLeak("LLM_BASE_URL must start with https:// (plain http only to localhost): "
                             "otherwise the key travels unencrypted")
        if parts.query or parts.username or parts.password:
            raise PermanentError("LLM_BASE_URL must not carry a query string or a user name; "
                                 "the key goes only in LLM_API_KEY")
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.endpoint = parts.hostname or ""
        self.model = model
        self._key = api_key
        self._urlopen = urlopen or urllib.request.urlopen

    def __repr__(self):
        return "OpenAICompatibleAdapter(%r, model=%r, key=[redacted])" % (self.endpoint, self.model)

    def complete(self, messages, temperature, max_tokens, timeout, meta=None):
        body = json.dumps({"model": self.model, "messages": messages, "temperature": temperature,
                           "max_tokens": max_tokens}).encode("utf-8")
        req = urllib.request.Request(self.url, data=body, method="POST", headers={
            "Content-Type": "application/json", "Authorization": "Bearer " + self._key})
        try:
            with self._urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = scrub(_read_error(e), [self._key])
            retry_after = _retry_after(e.headers)
            if e.code == 429 or 500 <= e.code < 600:
                raise TransientError("HTTP %d: %s" % (e.code, detail), e.code, retry_after)
            raise PermanentError("HTTP %d: %s" % (e.code, detail))
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            raise TransientError("network or timeout: %s" % scrub(getattr(e, "reason", e), [self._key]))
        try:
            data = json.loads(raw)
            text = data["choices"][0]["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError):
            raise PermanentError("the response is not in chat completions format: %s" % scrub(raw[:200], [self._key]))
        return Reply(text, data.get("usage"))


def _read_error(e):
    try:
        return e.read().decode("utf-8", "replace")[:300]
    except Exception:
        return str(e.reason)


def _retry_after(headers):
    try:
        value = headers.get("Retry-After") if headers is not None else None
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


class CommandAdapter(Adapter):
    """Pipe the prompt to a command on stdin; its stdout is the reply. The command keeps its own key."""
    name = "command (LLM_COMMAND)"

    def __init__(self, command, model):
        self.command = command
        self.model = model or "not given: set LLM_MODEL"

    def complete(self, messages, temperature, max_tokens, timeout, meta=None):
        if len(messages) == 1:
            text = messages[0]["content"]
        else:
            text = "\n\n".join("[%s]\n%s" % (m["role"], m["content"]) for m in messages)
        try:
            done = subprocess.run(self.command, shell=True, input=text, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, universal_newlines=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise TransientError("LLM_COMMAND took longer than %s seconds" % timeout)
        if done.returncode != 0:
            raise PermanentError("LLM_COMMAND exited %d: %s" % (done.returncode, done.stderr.strip()[:300]))
        return Reply(done.stdout.strip(), None)


class FakeAdapter(Adapter):
    """For the test and for --dry-run. `script` is a list consumed one item per call, or a function
    called as script(messages, meta). An item is a Reply, a text (a Reply with no usage), or an
    exception instance, which is raised. Every call is kept in self.calls."""
    name = "fake (no model called)"

    def __init__(self, script, model="fake"):
        self.script = script if callable(script) else list(script)
        self.model = model
        self.calls = []

    def complete(self, messages, temperature, max_tokens, timeout, meta=None):
        self.calls.append({"messages": [dict(m) for m in messages], "meta": meta, "temperature": temperature})
        item = self.script(messages, meta) if callable(self.script) else self.script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item if isinstance(item, Reply) else Reply(item, None)


# ---------- retries ----------

def backoff_delay(attempt, base, cap, rand):
    """Exponential backoff with jitter for the wait after failed attempt number `attempt` (1, 2, ...).
    The ceiling doubles each time (base, 2 base, 4 base, ...) up to cap; the wait is a random point
    in the top half of it, so clients that failed together do not all retry at the same moment."""
    ceiling = min(cap, base * 2 ** (attempt - 1))
    return ceiling / 2 + rand() * ceiling / 2


def call_with_retry(adapter, messages, temperature, max_tokens, timeout=60, max_attempts=4, base_delay=1.0,
                    max_delay=30.0, sleep=time.sleep, rand=random.random, meta=None, log=None):
    """Call the adapter; on TransientError wait and try again, up to max_attempts calls in all.
    PermanentError is raised at once. Returns (reply, number of calls, list of waits)."""
    waits = []
    for attempt in range(1, max_attempts + 1):
        try:
            return adapter.complete(messages, temperature, max_tokens, timeout, meta), attempt, waits
        except TransientError as e:
            if attempt == max_attempts:
                raise TransientError("gave up after %d attempts: %s" % (attempt, e), e.status)
            wait = backoff_delay(attempt, base_delay, max_delay, rand)
            if e.retry_after is not None:
                wait = min(max_delay, max(wait, e.retry_after))
            waits.append(wait)
            if log:
                log("  retry %d after %.1fs (%s)" % (attempt, wait, e))
            sleep(wait)


# ---------- tokens, cost and the budget ----------

def estimate_tokens(text):
    """An ESTIMATE: about 4 characters per token for English. Use the provider's count when it gives one."""
    return max(1, int(math.ceil(len(text) / 4.0)))


def rate_card(env=None):
    env = os.environ if env is None else env
    if env.get("LLM_PRICE_IN") and env.get("LLM_PRICE_OUT"):
        return {"label": "user-supplied rates (LLM_PRICE_IN, LLM_PRICE_OUT)", "currency": env.get("LLM_CURRENCY", "your currency"),
                "input_per_million_tokens": float(env["LLM_PRICE_IN"]), "output_per_million_tokens": float(env["LLM_PRICE_OUT"])}
    return dict(FICTIONAL_RATE_CARD)


def cost_of(prompt_tokens, completion_tokens, card):
    return (prompt_tokens * card["input_per_million_tokens"] + completion_tokens * card["output_per_million_tokens"]) / 1e6


class Budget(object):
    """A cap on tokens and on money for one run. Before each call, ask allows() with a worst-case
    estimate; after it, charge() what was used. A cap of None means no cap."""

    def __init__(self, max_tokens=None, max_cost=None, card=None):
        self.max_tokens, self.max_cost = max_tokens, max_cost
        self.card = card or dict(FICTIONAL_RATE_CARD)
        self.tokens = 0
        self.cost = 0.0

    def allows(self, prompt_tokens, completion_tokens):
        """None if a call of this size fits, else the reason it does not."""
        if self.max_tokens is not None and self.tokens + prompt_tokens + completion_tokens > self.max_tokens:
            return "token cap %d: %d used, next call could use %d" % (self.max_tokens, self.tokens, prompt_tokens + completion_tokens)
        extra = cost_of(prompt_tokens, completion_tokens, self.card)
        if self.max_cost is not None and self.cost + extra > self.max_cost:
            return "cost cap %.4f: %.4f used, next call could cost %.4f (%s)" % (self.max_cost, self.cost, extra, self.card["label"])
        return None

    def charge(self, prompt_tokens, completion_tokens):
        self.tokens += prompt_tokens + completion_tokens
        spent = cost_of(prompt_tokens, completion_tokens, self.card)
        self.cost += spent
        return spent


def usage_of(reply, messages):
    """(prompt tokens, completion tokens, 'reported' or 'estimated')."""
    u = reply.usage or {}
    if isinstance(u.get("prompt_tokens"), int) and isinstance(u.get("completion_tokens"), int):
        return u["prompt_tokens"], u["completion_tokens"], "reported"
    return estimate_tokens(" ".join(m["content"] for m in messages)), estimate_tokens(reply.text), "estimated"


# ---------- structured output ----------

def json_instructions():
    """Appended to build_prompt()'s text. It names all three kinds for both versions, which tells v1
    that asking back and refusing are allowed: one reason live v1 can differ from the simulated v1."""
    return "\n".join([
        "Reply format (%s): one JSON object and nothing else, with exactly these keys:" % STRUCTURED_VERSION,
        '  "kind": "sql", "clarify" or "refuse"',
        '  "sql": the SQLite query when kind is "sql", otherwise ""',
        '  "reason": one short sentence: why the query answers the question, or your clarifying question, or why you refuse',
    ])


def validate_reply(text):
    """(object, None) if text is valid JSON matching the schema above, else (None, what is wrong)."""
    body = text.strip()
    if body.startswith("```"):
        body = body[3:]
        if body.lower().startswith("json"):
            body = body[4:]
        end = body.rfind("```")
        body = (body[:end] if end != -1 else body).strip()
    try:
        obj = json.loads(body)
    except ValueError as e:
        return None, "not valid JSON (%s)" % e
    if not isinstance(obj, dict):
        return None, "the reply must be a JSON object"
    missing = [k for k in ("kind", "sql", "reason") if k not in obj]
    extra = sorted(k for k in obj if k not in ("kind", "sql", "reason"))
    if missing:
        return None, "missing key(s): %s" % ", ".join(missing)
    if extra:
        return None, "unexpected key(s): %s" % ", ".join(extra)
    if obj["kind"] not in KINDS:
        return None, 'kind must be "sql", "clarify" or "refuse"'
    if not isinstance(obj["sql"], str) or not isinstance(obj["reason"], str):
        return None, "sql and reason must be strings"
    if not obj["reason"].strip() or len(obj["reason"]) > MAX_REASON:
        return None, "reason must be 1 to %d characters" % MAX_REASON
    if obj["kind"] == "sql" and not obj["sql"].strip():
        return None, 'kind is "sql" but sql is empty'
    if obj["kind"] != "sql" and obj["sql"].strip():
        return None, 'sql must be "" when kind is "%s"' % obj["kind"]
    return obj, None


def as_reply_text(obj):
    """The reply in the plain format the grader reads (data/model_runs.csv)."""
    if obj["kind"] == "clarify":
        return "CLARIFY: " + obj["reason"].strip()
    if obj["kind"] == "refuse":
        return "REFUSE: " + obj["reason"].strip()
    return obj["sql"].strip()


# ---------- one recorded run ----------

def _csv_text(fields, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def record_run(questions, adapter, out_dir, prompt_fn, gateway, versions=("v1", "v2"), budget=None,
               temperature=0.0, max_output_tokens=300, timeout=60, max_attempts=4, base_delay=1.0,
               max_delay=30.0, sleep=time.sleep, clock=time.monotonic, rand=random.random,
               secrets=(), provenance=None, log=print):
    """Ask the model every question in every version and record the run in out_dir.

    prompt_fn(question, version) is the prompt; gateway(sql) runs SQL behind the read-only gateway
    and returns run_guarded's dict. Nothing here runs SQL any other way. A reply that fails the
    schema gets one retry with the error; if it fails again it is recorded as an empty reply, which
    the grader can never count as correct. A call that keeps failing, or a budget cap, stops the run;
    what was done so far is still recorded. Returns the fixture dict.
    """
    budget = budget or Budget()
    secrets = [s for s in secrets if s]
    say = lambda text: log(scrub(text, secrets))
    if os.path.exists(os.path.join(out_dir, "model_runs.csv")):
        raise PermanentError("%s already holds a recording; never overwrite one" % out_dir)
    runs, calls, stopped = [], [], ""
    for q in questions:
        for version in versions:
            if stopped:
                break
            messages = [{"role": "user", "content": prompt_fn(q["question"], version) + "\n" + json_instructions()}]
            row = {"question_id": q["question_id"], "prompt_version": version, "status": "", "kind": "", "calls": 0,
                   "retries": 0, "schema_error": "", "gateway_status": "", "gateway_reason": "", "rows": "",
                   "prompt_tokens": 0, "completion_tokens": 0, "token_source": "", "cost": 0.0, "seconds": 0.0}
            obj = None
            for check in (1, 2):
                need = estimate_tokens(" ".join(m["content"] for m in messages))
                why = budget.allows(need, max_output_tokens)
                if why:
                    stopped, row["status"] = "budget: " + why, "budget_stopped"
                    break
                started = clock()
                try:
                    reply, n, waits = call_with_retry(adapter, messages, temperature, max_output_tokens, timeout,
                                                      max_attempts, base_delay, max_delay, sleep, rand,
                                                      (q["question_id"], version), say)
                except (TransientError, PermanentError) as e:
                    stopped, row["status"] = "call failed: %s" % scrub(e, secrets), "call_failed"
                    break
                row["seconds"] += clock() - started
                row["calls"] += n
                row["retries"] += len(waits)
                p, c, source = usage_of(reply, messages)
                row["prompt_tokens"] += p
                row["completion_tokens"] += c
                row["token_source"] = source if row["token_source"] in ("", source) else "mixed"
                row["cost"] += budget.charge(p, c)
                obj, error = validate_reply(reply.text)
                if obj:
                    break
                row["schema_error"] = error
                if check == 1:
                    messages = messages + [
                        {"role": "assistant", "content": reply.text},
                        {"role": "user", "content": "Your reply was not valid: %s. Reply again with only the JSON object "
                                                    "described above." % error}]
            if row["status"] in ("budget_stopped", "call_failed") and row["calls"] == 0:
                say("stopped before %s %s: %s" % (q["question_id"], version, stopped))
                break
            if obj is None:
                row["status"] = row["status"] or "schema_failed"
                reply_text = ""
            else:
                row["status"], row["kind"], row["schema_error"] = "ok", obj["kind"], ""
                reply_text = as_reply_text(obj)
                if obj["kind"] == "sql":
                    result = gateway(reply_text)
                    row["gateway_status"] = result["status"]
                    row["gateway_reason"] = result["reason"]
                    row["rows"] = "" if result["rows"] is None else len(result["rows"])
            row["cost"] = round(row["cost"], 6)
            row["seconds"] = round(row["seconds"], 3)
            runs.append({"question_id": q["question_id"], "prompt_version": version, "reply": reply_text})
            calls.append(row)
            say("%s %s %-13s %-7s %s" % (q["question_id"], version, row["status"], row["kind"],
                                        row["gateway_status"] or reply_text[:50].replace("\n", " ")))
        if stopped:
            break
    reported = sum(1 for r in calls if r["token_source"] == "reported")
    fixture = dict(provenance or {})
    fixture.update({
        "file": "model_runs.csv",
        "calls_file": "calls.csv",
        "reply_source": "recorded live" if not isinstance(adapter, FakeAdapter) else "fake adapter (no model called)",
        "adapter": adapter.name,
        "model": adapter.model,
        "endpoint_host": adapter.endpoint or "not applicable",
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "structured_output": STRUCTURED_VERSION,
        "versions": list(versions),
        "replies_recorded": len(runs),
        "schema_failures": sum(1 for r in calls if r["status"] == "schema_failed"),
        "gateway_blocked": sum(1 for r in calls if r["gateway_status"] == "blocked"),
        "retries": sum(r["retries"] for r in calls),
        "tokens": {"prompt": sum(r["prompt_tokens"] for r in calls), "completion": sum(r["completion_tokens"] for r in calls),
                   "calls_with_reported_usage": reported, "calls_with_estimated_usage": len(calls) - reported,
                   "estimate_rule": "about 4 characters per token: an estimate, not the provider's count"},
        "cost": {"amount": round(budget.cost, 6), "currency": budget.card["currency"], "rate_card": budget.card},
        "budget": {"max_tokens": budget.max_tokens, "max_cost": budget.max_cost, "stopped_early": stopped},
    })
    os.makedirs(out_dir, exist_ok=True)
    files = {"model_runs.csv": _csv_text(["question_id", "prompt_version", "reply"], runs),
             "calls.csv": _csv_text(CALL_FIELDS, calls),
             "fixture.json": json.dumps(fixture, indent=2, sort_keys=True) + "\n"}
    for name, text in files.items():
        check_no_secret(text, secrets, name)
    for name, text in files.items():
        write_safely(os.path.join(out_dir, name), text, secrets)
    say("wrote %d replies to %s%s" % (len(runs), out_dir, (" (stopped early: %s)" % stopped) if stopped else ""))
    return fixture


# ---------- grading: the same offline grader, live next to simulated ----------

def load_submission(use_solution):
    path = os.path.join(HERE, "solution", "solution.py") if use_solution else os.path.join(HERE, "exercise.py")
    spec = importlib.util.spec_from_file_location("submission", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score(sub, path, questions, runs):
    outcomes = sub.grade_all(path, questions, runs)
    have = {}
    for (qid, v) in outcomes:
        have.setdefault(qid, set()).add(v)
    paired = [q for q in questions if have.get(q["question_id"]) == {"v1", "v2"}]
    cards = {v: sub.scorecard(outcomes, questions, v) for v in ("v1", "v2") if any(k[1] == v for k in outcomes)}
    comp = sub.compare(outcomes, paired) if paired else None
    return outcomes, cards, comp


def grade(sub, folder, log=print):
    data = sub.load()
    with open(os.path.join(folder, "model_runs.csv"), newline="") as f:
        live = list(csv.DictReader(f))
    keys = {(r["question_id"], r["prompt_version"]) for r in live}
    simulated = [r for r in data["model_runs"] if (r["question_id"], r["prompt_version"]) in keys]
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "copperwren.db")
        sub.build_db(path, data)
        out = {name: score(sub, path, data["eval_set"], runs) for name, runs in (("live", live), ("simulated", simulated))}
    if len(live) < 2 * len(data["eval_set"]):
        log("partial run: %d of %d replies; both columns use the same %d" % (len(live), 2 * len(data["eval_set"]), len(live)))
    for name in ("live", "simulated"):
        outcomes, cards, comp = out[name]
        for v, c in sorted(cards.items()):
            log("%-9s %s correct %d of %d (95%% %.2f to %.2f), wrong %d, asked back %d of %d, unsafe %d" % (
                name, v, c["correct"], c["answerable"], c["wilson_low"], c["wilson_high"], c["wrong"],
                c["clarified"], c["ambiguous"], c["unsafe"]))
        if comp and "v2" in cards:
            log("%-9s v2: %s" % (name, sub.recommend(cards["v2"], comp)))
    differ = [(k, out["simulated"][0][k], out["live"][0][k]) for k in sorted(out["live"][0]) if out["live"][0][k] != out["simulated"][0][k]]
    log("%d replies graded differently (question, version: simulated -> live)" % len(differ))
    for (qid, v), a, b in differ:
        log("  %s %s: %s -> %s" % (qid, v, a, b))
    return out


# ---------- the command line ----------

def replay_simulated(sub):
    """A FakeAdapter script for --dry-run: the simulated reply to each question, wrapped in the JSON schema."""
    replies = {(r["question_id"], r["prompt_version"]): r["reply"] for r in sub.load()["model_runs"]}

    def script(messages, meta):
        kind, text = sub.parse_reply(replies[meta])
        obj = {"kind": kind, "sql": text if kind == "sql" else "", "reason": "replayed" if kind == "sql" else text}
        return json.dumps(obj)
    return script


def make_adapter(name, env):
    if name == "openai":
        return OpenAICompatibleAdapter(env.get("LLM_BASE_URL", ""), read_key(env), env.get("LLM_MODEL", ""))
    if name == "command":
        if not env.get("LLM_COMMAND"):
            raise PermanentError("set LLM_COMMAND to a command that reads a prompt on stdin and prints the reply")
        return CommandAdapter(env["LLM_COMMAND"], env.get("LLM_MODEL") or env.get("LLM_MODEL_NAME"))
    raise PermanentError("set LLM_BASE_URL (with LLM_API_KEY and LLM_MODEL) or LLM_COMMAND, or use --dry-run")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--grade", metavar="FOLDER", help="grade a recorded run next to the simulated replies")
    parser.add_argument("--use-solution", action="store_true", help="use solution/solution.py instead of exercise.py")
    parser.add_argument("--dry-run", action="store_true", help="fake adapter replaying the simulated replies: no key, no cost")
    parser.add_argument("--adapter", choices=["openai", "command"], help="default: openai if LLM_BASE_URL is set, else command")
    parser.add_argument("--out", help="output folder (default data/live_runs/<UTC time>)")
    parser.add_argument("--limit", type=int, help="ask only the first N questions")
    parser.add_argument("--versions", default="v1,v2", help="prompt versions, comma separated")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-output-tokens", type=int, default=300)
    parser.add_argument("--max-tokens", type=int, default=60000, help="token cap for the whole run")
    parser.add_argument("--max-cost", type=float, default=0.50, help="cost cap for the whole run, at the rate card's prices")
    args = parser.parse_args(argv)
    env = os.environ
    secrets = [read_key(env)]
    sub = load_submission(args.use_solution)
    if args.grade:
        grade(sub, args.grade, log=lambda t: print(scrub(t, secrets)))
        return 0
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = args.out or os.path.join(LIVE_ROOT, stamp)
    try:
        adapter = FakeAdapter(replay_simulated(sub)) if args.dry_run else \
            make_adapter(args.adapter or ("openai" if env.get("LLM_BASE_URL") else "command"), env)
        card = rate_card(env)
        check_config({"LLM_BASE_URL": env.get("LLM_BASE_URL"), "LLM_MODEL": env.get("LLM_MODEL"),
                      "LLM_COMMAND": env.get("LLM_COMMAND"), "--out": out}, secrets)
        data = sub.load()
        questions = data["eval_set"][:args.limit] if args.limit else data["eval_set"]
        versions = tuple(v.strip() for v in args.versions.split(",") if v.strip())
        template = {v: hashlib.sha256((sub.build_prompt("{question}", v, data["glossary"]) + "\n" + json_instructions())
                                      .encode("utf-8")).hexdigest()[:16] for v in versions}
        provenance = {
            "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "prompt_version": "build_prompt() %s from %s, plus structured output %s" % (
                " and ".join(versions), "solution/solution.py" if args.use_solution else "exercise.py", STRUCTURED_VERSION),
            "prompt_template_sha256": template,
            "questions_asked": len(questions),
            "how": "live_run.py: adapter call with retries and backoff, JSON schema check with one retry, "
                   "every SQL reply run only through run_guarded",
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "copperwren.db")
            sub.build_db(path, data)
            record_run(questions, adapter, out, lambda question, v: sub.build_prompt(question, v, data["glossary"]),
                       lambda sql: sub.run_guarded(path, sql), versions=versions,
                       budget=Budget(args.max_tokens, args.max_cost, card), temperature=args.temperature,
                       max_output_tokens=args.max_output_tokens, secrets=secrets, provenance=provenance,
                       log=lambda t: print(scrub(t, secrets)))
    except (SecretLeak, PermanentError, TransientError) as e:
        sys.exit("live_run.py stopped: %s" % scrub(e, secrets))
    print("grade it: python3 live_run.py%s --grade %s" % (" --use-solution" if args.use_solution else "", out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
