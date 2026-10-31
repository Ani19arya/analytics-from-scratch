# Skills

This folder holds a SKILL.md tutor for coding agents (Claude Code, Cursor, Codex, or any agent that reads SKILL.md files). Once installed, ask your agent to "tutor me through analytics from scratch". It places you with up to five short questions (running code, SQL, statistics, Python, and your goal), picks a starting lesson, and teaches one lesson at a time.

It works in three modes. It asks which one you want if you do not say, and you can switch at any time ("switch to interviewer mode", "slow down"):

- **Beginner.** Plain words and an everyday analogy first. It asks you to predict the output before you run anything, and gives hints one step at a time before any answer.
- **Working analyst.** Starts with the placement check `python3 tools/placement.py`, skips what you already know, and frames each lesson as a workplace problem with a stakeholder, a deadline and messy data. It challenges your recommendation: what would change your mind, what is the counterfactual, what did you not check.
- **Interviewer.** A 45 minute mock analytics interview: SQL (about 12 minutes), statistics (10), a metrics case (12), a behavioural question (6) and a scorecard (5). Every question comes from a course lesson, and the scorecard quotes your answers against a transparent rubric and names the lessons to revisit. The rubric and question bank are in [INTERVIEW_RUBRIC.md](analytics-from-scratch/INTERVIEW_RUBRIC.md). It is practice, not a prediction of a real interview.

All three modes share one learner profile, `.learner/profile.json` (kept on your computer, gitignored), read and written with `python3 tools/progress.py`: `status` at the start of a session, `check <lesson-id>` after a lesson, and the placement result and mock interview scorecards recorded as you go. `progress.py report --md` shows your before and after.

In every mode it only sends you to lessons that exist, never invents numbers, asks you to run the tests, and gives honest feedback.

What the tutor does:

- **Places you.** Complete beginners start in [phases/00-start-here](../phases/00-start-here). Someone comfortable with SQL and statistics but new to Python goes to the Python phase before the AI and getting-hired lessons, which use Python. An interview next week can start at the SQL interview questions.
- **Follows the course order.** The order comes from [LEARNING_ROADMAP.md](../LEARNING_ROADMAP.md) and [curriculum.json](../curriculum.json): every subject at Level 1 (beginner), then Level 2 (intermediate), then Level 3 (advanced), with Level 4 (land the job) for the search itself. It only sends you to lessons that exist.
- **Teaches the lesson shape.** Each lesson has Before you start, In plain words, a diagram where the idea has a shape, a walk through, Common mistakes, Check yourself and What to tell the stakeholder.
- **Gives hints before answers.** It will not paste the solution as its answer. After your own attempt you may open `solution/` and it will compare it with your code line by line. Running the worked answer the way a lesson's walk through does is always fine.
- **Checks understanding.** After your test passes, it asks you to explain one line or predict one output, because a passing test does not prove you could write it again.

## Install

With the skills CLI:

```
npx skills add Ani19arya/analytics-from-scratch
```

Manual install for Claude Code: copy the skill folder into your skills directory.

```
mkdir -p ~/.claude/skills
cp -r skills/analytics-from-scratch ~/.claude/skills/
```

Then open your agent inside a clone of this repo so it can see the lessons.

## What is inside

- `analytics-from-scratch/SKILL.md`: the tutor instructions.
- `analytics-from-scratch/INTERVIEW_RUBRIC.md`: the rounds, scoring scale, pass and fail examples, red flags and question bank for Interviewer mode.
