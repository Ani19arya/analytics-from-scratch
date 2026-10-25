# Lesson format (every lesson follows this exactly)

Folder: `phases/<NN-phase>/<NN-lesson-slug>/`

Files:
- `README.md`: the lesson.
- `make_data.py`: builds the lesson's dataset into `data/` deterministically (`random.seed(...)`). Stdlib only. Run it and commit the CSVs it writes.
- `data/*.csv`: small (under 2,000 rows each). Synthetic and labelled as synthetic in the README, unless it is a public-domain or CC0 source cited with a URL.
- `exercise.sql` or `exercise.py`: the starter the learner fills in. It must FAIL the test as shipped (TODOs, `raise NotImplementedError`, or an empty query).
- `solution/solution.sql` or `solution/solution.py`: the worked answer.
- `test_lesson.py`: stdlib `unittest` only (plus `sqlite3`, `csv`, `math`, `statistics`, `random`). It checks the learner's file by default; with env `CHECK_SOLUTION=1` it checks the solution file instead. It must pass on the solution and fail on the exercise.

Runtime: Python 3.9+, standard library only. No pip installs, no network, no API keys. SQL lessons run on Python's built-in `sqlite3`.

README.md sections, in this order:
1. `# <Lesson title>`, then one line: the business question.
2. `## The problem`: a realistic analyst scenario (a named fictional company, a stakeholder, a deadline). 3 to 6 sentences.
3. `## What you will build from scratch`: bullet list.
4. `## The idea`: the concept explained from first principles, with the math or the SQL logic written out. No framework does the thinking for you.
5. `## Walk through`: step by step, with small code blocks.
6. `## Your turn`: what to fill in, and the run command: `python3 test_lesson.py` (from the lesson folder).
7. `## Check yourself`: 2 to 4 short questions an interviewer might ask on this topic, answers hidden in a `<details>` block.
8. `## In real job postings`: one or two sentences with a dated, real number from the Real Analyst Jobs live feed (given to you in the task), and a link to the matching page on https://realanalystjobs.com (only URLs given to you in the task).
9. `## Next`: link to the next lesson in the phase (relative path), or the next phase.

Style rules (checked in review):
- No em dashes or en dashes anywhere. No curly quotes. Plain, direct sentences.
- No invented statistics about the world. Numbers in prose are either from the lesson's own data or the dated job-feed numbers provided.
- Every code block must actually run.
