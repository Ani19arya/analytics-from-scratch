# Repository audit (31 October 2026)

This is the starting point for the course rebuild: what the repository does well, what is wrong, what is missing, and the order in which to fix it. It was written after reading every lesson README, exercise, solution and test, running every README code block, and rebuilding every dataset.

The line-by-line findings live in three appendices:

- [docs/audit/2026-10-31-phases-01-03.md](docs/audit/2026-10-31-phases-01-03.md): SQL, statistics, metrics. 12 lessons, 52 defects with file, line and fix.
- [docs/audit/2026-10-31-phases-04-07.md](docs/audit/2026-10-31-phases-04-07.md): dashboards, Python, AI, getting hired, tools and the tutor skill. 15 lessons, 53 defects.
- [docs/audit/2026-10-31-skills-evidence.md](docs/audit/2026-10-31-skills-evidence.md): what employers ask for, from 9,044 live analyst postings (29 Oct 2026) and 20 cited external sources.

## 1. Where the course stands

| | |
|---|---|
| Lessons | 27, in 7 phases |
| Test contract | `python3 tools/run_all_tests.py --exercise`: 27 lessons, 0 problems. Every solution passes, every shipped exercise fails |
| Reproducibility | Every `make_data.py` rebuilds its CSVs byte for byte. Every README code block runs and prints the numbers the prose quotes (one exception, see below) |
| Style | No em or en dashes, no curly quotes, synthetic data labelled in every lesson |
| Runtime | Python 3.9+ standard library and `sqlite3`. Offline. No installs, no keys |

Average scores from the two lesson audits (1 to 5):

| Axis | Phases 01 to 03 | Phases 04 to 07 |
|---|---|---|
| Technical accuracy | 3.8 | 3.9 |
| Beginner friendliness | 3.4 | 3.7 |
| Exercise and test quality | 3.7 | 3.9 |
| Visual explanation | 1.6 | 1.6 |
| Business realism | 4.4 | 3.9 |

## 2. What is excellent and must be preserved

These are the course's signature. Every new lesson keeps them.

1. **Build it from scratch, then check it.** Each lesson rebuilds the method (GROUP BY as a loop with a dictionary, a z-test by hand, DAX filter context in SQL) and a test proves the answer.
2. **Tests compute the expected answer independently.** The expected numbers come from plain Python in the test, never from the solution file.
3. **Every lesson opens with a trap and a real wrong number.** The join fan-out that counts 465 rows instead of 360. The funnel that reads 14.7% by events and 40.3% by users. MAU of 170 against 85. The truncated axis that turns a 1.28x change into 4.36x. Interviews test exactly these.
4. **"What to tell the stakeholder" sentences.** A calculation becomes a decision, which is the job skill most courses skip.
5. **Honest limits sections and labelled fixtures.** The AI lessons say what a check cannot catch and say when outputs are simulated.
6. **Numbers in prose are computed, never typed.** Job-market numbers are dated and come from the public Real Analyst Jobs feed.
7. **Offline, free, MIT.** Anyone with Python can run every lesson.

## 3. What is wrong (fix before adding anything)

Learners copy sentences into real work, so wrong statements come first. These are the high-severity defects; every one has a file, line and fix in the appendices.

| Lesson | Defect |
|---|---|
| 03-01 Metric trees | The claim "if revenue did not change, every effect is 0" is false: with visitors +10% and conversion -9.1% the split is +228.7 and -228.7. The test only compares identical weeks, so it locks the bug in. Fix with the logarithmic mean (LMDI), which also removes the crash when a factor is 0 |
| 01-04 Cohort retention | The pivot query prints 0.0 for months that have not happened yet, the exact blank-is-not-zero mistake the lesson warns about |
| 02-02 Confidence interval | The stakeholder sentence describes the interval as being about the surveyed customers. It is about all customers |
| 03-03 Active users | The explanation of the DAU drop is contradicted by the lesson's own data |
| 02-03 A/B test | Check-yourself answer 4 says significance means the effect is "probably real", contradicting the correct answer 2 |
| 01-03 Window functions | Calls an October to September running total "year to date" |
| 04-02 DAX measures | Says CALCULATE adds a filter (a boolean filter replaces the filter on that column) and maps ALL(category) to a query that removes every filter |
| 06-02 Check LLM-written SQL | Ignores row order for ranked questions, fails a query for a column reorder, tests on one database only, and runs the model's SQL with no read-only guard |
| 06-01 Grade an LLM classifier | Simulated labels ignore the ticket text, and the pass/fail verdict on 72 to 75 rows carries no uncertainty |
| 07-01 Read job postings like data | The visa classifier marks "Sponsorship is not available" and "We do not offer sponsorship" as yes, the costliest error for a job seeker |
| 07-03 Portfolio project | "Churn" mixes trials that never converted with paid cancellations |
| 05-01 Clean a messy CSV | The money parser crashes on input such as "$," instead of rejecting it |
| All job-market sections | Quote US 2,848 and 2,102 postings for 25 Oct, while the committed snapshot for that day says 2,789 and 2,056 (it removes reposting sites) |

Structural problems:

- **Tests can be gamed.** SQL tests check one committed dataset, so a hard-coded `VALUES (...)` list passes. Fix: build a second dataset with another seed inside each test.
- **No navigation for three phases.** Phases 01, 02 and 06 have no README.
- **The tutor skill misroutes.** It sends a learner who knows SQL and statistics straight to the AI phase, which assumes Python. It also forbids opening `solution/`, which some READMEs tell the learner to import.
- **Tooling gaps.** `run_all_tests.py` does not lint style, run README code blocks or check that data rebuilds identically. There is no CI. `.gitignore` misses `reports/`.

## 4. What is missing

| Area | Gap | Evidence it matters |
|---|---|---|
| Absolute beginner on-ramp | No first SQL query (SELECT, WHERE, ORDER BY), no NULL/CASE, no Python first steps, no "how to run things" page. A true beginner cannot start | The course promises "from scratch" |
| Visual explanation | Almost no diagrams: joins, windows, star schema, filter context, cohort triangles, distributions, NL-to-SQL checks, RAG and agent flows are all text only | Visuals average 1.6 out of 5 |
| Spreadsheets | No lookups, pivots or Power Query | Excel appears in 40.7% of tagged postings and 58.5% of entry-level ones |
| Statistics depth | No probability or distributions, no sampling or CLT, no permutation test, chi-square, correlation vs causation, regression or bootstrap | Statistics and experiments are core for product and growth roles |
| Metrics depth | No metric specification, growth accounting, retention curves, mix effects, diagnosing a drop, attribution or unit economics | Product analyst postings name SQL in 84.6% and Looker in 27.2% |
| Python depth | No EDA, APIs and JSON, data quality tests, joins in Python, more chart types, or a bridge to pandas | Python appears in 48.4% of tagged postings, already 47.2% at entry level |
| BI modelling | No role-playing dates, slowly changing dimensions, semantic layer, row-level security or table calculations | Any BI tool 46.8%; Power BI 59.6% of BI analyst postings |
| Modern data stack | No warehouse layers, dbt-style models, orchestration, git | Snowflake rises from 8.7% (entry) to 20.3% (senior); dbt from 2.8% to 11.0% |
| Generative AI | Three lessons only. Missing: how LLMs work for analysts, prompt versions as experiments, structured output, eval-set size, human-in-the-loop thresholds, LLM as judge, safe NL-to-SQL, PII handling, RAG, auditing agents, MCP | 45% of data and analytics postings mention AI (Indeed Hiring Lab, Dec 2025); 71% of analytics engineers fear hallucinated output reaching stakeholders (dbt Labs 2026) |
| Business case studies | No industry modules (e-commerce, SaaS, fintech, marketplace, marketing, supply chain, operations) | Business realism is the course's strength; it should cover the industries analysts work in |
| Capstones | One portfolio lesson. No end-to-end projects with rubrics | Portfolios are how entry-level candidates show skill |
| Career | Interview prep is SQL only. No statistics or case rounds, take-home, role roadmaps or honest resume bullets | Roles differ: BA postings ask for Python in only 27.0%, data analyst postings in 66.2% |

## 5. What is outdated

Little, because the course is a week old. Two framing updates:

- **Hand-typing routine SQL and charts is becoming less of a differentiator** as assistants draft them (dbt Labs 2026: 72% prioritise AI-assisted coding). SQL stays essential (69.9% of postings), so the course keeps teaching it in full. What changes is the emphasis: every SQL and BI module should also teach *reviewing* a query or dashboard someone (or something) else wrote.
- **AI lessons must use the current vocabulary**: structured outputs and tool use, MCP and semantic layers, alongside the evaluation methods the course already teaches.

## 6. Decisions for the rebuild

1. **Keep the lesson contract.** Every new lesson has a business problem, seeded synthetic data, an exercise that fails, a solution that passes, and an independent test. Topics that cannot run offline use one of four honest patterns: rebuild the logic in SQL or Python; check a CSV the learner exports from the tool; test against recorded model outputs labelled with model, date and prompt; or a guide page marked as untested.
2. **Keep every existing lesson path.** They are live URLs on GitHub and on realanalystjobs.com/learn. New lessons are appended within a phase and new phases are added; the learning order lives in `curriculum.json` and [LEARNING_ROADMAP.md](LEARNING_ROADMAP.md), not in folder numbers.
3. **New phases**: 00 Start here, 08 Modern data stack, 09 Business case studies, 10 Capstone projects.
4. **Diagrams are Mermaid in the README** (GitHub renders them, they are diffable text) or committed SVG drawn by the lesson's own code.
5. **Depth before volume.** Fix accuracy, then the on-ramp, then fill gaps in learning order. No placeholder lessons: a lesson is listed as planned in `curriculum.json` until it exists and passes.

## 7. Prioritised roadmap

| Wave | Work | Done when |
|---|---|---|
| 1. Correctness | Fix every high-severity defect above; re-run each test on a second seeded dataset; align job-market numbers with the snapshot | All 27 lessons pass the stronger tests and the defect table is empty |
| 2. Foundation | New README as a learning homepage, `LEARNING_ROADMAP.md`, `2026-2027-ANALYTICS-SKILLS.md`, `CONTRIBUTING.md`, `curriculum.json`, missing phase READMEs, linting and CI in `tools/` | A beginner can find where to start and a contributor knows the rules |
| 3. On-ramp | Phase 00: how to use this course, analytical thinking, first SQL query, NULL/CASE, Python first steps | A complete beginner can reach lesson 01-01 unaided |
| 4. Visuals | Mermaid diagrams for every concept listed in the appendices | Visual scores reach 4 out of 5 |
| 5. Core depth | SQL, statistics, metrics, Python and spreadsheet lessons from the gap list, in learning order | Each phase covers beginner to advanced |
| 6. BI and data stack | BI modelling lessons; phase 08 (warehouse layers, dbt from scratch, orchestration, data quality, git) | |
| 7. AI era | Phase 06 expansion: structured output, eval sizing, human in the loop, LLM as judge, safe NL-to-SQL, PII, RAG, agent audit, MCP | |
| 8. Business and projects | Phase 09 industry case studies, phase 10 capstones with rubrics, phase 07 interview rounds and role roadmaps | |
| 9. Quality | Full re-audit, link check, style lint, test run; refresh job-market evidence monthly | |

## 8. Progress

| Date | Wave | Result |
|---|---|---|
| 31 Oct 2026 | 1. Correctness | Every high-severity defect in section 3 is fixed, plus the medium and low items in the appendices. All 27 original lessons now test a second seeded dataset and hand-made edge cases. Job-market numbers now come from the 25 Oct data drop |
| 31 Oct 2026 | 2. Foundation | README, roadmap, skills evidence, contributing guide, lesson template v2, curriculum.json, lint, docs builder and CI are in place |
| 31 Oct 2026 | 3. On-ramp | Phase 00 is live: six Level 1 lessons and `tools/query.py` |
| 31 Oct 2026 | 4. Visuals | Every live lesson has at least one diagram (Mermaid or an SVG its own code draws) |
| 31 Oct 2026 | 5. Core depth | 22 more Level 1 lessons live (01-05 to 01-07, 02-05 to 02-07, 03-05, 03-06, 04-05 to 04-07, 05-05, 05-06, 06-04, 06-05, 06-11, 07-05 to 07-07, 07-11, 07-12, 08-06): Level 1 is complete |
| 31 Oct 2026 | 6. Level 2 | All 47 intermediate lessons live across SQL, statistics, metrics, dashboards, Python, AI, interviews, the modern data stack and nine business case studies. Each solution passes on Python 3.9 and 3.13, each exercise fails as shipped, and each dataset rebuilds byte for byte |

State after these waves: 102 live lessons, 19 planned (all Level 3: the advanced lessons and the capstones). `python3 tools/run_all_tests.py --exercise` reports 0 problems and `python3 tools/lint.py --strict` reports 0 errors and 0 warnings. Next: wave 7, Level 3, in the order of LEARNING_ROADMAP.md.
