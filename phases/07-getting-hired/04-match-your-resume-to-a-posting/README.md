# Match your resume to a posting

Business question: of five open roles, which ones fit this resume best, and which missing skills stand between the candidate and the rest?

## The problem

Maya is a junior analyst in Pune with one internship and one project. She has five postings open in browser tabs and time to write two strong applications this week. She wants to know which two match her best and, for the others, what is missing. You will build a matcher from scratch: split text into tokens, map the many spellings of a skill to one name, weight the required skills above the nice to haves, and rank the five postings with the matched and missing skills next to each score.

The files `data/resume.txt` and `data/postings.csv` are synthetic, written by `make_data.py`. Maya, her internship and all five companies are invented.

## What you will build from scratch

- `tokenize`: lower case word tokens that keep `a/b` and `r&d` whole.
- `extract_skills`: canonical skill names from text, through a synonym table.
- `score`: a weighted match score with matched and missing lists.
- `rank`: the five postings, best first.

## The idea

**Tokens, not substrings.** Searching for `"r"` inside the text finds it in nearly every word. Split the text into tokens first, then compare whole tokens. The pattern `[a-z0-9]+(?:[/+#&][a-z0-9]+)*` keeps `a/b` and `r&d` as single tokens, so "R&D" never looks like the R language, and "Reporting" is the token `reporting`, not `r`.

**Normalize synonyms.** People write PowerBI, Power BI and Power-BI. They write PostgreSQL when the posting says SQL, and pandas when it says Python. A synonym table maps every form to one canonical name. Multi word forms are matched as runs of tokens: join the tokens with spaces, pad both ends, and look for `" power bi "`. "Power-BI" tokenizes to `power bi`, so it matches without its own entry.

**Weight what the posting needs.** Missing a required skill hurts more than missing a nice to have. With required skills R and nice to haves N, and your skills S:

    score = 100 * (2 * |R and S| + 1 * |N and S|) / (2 * |R| + |N|)

The weight 2 is a choice, not a law. What matters is that it is above 1 and that you use the same weights for every posting so the scores compare.

**Report the gaps, not just the score.** A score of 60 says little. "Missing: Tableau" tells Maya what to learn or what to explain in a cover letter.

## Walk through

Run these from the lesson folder.

Step 1. Tokens.

```python
import sys
sys.path.insert(0, "solution")
import solution as s

print(s.tokenize("Power-BI, A/B tests and our R&D team. Reporting to the CFO."))
print(sorted(s.extract_skills("Power-BI, A/B tests and our R&D team. Reporting to the CFO.")))
```

The tokens are `power`, `bi`, `a/b`, `tests`, ..., `r&d`, ..., `reporting`. The skills are `a/b testing` and `power bi`. No R.

Step 2. What the synonym table is worth.

```python
import sys
sys.path.insert(0, "solution")
import solution as s

resume, postings = s.load()
print("with synonyms:", sorted(s.extract_skills(resume)))
s.SYNONYMS = {k: [k] for k in s.SYNONYMS}
print("exact names only:", sorted(s.extract_skills(resume)))
for pid, r in s.rank(resume, postings):
    print(pid, r["score"])
```

With synonyms, Maya's resume has 7 skills. With exact names only it has 4: PowerBI, A/B tests and GA4 are lost. The marketing role at Elmstead Media (P4) falls from 100.0 to 42.9, though it asks for exactly what she has.

Step 3. Rank.

```python
import sys
sys.path.insert(0, "solution")
import solution as s

s.main()
```

| posting | role | score | missing required | missing nice to have |
|---|---|---|---|---|
| P1 | Data Analyst, Brightmoor Retail | 100.0 | none | none |
| P4 | Marketing Analyst, Elmstead Media | 100.0 | none | none |
| P2 | Product Analyst, Calloway Health | 60.0 | tableau | dbt, looker |
| P3 | Risk Analyst, Darnell Bank | 60.0 | sas | machine learning, r |
| P5 | Senior Data Analyst, Fairhaven Logistics | 50.0 | dbt, looker, snowflake | none |

What to tell Maya: apply to P1 and P4 this week. P2 needs Tableau; she knows Power BI, which is close, so a sentence in the cover letter and a small Tableau dashboard would answer it. P5 is a senior role and misses three required tools, so it is the weakest fit.

**Why this is a starting point and not the whole story.** Keyword matching sees words, not meaning. It cannot tell "used Tableau once" from "built and owned the Tableau reporting layer". It ignores level: P5 is senior and the score does not know. It only knows the synonyms you gave it, so a skill written a new way is a miss. And a person reads the resume after any screen. Use the missing list to decide what to learn and which true experience to describe in the posting's own words. Do not paste in skills you do not have: an interviewer will ask about them.

## Your turn

Open `exercise.py` and fill in `tokenize`, `extract_skills`, `score` and `rank`. Then run, from this folder:

```
python3 test_lesson.py
```

To see the reference solution pass: `CHECK_SOLUTION=1 python3 test_lesson.py`.

Then put your own resume in `data/resume.txt` and paste five real postings into `data/postings.csv`, each with a `What you need:` and a `Nice to have:` part. Add the synonyms your field uses. To compare with a ready-made tool, try the [resume job matcher](https://realanalystjobs.com/tools/resume-job-matcher), and use the [analyst skills checklist](https://realanalystjobs.com/tools/analyst-skills-checklist) to plan what to learn.

## Check yourself

1. Why tokenize before matching instead of searching for substrings?
2. A posting says "PowerBI" and your resume says "Power BI". What makes them match here?
3. Why weight required skills above nice to haves?
4. Your score is 100 for a role. Does that mean you should get an interview?

<details>
<summary>Answers</summary>

1. Substrings match inside other words: "r" is inside almost everything, "sql" is inside "nosql". Whole tokens only match whole words, and the tokenizer decides what a word is, for example keeping `a/b` and `r&d` together.
2. The synonym table maps both `powerbi` and `power bi` to the canonical name `power bi`, and "Power-BI" splits into the same two tokens.
3. A missing requirement often ends the application; a missing nice to have rarely does. Equal weights would rank a posting where you have only the extras above one where you have every requirement.
4. No. It means the words line up. Level, years, location, visa status and how well your experience shows the skill all matter, and none of them is in the score.

</details>

## In real job postings

In the Real Analyst Jobs live feed on 25 October 2026, of the 2,102 US analyst postings that list tools, 72% ask for SQL and 24% for Power BI, while in India (914 postings that list tools) Power BI is at 39%. The same resume can match very differently by market, so score it against the roles you will actually apply to.

## Next

You have finished Analytics from Scratch. Well done: you have written SQL, statistics, metrics, dashboards, Python and AI workflows by hand, and now you can read the job market like data and show your work. Go back to the [course README](../../../README.md) for anything you want to revisit, and browse live analyst roles at [Real Analyst Jobs](https://realanalystjobs.com).
