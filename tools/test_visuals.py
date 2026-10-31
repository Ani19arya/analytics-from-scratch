"""Checks for the offline teaching pages in visuals/.

    python3 -B -m unittest tools/test_visuals.py

1. Every page exists, is one self-contained file that makes no network calls, has a
   title, a lang attribute and a viewport meta, follows light and dark mode, and has no
   em dashes, en dashes or curly quotes.
2. Each page embeds its inputs and expected outputs in
   <script type="application/json" id="fixtures">. The embedded data must match the
   lesson's CSV files, and every expected value is recomputed here with separate Python
   code (no JavaScript is run). The pages run the same fixtures through their own
   JavaScript when they open and print the result as "Self check".

Standard library only, no network.
"""
import csv
import importlib.util
import json
import math
import os
import random
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIS = os.path.join(ROOT, "visuals")
PHASES = os.path.join(ROOT, "phases")
PAGES = {
    "join-fanout": "01-sql/02-joins-without-losing-rows",
    "window-functions": "01-sql/03-window-functions",
    "cohort-triangle": "01-sql/04-cohort-retention",
    "ab-test": "02-statistics-and-experiments/03-ab-test-from-scratch",
    "agent-loop": "06-ai-for-analysts/13-agent-loop-from-scratch",
}
BAD_CHARS = {chr(0x2014): "em dash", chr(0x2013): "en dash", chr(0x201C): "curly quote", chr(0x201D): "curly quote",
             chr(0x2018): "curly quote", chr(0x2019): "curly quote"}
NETWORK_JS = ["fetch(", "XMLHttpRequest", "WebSocket", "EventSource", "sendBeacon", "import(", "importScripts", "@import"]


def read(name):
    with open(os.path.join(VIS, name), encoding="utf-8") as f:
        return f.read()


def fixtures(page):
    m = re.search(r'<script type="application/json" id="fixtures">(.*?)</script>', read(page + ".html"), re.S)
    if not m:
        raise AssertionError(page + ": no fixtures block")
    return json.loads(m.group(1))


def csv_rows(lesson, name):
    with open(os.path.join(PHASES, lesson, "data", name), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self._in_title = tag == "title"

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


class TestPagesAreOffline(unittest.TestCase):
    def test_every_page(self):
        for name in list(PAGES) + ["index"]:
            path = os.path.join(VIS, name + ".html")
            with self.subTest(page=name):
                self.assertTrue(os.path.isfile(path), name + ".html is missing")
                text = read(name + ".html")
                p = Tags()
                p.feed(text)
                html = [a for t, a in p.tags if t == "html"]
                self.assertTrue(html and html[0].get("lang"), "no lang attribute on <html>")
                self.assertTrue(p.title.strip(), "no <title>")
                self.assertTrue(any(t == "meta" and a.get("name") == "viewport" and "width=device-width" in (a.get("content") or "")
                                    for t, a in p.tags), "no viewport meta")
                self.assertTrue("prefers-color-scheme: dark" in text, name + ".html has no dark mode")
                for word in ["http://", "https://", "//cdn"] + NETWORK_JS:
                    self.assertFalse(word in text, "%s.html contains %s: pages must not touch the network" % (name, word))
                for tag, attrs in p.tags:
                    if tag == "script":
                        self.assertNotIn("src", attrs, "external script")
                    if tag == "link":
                        self.fail("<link> tags load external files: put CSS inline")
                    for key in ("src", "href", "action", "srcset", "poster"):
                        target = attrs.get(key)
                        if target is None:
                            continue
                        self.assertNotRegex(target, r"^[a-zA-Z][a-zA-Z0-9+.-]*:", "%s %s=%s is not a relative path" % (tag, key, target))
                        local = target.split("#")[0]
                        if local:
                            resolved = os.path.normpath(os.path.join(VIS, local))
                            self.assertTrue(os.path.exists(resolved), "broken link " + target)
                for ch, label in BAD_CHARS.items():
                    self.assertFalse(ch in text, "%s.html contains an %s" % (name, label))

    def test_readme(self):
        text = read("README.md")
        for ch, label in BAD_CHARS.items():
            self.assertFalse(ch in text, "visuals/README.md contains an %s" % label)
        for name in PAGES:
            self.assertIn(name + ".html", text)

    def test_lessons_link_to_their_page(self):
        for name, lesson in PAGES.items():
            with open(os.path.join(PHASES, lesson, "README.md"), encoding="utf-8") as f:
                self.assertTrue("../../../visuals/%s.html" % name in f.read(), lesson + " README does not link its page")

    def test_core_functions_are_present(self):
        need = {
            "join-fanout": ["function runJoin(", "function predictRows(", "function selfCheck("],
            "window-functions": ["function computeWindow(", "function selfCheck("],
            "cohort-triangle": ["function buildModel(", "function triangle(", "function averages(", "function selfCheck("],
            "ab-test": ["function erf(", "function normalCdf(", "function twoProportionZtest(", "function diffCi(",
                        "function srmCheck(", "function MersenneTwister(", "function simulatePeeking(", "function selfCheck("],
            "agent-loop": ["function parseAction(", "function ungroundedNumbers(", "function runCost(", "function selfCheck("],
        }
        for page, funcs in need.items():
            text = read(page + ".html")
            for f in funcs:
                self.assertTrue(f in text, "%s.html has no %s" % (page, f))


class TestJoinFanout(unittest.TestCase):
    L = PAGES["join-fanout"]

    @classmethod
    def setUpClass(cls):
        cls.fx = fixtures("join-fanout")
        d = cls.fx["data"]
        cls.orders = [tuple(o) for o in d["orders"]]
        cls.addresses = [tuple(a) for a in d["addresses"]]

    def test_data_matches_lesson(self):
        d = self.fx["data"]
        self.assertEqual(d["customers"], [r["customer_id"] for r in csv_rows(self.L, "customers.csv")])
        self.assertEqual(self.orders, [(int(r["order_id"]), r["customer_id"], float(r["amount"])) for r in csv_rows(self.L, "orders.csv")])
        self.assertEqual(self.addresses, [(r["customer_id"], r["city"], int(r["is_primary"])) for r in csv_rows(self.L, "customer_addresses.csv")])

    def join(self, customers, keep, mode):
        orders = [o for o in self.orders if customers is None or o[1] in customers]
        addr = [a for a in self.addresses if (customers is None or a[0] in customers) and (a[2] == 1 or keep is None or a[0] in keep)]
        if mode == "all":
            rows = [o[2] for o in orders for a in addr if a[0] == o[1]]
        elif mode == "primary":
            rows = []
            for o in orders:
                n = sum(1 for a in addr if a[0] == o[1] and a[2] == 1)
                rows += [o[2]] * max(n, 1)
        elif mode == "preagg":
            spend = {}
            for o in orders:
                spend[o[1]] = spend.get(o[1], 0) + o[2]
            rows = []
            for c, s in spend.items():
                n = sum(1 for a in addr if a[0] == c and a[2] == 1)
                rows += [s] * max(n, 1)
        else:
            keys = {a[0] for a in addr}
            rows = [o[2] for o in orders if o[1] in keys]
        return len(rows), round(sum(rows), 2)

    def test_explorer_cases(self):
        self.assertEqual(len(self.fx["cases"]), 16)
        for c in self.fx["cases"]:
            n, s = self.join(set(self.fx["explorer"]["customers"]), set(c["second"]), c["mode"])
            self.assertEqual(n, c["rows"], c)
            self.assertAlmostEqual(s, c["sum"], places=2, msg=c)

    def test_full_data_matches_the_lesson_text(self):
        got = {c["mode"]: (c["rows"], c["sum"]) for c in self.fx["full"]}
        self.assertEqual(got["all"], (465, 38399.54))
        self.assertEqual(got["primary"], (360, 29551.86))
        for c in self.fx["full"]:
            n, s = self.join(None, None, c["mode"])
            self.assertEqual(n, c["rows"])
            self.assertAlmostEqual(s, c["sum"], places=2)
        self.assertEqual(self.fx["orders_total"], {"rows": 360, "sum": 29551.86})

    def test_spot_the_mistake(self):
        spot = self.fx["spot"]
        wrong = [c for c, s in spot["result"] if abs(s - dict(spot["true"])[c]) > 0.005]
        self.assertEqual(wrong, [spot["answer"]])
        for c, s in spot["result"]:
            n_addr = sum(1 for a in self.addresses if a[0] == c)
            self.assertAlmostEqual(s, round(n_addr * sum(o[2] for o in self.orders if o[1] == c), 2), places=2)


class TestWindowFunctions(unittest.TestCase):
    L = PAGES["window-functions"]

    @classmethod
    def setUpClass(cls):
        cls.fx = fixtures("window-functions")

    def test_data_matches_lesson(self):
        d = self.fx["data"]
        monthly = [[r["region"], r["month"], int(r["revenue"])] for r in csv_rows(self.L, "monthly_revenue.csv") if r["month"] <= "2026-01"]
        self.assertEqual(d["monthly"], monthly)
        self.assertEqual(d["reps"], [[r["rep"], r["region"], int(r["sales"])] for r in csv_rows(self.L, "rep_sales.csv")])

    def compute(self, c):
        if c["dataset"] == "monthly":
            rows = [{"region": r[0], "key": r[1], "v": r[2], "pos": i} for i, r in enumerate(self.fx["data"]["monthly"])]
        else:
            rows = [{"region": r[1], "key": r[0], "v": r[2], "pos": i} for i, r in enumerate(self.fx["data"]["reps"])]
        order = {"month": lambda r: (r["key"],), "revenue_desc": lambda r: (-r["v"],), "sales_desc": lambda r: (-r["v"],),
                 "sales_desc_rep": lambda r: (-r["v"], r["key"]), "none": lambda r: ()}[c["order"]]
        groups = {}
        for r in rows:
            groups.setdefault(r["region"] if c["partition"] == "region" else "", []).append(r)
        out = {}
        for part in groups.values():
            part.sort(key=lambda r: order(r) + (r["pos"],))
            for i, r in enumerate(part):
                peers = [j for j, q in enumerate(part) if order(q) == order(r)]  # RANGE: rows tied with r
                if c["fn"] == "sum":
                    if c["order"] == "none":
                        frame = part
                    elif c["frame"] == "range":
                        frame = part[:max(peers) + 1]
                    elif c["frame"] == "rows2":
                        frame = part[max(0, i - 2):i + 1]
                    else:
                        frame = part[:i + 1]
                    val = sum(q["v"] for q in frame)
                elif c["fn"] == "rank":
                    val = 1 + sum(1 for q in part if order(q) < order(r))
                elif c["fn"] == "row_number":
                    val = i + 1
                else:
                    val = part[i - 1]["v"] if i > 0 else None
                out[r["region"] + "|" + r["key"]] = val
        return out

    def test_every_case(self):
        self.assertGreaterEqual(len(self.fx["cases"]), 40)
        for c in self.fx["cases"]:
            self.assertEqual(self.compute(c), c["values"], {k: c[k] for k in c if k != "values"})

    def test_lesson_numbers(self):
        def case(**kw):
            return [c for c in self.fx["cases"] if all(c[k] == v for k, v in kw.items())][0]["values"]
        ytd = case(dataset="monthly", partition="region", order="month", frame="rows", fn="sum")
        self.assertEqual([ytd["North|2025-10"], ytd["North|2025-11"], ytd["North|2025-12"]], [36518, 70971, 111555])
        rng = case(dataset="reps", partition="region", order="sales_desc", frame="range", fn="sum")
        self.assertEqual([rng["North|R0%d" % i] for i in (4, 5, 2, 3, 1)], [120000, 120000, 230000, 230000, 280000])
        rank = case(dataset="reps", partition="region", order="sales_desc", fn="rank")
        self.assertEqual([rank["North|R0%d" % i] for i in (4, 5, 2, 3, 1)], [1, 1, 3, 3, 5])
        lag = case(dataset="monthly", partition="region", order="month", fn="lag")
        self.assertEqual((lag["North|2025-10"], lag["North|2025-11"]), (None, 36518))


class TestCohortTriangle(unittest.TestCase):
    L = PAGES["cohort-triangle"]

    @classmethod
    def setUpClass(cls):
        cls.fx = fixtures("cohort-triangle")

    def test_data_matches_lesson(self):
        d = self.fx["data"]
        self.assertEqual(d["users"], [[int(r["user_id"]), r["signup_date"]] for r in csv_rows(self.L, "users.csv")])
        self.assertEqual(d["events"], [[int(r["user_id"]), r["event_date"]] for r in csv_rows(self.L, "events.csv")])

    def model(self):
        def mi(d):
            return int(d[:4]) * 12 + int(d[5:7])
        signup = dict((u, d) for u, d in self.fx["data"]["users"])
        end = max(mi(d) for _, d in self.fx["data"]["events"])
        size, users_in, events_in = {}, {}, {}
        for u, d in signup.items():
            size[d[:7]] = size.get(d[:7], 0) + 1
        for u, d in self.fx["data"]["events"]:
            key = (signup[u][:7], mi(d) - mi(signup[u]))
            users_in.setdefault(key, set()).add(u)
            events_in[key] = events_in.get(key, 0) + 1
        return mi, end, size, users_in, events_in

    def values(self, count, denom, unobserved):
        mi, end, size, users_in, events_in = self.model()
        num = (lambda k: len(users_in.get(k, ()))) if count == "users" else (lambda k: events_in.get(k, 0))
        tri = {}
        for c in sorted(size):
            row = []
            for m in range(self.fx["max_month"] + 1):
                if m > end - mi(c + "-01"):
                    row.append(None if unobserved == "blank" else 0.0)
                    continue
                den = size[c] if denom == "size" or m == 0 else num((c, m - 1))
                row.append(100.0 * num((c, m)) / den)
            tri[c] = row
        return tri

    def test_every_case(self):
        self.assertEqual(len(self.fx["cases"]), 8)
        for case in self.fx["cases"]:
            tri = self.values(case["count"], case["denom"], case["unobserved"])
            shown = {c: [None if v is None else round(v, 1) for v in row] for c, row in tri.items()}
            self.assertEqual(shown, case["triangle"], case["count"] + case["denom"] + case["unobserved"])
            avgs = []
            for m in range(self.fx["max_month"] + 1):
                vals = [row[m] for row in tri.values() if row[m] is not None]
                avgs.append(round(sum(vals) / len(vals), 1) if vals else None)
            self.assertEqual(avgs, case["averages"])

    def test_lesson_numbers(self):
        right = [c for c in self.fx["cases"] if (c["count"], c["denom"], c["unobserved"]) == ("users", "size", "blank")][0]
        t = right["triangle"]
        self.assertEqual(t["2026-01"][1:4], [57.1, 35.7, 26.2])
        self.assertEqual(t["2026-04"][1:4], [60.0, 43.6, None])
        self.assertEqual(t["2026-06"][1], None)
        zero = [c for c in self.fx["cases"] if (c["count"], c["denom"], c["unobserved"]) == ("users", "size", "zero")][0]
        self.assertEqual((right["averages"][3], zero["averages"][3]), (24.2, 12.1))
        self.assertEqual(self.fx["sizes"], {"2026-01": 42, "2026-02": 52, "2026-03": 51, "2026-04": 55, "2026-05": 58, "2026-06": 40})

    def test_spot_the_mistake(self):
        right = [c for c in self.fx["cases"] if (c["count"], c["denom"], c["unobserved"]) == ("users", "size", "blank")][0]["triangle"]
        spot = self.fx["spot"]["triangle"]
        diffs = [[c, m] for c in right for m in range(len(right[c])) if right[c][m] != spot[c][m]]
        self.assertEqual(diffs, [self.fx["spot"]["answer"]])
        c, m = self.fx["spot"]["answer"]
        events = self.values("events", "size", "blank")
        self.assertEqual(spot[c][m], round(events[c][m], 1))


def phi(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


class TestAbTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = fixtures("ab-test")

    def test_normal_cdf(self):
        for z, want in self.fx["normal_cdf"]:
            self.assertAlmostEqual(round(phi(z), 4), want, places=9)

    def test_cases(self):
        self.assertGreaterEqual(len(self.fx["cases"]), 5)
        for c in self.fx["cases"]:
            ca, na, cb, nb = c["conv_a"], c["n_a"], c["conv_b"], c["n_b"]
            pa, pb = ca / na, cb / nb
            pool = (ca + cb) / (na + nb)
            se = math.sqrt(pool * (1 - pool) * (1 / na + 1 / nb))
            z = (pb - pa) / se if se else 0.0
            p = 2 * (1 - phi(abs(z))) if se else 1.0
            se_u = math.sqrt(pa * (1 - pa) / na + pb * (1 - pb) / nb)
            e = (na + nb) / 2
            chi2 = (na - e) ** 2 / e + (nb - e) ** 2 / e
            want = {"p_a": pa, "p_b": pb, "lift": pb - pa, "p_pool": pool, "se": se, "z": z, "p_value": p,
                    "ci_low": pb - pa - 1.96 * se_u, "ci_high": pb - pa + 1.96 * se_u,
                    "srm_chi2": chi2, "srm_p": math.erfc(math.sqrt(chi2 / 2))}
            for k, v in want.items():
                self.assertAlmostEqual(c[k], round(v, 4), places=9, msg="%s %s" % (k, c))
            self.assertEqual(c["decision"], "ship" if p < 0.05 and pb > pa else "do not ship")

    def test_lesson_numbers(self):
        c = self.fx["cases"][0]
        self.assertEqual((c["conv_a"], c["n_a"], c["conv_b"], c["n_b"]), (107, 976, 135, 924))
        self.assertEqual((c["z"], c["ci_low"], c["ci_high"], c["srm_chi2"], c["srm_p"]), (2.3835, 0.0064, 0.0665, 1.4232, 0.2329))
        self.assertAlmostEqual(c["p_value"], 0.0172)

    def test_rng_is_python_random(self):
        rng = random.Random(self.fx["rng"]["seed"])
        self.assertEqual([rng.random() for _ in self.fx["rng"]["first"]], self.fx["rng"]["first"])

    def simulate(self, sims, days, per_day, rate, alpha, seed):
        rng = random.Random(seed)
        any_day = last_day = 0
        for _ in range(sims):
            a = b = n = 0
            crossed = False
            p = 1.0
            for _ in range(days):
                n += per_day
                a += sum(1 for _ in range(per_day) if rng.random() < rate)
                b += sum(1 for _ in range(per_day) if rng.random() < rate)
                pool = (a + b) / (2 * n)
                if pool in (0.0, 1.0):
                    p = 1.0
                else:
                    z = (b / n - a / n) / math.sqrt(pool * (1 - pool) * (2 / n))
                    p = min(1.0, 2 * (1 - phi(abs(z))))
                crossed = crossed or p < alpha
            any_day += crossed
            last_day += p < alpha
        return any_day / sims, last_day / sims

    def test_peeking(self):
        for c in self.fx["peeking"]:
            got = self.simulate(c["sims"], c["days"], c["per_day"], c["rate"], c["alpha"], c["seed"])
            self.assertEqual(got, (c["any_day"], c["last_day"]))
            self.assertGreater(c["any_day"], c["last_day"])
        self.assertEqual(self.fx["lesson_peeking"], {"sims": 2000, "seed": 0, "any_day": 0.2185, "last_day": 0.0455})


class TestAgentLoop(unittest.TestCase):
    L = PAGES["agent-loop"]
    NUMBER = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?")

    @classmethod
    def setUpClass(cls):
        cls.fx = fixtures("agent-loop")

    def test_fixture_says_simulated(self):
        self.assertIn("simulated", self.fx["source"])
        self.assertIn("no model was called", self.fx["source"])

    def test_costs_kinds_and_grounding(self):
        card = self.fx["rate_card"]
        for run in self.fx["runs"]:
            m = run["messages"]
            calls = inp = out = 0
            for i, msg in enumerate(m):
                if msg["role"] == "assistant":
                    calls += 1
                    inp += sum(-(-len(p["content"]) // 4) for p in m[:i])
                    out += -(-len(msg["content"]) // 4)
            credits = inp / 1000 * card["input_per_1k"] + out / 1000 * card["output_per_1k"]
            self.assertEqual((calls, inp, out, round(credits, 2)),
                             (run["cost"]["calls"], run["cost"]["input_tokens"], run["cost"]["output_tokens"], run["cost"]["credits"]), run["id"])
            kinds = []
            for msg in m:
                if msg["role"] != "assistant":
                    continue
                try:
                    obj = json.loads(msg["content"])
                    kinds.append("final" if "final" in obj else "tool")
                except ValueError:
                    kinds.append("error")
            self.assertEqual(kinds, run["kinds"], run["id"])
            if run["answer"]:
                seen = [float(s.replace(",", "")) for t in [run["question"]] + [x["content"] for x in m if x["role"] == "tool"]
                        for s in self.NUMBER.findall(t)]
                bad = []
                for s in self.NUMBER.findall(run["answer"]):
                    plain = s.replace(",", "")
                    d = len(plain.split(".")[1]) if "." in plain else 0
                    if not any(round(v, d) == round(float(plain), d) for v in seen):
                        bad.append(s)
                self.assertEqual(bad, run["ungrounded"], run["id"])
                self.assertEqual(run["status"], "ungrounded" if bad else "answered")
        planted = [r["id"] for r in self.fx["runs"] if r["ungrounded"]]
        self.assertEqual(planted, ["Q08"])

    def test_runs_match_the_lesson_solution(self):
        lesson = os.path.join(PHASES, self.L)
        old = sys.dont_write_bytecode
        sys.dont_write_bytecode = True
        try:
            spec = importlib.util.spec_from_file_location("visuals_agent_solution", os.path.join(lesson, "solution", "solution.py"))
            sol = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sol)
        finally:
            sys.dont_write_bytecode = old
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "shop.db")
            sol.build_db(path, {"customers": sol.load_csv("customers.csv"), "orders": sol.load_csv("orders.csv")})
            tools = sol.make_tools(path)
            scripts = sol.scripts_by_question(sol.load_csv("agent_script.csv"))
            for run in self.fx["runs"]:
                got = sol.run_agent(run["question"], sol.ScriptedModel(scripts[run["id"]]), tools)
                self.assertEqual(got["messages"], run["messages"], run["id"])
                self.assertEqual(got["status"], run["status"], run["id"])


if __name__ == "__main__":
    unittest.main()
