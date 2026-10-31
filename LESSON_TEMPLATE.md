# Lesson format, version 2 (every lesson follows this)

Version 2 (31 Oct 2026) keeps everything from version 1 and adds what the [repository audit](REPOSITORY_AUDIT.md) found missing: a plain-words opening, a diagram where the concept has a shape, common mistakes, levels, and tests that cannot be passed by pasting the answer.

## Folder and files

Folder: `phases/<NN-phase>/<NN-lesson-slug>/`, listed in [curriculum.json](curriculum.json) with `"status": "live"`.

| File | Rule |
|---|---|
| `README.md` | The lesson, in the section order below |
| `make_data.py` | Builds the dataset deterministically. Stdlib only. Exposes `build(seed)` returning the rows, and writes `data/*.csv` for the default seed when run directly |
| `data/*.csv` | Under 2,000 rows each. Synthetic and labelled as synthetic, unless a public-domain or CC0 source is cited with a URL |
| `exercise.sql` or `exercise.py` | The starter. It must FAIL the test as shipped |
| `solution/solution.sql` or `solution/solution.py` | The worked answer |
| `test_lesson.py` | Stdlib `unittest` only. Checks the learner's file by default, the solution with `CHECK_SOLUTION=1` |
| `diagram.svg` and `draw_*.py` (optional) | A diagram the lesson's own stdlib code draws. Commit both the script and the SVG it writes, and embed the SVG in the README |

## The test

1. **Expected answers are computed independently** in plain Python inside the test, never read from the solution file.
2. **Two datasets.** The test runs the learner's code on the committed data AND on a second dataset from `make_data.build(seed=<other>)` built in memory. A hard-coded list of answers passes the first and fails the second.
3. **Small hand-made cases** for every function: the empty input, the tie, the NULL, the zero.
4. **Helpful failures.** A failing assertion says what was expected and what to look at, in one sentence.
5. Must pass on the solution and fail on the shipped exercise. `python3 tools/run_all_tests.py --exercise` checks both.

## Lesson kinds

Set `kind` in curriculum.json.

| Kind | Use when | How it is checked |
|---|---|---|
| `tested` | The logic can run in Python or SQLite | The test above |
| `tested` with a recorded fixture | The lesson is about an AI model's output | Test against recorded outputs in `data/`, with provenance in `data/fixture.json` (model, date, prompt and temperature), or clearly labelled as simulated (model "none"). An optional `live_run.py` may re-record with the learner's own key and is never used by the test |
| `tested` with an export check | The skill lives in a GUI (Excel, Power BI, Tableau) | Rebuild the logic in code and test it. An optional task asks the learner to do it in the tool and export a CSV, which the test checks if present and skips if not |
| `guide` | Nothing computational to check (behavioural interviews, wiring a client) | No test. Marked "Guide, no test" everywhere. Still has Check yourself questions |

Optional tools (pandas, git, a time zone database) are tested with `unittest.skipUnless`, so the course still runs with nothing installed.

## README sections, in this order

1. `# <Lesson title>`, then one line: the business question.
2. `## Before you start`: level (1, 2 or 3), time, and the lessons it builds on, as relative links.
3. `## The problem`: a named fictional company, a stakeholder, a deadline. 3 to 6 sentences. Check that the company name is not a real company in that industry.
4. `## In plain words`: the idea with an everyday analogy (shopping, cricket, food delivery, a bank statement) before any jargon. Every technical term is defined the first time it appears.
5. `## What you will build from scratch`: a short bullet list.
6. `## The idea`: the concept from first principles, with the math or SQL logic written out. Include a diagram when the concept has a shape (joins, windows, schemas, pipelines, distributions, agent flows). Use a Mermaid block or an SVG the lesson's code draws. No decorative diagrams.
7. `## Walk through`: step by step, small code blocks, each explained line by line, each followed by the output it prints. Every block must run.
8. `## Common mistakes`: the trap that gives a plausible wrong number, shown failing on the lesson's data, plus two or three more.
9. `## Your turn`: what to fill in, the run command `python3 test_lesson.py`, and an optional stretch task.
10. `## Check yourself`: 2 to 4 questions an interviewer might ask, answers in a `<details>` block.
11. `## What to tell the stakeholder`: the one or two sentences you would send, with the number and the caveat.
12. `## In real job postings`: one or two sentences with a dated number from the data drop in [data/job-market](data/job-market), and a link to a matching page on https://realanalystjobs.com.
13. `## Next`: link to the next lesson.

## Style (checked by `tools/lint.py`)

- No em dashes or en dashes. No curly quotes. Plain, direct sentences.
- No invented statistics about the world. Numbers in prose come from the lesson's own data, from the dated job-market data drop, or from a cited source with a link and the date it was read.
- No placeholders: no "TODO", "coming soon" or empty sections in a live lesson README. (TODOs belong in `exercise.*` only.)
- SQLite-only syntax gets a one-line note on how other databases write it.
