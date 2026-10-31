# Cloud task: finish Level 2 of Analytics from Scratch

Branch: `wave6-level2`. Read this whole file first. Work only on this branch, commit in logical units, push to `wave6-level2`. Do NOT merge to main and do NOT open a pull request unless the owner asks; the owner reviews the branch.

Delete this file in your final commit.

## State when this branch was pushed (31 Oct 2026)

- 33 lessons are live in curriculum.json (all checks green on main).
- 22 Level 1 lessons are WRITTEN and individually verified (solution passes, exercise fails, data rebuilds byte for byte, README outputs real) but still `"status": "planned"` in curriculum.json: 01-05, 01-06, 01-07, 02-05, 02-06, 02-07, 03-05, 03-06, 04-05, 04-06, 04-07, 05-05, 05-06, 06-04, 06-05, 06-11, 07-05, 07-06, 07-07, 07-11 (guide), 07-12, 08-06.
- Some Level 2 folders exist from agents that were STOPPED mid-work. Treat every Level 2 folder as an unverified draft: finish what is missing, then verify it fully. Folders and what they had when stopped:
  - looked complete but unverified: 01-08, 01-09, 02-08, 03-07, 03-08, 04-08, 05-07, 06-06, 08-01, 09-04
  - partial (no README or missing files): 02-09, 03-09, 03-10, 03-11, 03-12, 04-09, 05-08, 06-07, 06-08, 06-09, 06-10, 06-12, 08-02, 09-05
- Not started: 01-10, 01-11, 01-12, 02-10, 02-11, 02-12, 04-10, 04-11, 04-12, 05-09, 05-10, 07-08, 07-09, 07-10, 08-03, 08-05, 09-01, 09-02, 09-03, 09-06, 09-07, 09-08, 09-09.

## Step 1: integrate Level 1 (do this first, commit, push)

1. Set the 22 Level 1 lessons above to `"status": "live"` in curriculum.json.
2. `python3 tools/build_docs.py`, then update each hand-written `phases/*/README.md` lesson list so the new lessons appear and nothing says planned for a live lesson. 02-02's Before you start still calls 02-05 and 02-07 planned: fix it.
3. Add `my_region_totals.csv` to .gitignore (learner export from 04-05).
4. 07-12 ships sample projects with deliberately fake API keys (`data/projects/churn-leaked-key/.env`, an `API_KEY = "demo..."` line). Make sure they cannot look like a real provider key format, so GitHub secret scanning does not block the push.
5. Run the full checks below. Fix anything red. Commit "Wave 5: 22 Level 1 lessons live" and push.

## Step 2: write all 47 Level 2 lessons

Every lesson in curriculum.json with `"level": "intermediate"` that is not live. Use the exact id, path, title, question and kind from curriculum.json. Use subagents in parallel if you have them (one per phase group is a good split: SQL 01-08..12; stats 02-08..12; metrics 03-07..12; BI 04-08..12; Python 05-07..10 plus interviews 07-08..10; AI 06-06..10 and 06-12; stack 08-01, 08-02, 08-03, 08-05; cases 09-01..09). Mark each lesson live only after it passes every check. Commit and push after each phase group so progress is never lost.

Lesson-specific notes:
- 01-08 duplicates: ROW_NUMBER over a business key, near-duplicates (case, whitespace, email aliases), reconcile to a source total. 01-09: ROWS vs RANGE over a date spine with missing days. 01-10: 30-minute timeout with LAG and running SUM, boundary at exactly 30:00. 01-11: date minus ROW_NUMBER, duplicate same-day logs. 01-12: a teammate or assistant query with planted bugs (fan-out join, WHERE on a LEFT JOIN right table, integer division, wrong date bound); learner writes the fix AND findings checked by bug code.
- 02-08 permutation test with the +1 correction, exact enumeration on a tiny set. 02-09 chi-square in stdlib (regularized gamma), Cramer's V, expected count under 5 warning, trap of running on percentages. 02-10 Pearson r by hand, Simpson reversal by tenure. 02-11 OLS by formula, R squared, slope SE, statistics.linear_regression behind skipUnless(3.10+). 02-12 percentile bootstrap for a median and a ratio of sums, resample the right unit.
- 03-07 growth accounting and quick ratio. 03-08 classic vs unbounded retention, right-censoring. 03-09 rate vs mix decomposition summing exactly. 03-10 diagnose a 20% DAU drop with a planted tracking bug on one app version. 03-11 first, last, linear, time-decay attribution; credits sum to conversions. 03-12 margin LTV by cohort, CAC, payback.
- 04-08 role-playing dates (USERELATIONSHIP) and a bridge table. 04-09 a metric registry compiled to SQL. 04-10 SCD Type 1 vs 2 and point-in-time joins. 04-11 row-level security mapping table; unmapped user sees nothing. 04-12 Tableau table calcs vs FIXED/INCLUDE LOD and filter order. Cite Microsoft Learn or Tableau Help with URL and date read for any tool behaviour.
- 05-07 offline recorded paginated JSON, retry with a fake clock (no network in tests). 05-08 stdlib SVG histogram, scatter, line; bins and truncated axes. 05-09 data quality tests as code catching a planted broken load. 05-10 stdlib functions mapped to pandas, pandas tests behind skipUnless.
- 06-06 schema-validate model JSON, repair or reject, load to sqlite. 06-07 Wilson interval width vs n, paired comparison. 06-08 threshold for 95% precision chosen on validation, reported on held-out. 06-09 judge vs human: kappa, position and length bias. 06-10 read-only guard (single SELECT, allowlist, LIMIT, block PRAGMA/ATTACH, sqlite uri mode=ro). 06-12 stdlib BM25 or TF-IDF over a glossary with a deprecated definition, recall@k, citation check. Recorded or simulated fixtures with data/fixture.json provenance.
- 07-08 metrics case interview with a planted cause. 07-09 stats round (power, p-values, Simpson). 07-10 take-home grader with one strong and two weak submissions.
- 08-01 raw, staging, marts in sqlite. 08-02 a tiny dbt: ref() parsing, DAG, topological sort with cycle detection, schema tests. 08-03 incremental with lookback, late rows, backfill equals full rebuild. 08-05 bytes-scanned cost model with partitions and clustering; fictional price clearly labelled unless cited.
- 09-01..09 case studies: README keeps the 13 template sections AND uses the 12 case steps from phases/09-business-case-studies/README.md as ### subheadings inside The idea / Walk through; add RUBRIC.md for steps 10 to 12; test checks steps 7 to 9 numbers on two seeds; each case a different fictional company.

## Step 3: finish

- `python3 tools/build_docs.py`, update phase READMEs, update REPOSITORY_AUDIT.md section 8 Progress with a dated row, update LEARNING_ROADMAP.md if anything there says Level 2 is planned.
- Full checks green, delete this file, commit, push. Final message: what is live, anything you could not finish and why.

## Full checks (run from the repo root before every push)

```
python3 tools/run_all_tests.py --exercise
python3 tools/lint.py --strict
python3 tools/build_docs.py --check
for f in phases/*/*/make_data.py; do (cd "$(dirname "$f")" && python3 make_data.py > /dev/null); done; git status --short
```

All must pass (the last prints nothing besides your intended changes). CI runs the same on Python 3.9 and 3.12, so no 3.10+ syntax.

## Lesson brief (applies to every lesson)

Repo: this repository (public GitHub course, MIT).

## Read first (all short)
- LESSON_TEMPLATE.md (the contract, version 2: files, the two-dataset test, the 13 README sections in order, lesson kinds, style)
- CONTRIBUTING.md
- curriculum.json: find your lessons by id. Use the exact `path`, `title`, `question`, `kind`, `hours`, `level` from there.
- Two or three LIVE lessons in the same phase as yours (and phases/00-start-here for tone). Match their structure, voice, test style and README depth closely. Look at how they do `build(seed)`, the CHECK_SOLUTION switch, the second-seed test, and the "In real job postings" section.
- data/job-market/README.md and data/job-market/2026-10/ for the only job-market numbers you may quote.
- REPOSITORY_AUDIT.md section 3 and appendices, so you do not reintroduce a defect class it fixed (wrong stats formulas, NULL handling, tests that pass on hard-coded answers, invented facts).

## Hard rules
- Python 3.9+ standard library and sqlite3 only. Offline. No pip, no network, no API keys. Optional tools (git, pandas) only behind `unittest.skipUnless`.
- Every lesson: README.md, make_data.py exposing build(seed) and writing data/*.csv for the default seed when run directly, data/*.csv (<2,000 rows, labelled synthetic), exercise.(sql|py) that FAILS the test as shipped (TODOs only here), solution/solution.(sql|py), test_lesson.py (unittest; checks the learner file by default, the solution with CHECK_SOLUTION=1; expected answers computed independently inside the test; second dataset from build(other_seed) in memory; small hand-made edge cases: empty, tie, NULL, zero; one-sentence helpful failure messages).
- Kind `guide` lessons: README only, no test, still have Check yourself.
- README: exactly the 13 sections from LESSON_TEMPLATE.md in that order. Plain words first, define every term the first time. Every code block in Walk through must actually run and the printed output shown must be the real output (run it and paste). Include a Mermaid diagram where the concept has a shape (no decorative diagrams).
- Style: NO em dashes, NO en dashes, NO curly quotes anywhere (use plain hyphen, comma, colon). Short direct sentences.
- No invented real-world statistics. Numbers come from the lesson's own synthetic data, from data/job-market (say the date of the drop), or from a cited source with URL and date read. No real model prices unless cited with URL and date read; prefer a fictional rate card clearly labelled as an example. AI-output lessons use recorded fixtures with data/fixture.json provenance, or label them simulated (model "none").
- Fictional companies only; check the name is not a real company in that industry. You may reuse the course's existing fictional companies where it fits (Tiffinbell from phase 00, and others you see in live lessons).
- "In real job postings": one or two sentences with a dated number from data/job-market and a link to a matching realanalystjobs.com page that already exists (check the URL pattern other live lessons use; do not invent new paths).
- "Before you start" links to prerequisite lessons with relative links. "Next" links to the next lesson in curriculum.json order IF it is live or in this wave (all wave-5 lessons are listed below); otherwise link to the phase README (`../README.md`). Only link to folders that exist or will exist in this wave.
- Data must rebuild byte for byte: running make_data.py twice gives identical files.

## Do not touch
tools/ and .github/ unless a check is genuinely broken (say so in a commit message).

## Verify before you finish (for each of your lessons)
```
cd <lesson> && python3 make_data.py && CHECK_SOLUTION=1 python3 test_lesson.py   # must pass
cd <lesson> && python3 test_lesson.py                                             # must FAIL
cd <lesson> && python3 make_data.py && git status --short .                        # no diff after second rebuild (new files are untracked, so compare checksums instead: shasum data/* before and after)
python3 tools/lint.py   # from repo root; ignore only "folder exists but curriculum.json says planned" for YOUR folders and anything in other agents' folders. Everything else in your folders must be clean.
```
Also run on Python 3.9 semantics: no `match`, no `X | Y` type hints, no `str.removeprefix`, no zip(strict=).

## Level 2 and what already exists
Level 2 means: solve realistic problems independently. Compared with Level 1, the problem is messier, the exercise gives less scaffolding (fewer TODO hints, more to decide), and Common mistakes covers the subtle traps an experienced analyst still falls into. Keep the plain-words opening and define every new term; a Level 1 graduate must be able to follow.
All 39 Level 1 lessons now exist on disk (some are not yet marked live in curriculum.json, but their folders exist, so you may link to them). Treat any lesson folder that exists under phases/ as linkable. For "Next", link to the next lesson in curriculum.json order if its folder exists or it is in this wave (wave 6 = every intermediate lesson); otherwise ../README.md.
Keep temp files outside the repo (for example /tmp/w6-<label>/).
Optional-tool rule still holds: dbt, pandas, git, Tableau or Power BI are never required; rebuild the logic in stdlib and put any real-tool check behind unittest.skipUnless.

