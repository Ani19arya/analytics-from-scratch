# Skills

This folder holds a SKILL.md tutor for coding agents (Claude Code, Cursor, Codex, or any agent that reads SKILL.md files). Once installed, ask your agent to "tutor me through analytics from scratch" and it will place you with three questions, pick a starting lesson in `phases/`, and teach one lesson at a time with hints before answers.

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
