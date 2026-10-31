# Skills

This folder holds a SKILL.md tutor for coding agents (Claude Code, Cursor, Codex, or any agent that reads SKILL.md files). Once installed, ask your agent to "tutor me through analytics from scratch". It places you with up to five short questions (running code, SQL, statistics, Python, and your goal), picks a starting lesson, and teaches one lesson at a time.

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
