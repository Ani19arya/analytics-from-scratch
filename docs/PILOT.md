# Running a pilot

A plan for the course owner to run a pilot with 20 to 100 learners and learn whether the course works, without tracking anyone. Nothing in the course collects or sends data. Learners share only what they choose to, in two ways:

1. `python3 tools/progress.py export`: a pseudonymous summary of their own progress (no name or contact details, but a random id and their activity pattern could still point to them in a small group). It prints exactly what it includes and writes nothing until they type `y` or pass `--yes`. The default `--level coarse` leaves out dates, tries and scores; `--level full` keeps them and is meant to be sent privately to you.
2. The [Pilot check-in](../.github/ISSUE_TEMPLATE/pilot-check-in.yml) issue form: a short weekly form where they can answer four questions and, if they want, paste a coarse export.

Stuck points also come in through [I got stuck on a lesson](../.github/ISSUE_TEMPLATE/stuck-on-a-lesson.yml) and errors through [Something in a lesson is wrong](../.github/ISSUE_TEMPLATE/lesson-is-wrong.yml).

## Before you start

- Decide the dates (for example four to six weeks) and the one question the pilot must answer, such as "do beginners get through phase 00 and pass a first SQL lesson?".
- Write down now what result would make you change something. Without that, any number looks fine afterwards.
- Pin the course version. Ask learners to work from one commit or tag, so you compare like with like. A full export records `course_version` (the git short sha, or `unknown`); a coarse one records only `course_month`.
- Decide how exports reach you. Public issues: coarse only. Full exports: a private channel you name (email, a private form or a private repo), never a public issue.
- Tell learners, in plain words: what you will ask them to share, that it is optional, that exports are pseudonymous and not anonymous, that issues on a public repo are visible to everyone, how to send an export privately instead, and that they can ask you to delete their data (see the privacy section). Full exports keep a pilot id that they can replace at any time with `progress.py export --level full --new-id` (then their old and new exports no longer line up).
- Ask every learner to run the placement check in week 1 (`python3 tools/progress.py placement`) and again at the end. The 13 base questions are the same every time; a few follow-up questions depend on earlier answers, so compare per-area percentages, not raw totals.

## What learners do

- Week 1: placement, then lessons as `progress.py status` suggests. Record each one with `progress.py check <lesson-id>`.
- Each week: open a Pilot check-in issue. Pasting a coarse export is optional.
- When stuck for a while: open an "I got stuck on a lesson" issue.
- At the end: placement again, then one last export (coarse in public, or full sent privately to you).

## What an export contains

Each level has its own allowlist of keys, and `test_progress.py` fails if any key outside that level's allowlist appears. Neither level has notes, names, emails, paths or typed text.

Coarse (`--level coarse`, the default, schema `afs-pilot-export-coarse-1`): `export_id` (a fresh random id for this one export, not stored anywhere), `exported_week` (ISO week such as `2026-W44`), `course_month` (such as `2026-10`), `track`, `placement` (count, then the level per area for the first and latest placement: strong, mixed or weak, no scores), `lessons` (per lesson tried: id and passed true or false), `activity` (in days since the first day of activity: latest day, the export day, the day of the first pass) and `interviews` (per round passed true or false, and pass or not yet overall, no 1 to 4 scores). No day dates anywhere.

Full (`--level full`, schema `afs-pilot-export-1`): `pilot_id` (random, stored in the learner's profile so weekly exports line up), `exported_on` (day), `course_version`, `track`, `placement` (count, then first and latest: day, correct, total, and per area correct, total and level), `lessons` (per lesson tried: id, day of first try, tries, passed, day passed, failed tries before the pass), `activity` (first day, latest day, days between) and `interviews` (day, 1 to 4 score per round, pass or not yet).

## Collect and compute

Save each export you receive as its own `.json` file in one folder (copy the JSON from a check-in issue or a private message into a file). Keep that folder out of the repo. Then run:

```
python3 tools/progress.py aggregate pilot-exports/
python3 tools/progress.py aggregate pilot-exports/ --json
```

It reads every `*.json` file in the folder, of either level, and skips files that are not exports. Full exports are deduplicated by pilot id (the latest one wins), so weekly full exports from one learner count once. Coarse exports have no lasting id, so they cannot be linked: the same file saved twice counts once (same `export_id`), but two coarse exports from one learner count as two. That is the price of the coarse level. If you use coarse exports, ask for one per learner, at the end, and treat earlier weekly ones as a rough signal only. The output says how many exports of each level it read and which metrics coarse exports cannot give.

What coarse exports can and cannot give:

- Same as full: placement completion, first lesson pass and the days to it, day-7 return (from days since first activity), lessons passed per learner, capstone completion, mock interview pass, and per lesson how many tried and how many have not passed.
- Not from coarse: placement change in points (coarse has levels only, so `aggregate` adds `placement_level_change`, counting areas whose level went up, stayed or went down, from both levels), the median failed tries before a pass (full exports only), and a reliable one-per-learner count.

If you prefer to compute by hand, every metric below comes from a few fields, and this standard library snippet is a starting point:

```python
import glob, json
rows = [json.load(open(p)) for p in glob.glob("pilot-exports/*.json")]
rows = [r for r in rows if r.get("schema") in ("afs-pilot-export-1", "afs-pilot-export-coarse-1")]
print(sum(1 for r in rows if r["placement"]), "of", len(rows), "completed placement")
```

## What to measure, and what each one decides

Report every metric as "k of n", with n stated. With 20 to 100 learners, a difference of a few people is noise; look for large, consistent patterns and read the issues alongside the numbers.

| Metric | How it is computed from exports | What it informs |
|---|---|---|
| Placement completion | `placement` is not null | Is the placement check too long or unclear as a first step? |
| First lesson pass | `lessons.passed` is at least 1; also the days from `activity.first_day` to the first `passed_on` | Is setup (Python, the first lesson) a wall? If few pass a first lesson, fix phase 00 before anything else. |
| Day-7 return | `activity.latest_day` is 7 or more days after `activity.first_day`, counted only among learners whose `exported_on` is at least 7 days after their first day (coarse: `activity.latest_day` and `activity.export_day` are already days since the first day) | Do people come back after the first sitting? Low return points to pacing, length or motivation, not content. |
| Lessons passed per learner | median, min and max of `lessons.passed` | Overall progress. Compare against the pace you planned for the pilot dates. |
| Placement before and after | full exports with `placement.count` of 2 or more: per area, latest percent correct minus first percent correct (median across learners); for both levels, how many areas moved up, stayed or moved down a level | Which areas the lessons actually move. An area that does not move is the first to rewrite. |
| Capstone completion | at least one passed lesson whose id starts with `10-` | Do learners reach the work they would show an employer? |
| Where people get stuck | per lesson: how many tried it, how many have not passed, median failed tries before a pass (full exports only); plus "I got stuck" issues by lesson id and step | Which lessons to fix first. The issue text says why; the export says how many. |
| Mock interviews (if used) | learners with any `interviews`, and how many passed their latest | Whether the getting-hired part is used at all. |
| Clarity and recommend | count the answers in the check-in issues | A check on the numbers: a lesson can be passed and still feel confusing. |

Keep in mind who is missing: learners who stop rarely send a last export. Count how many started (for example, people who sent any export or check-in) and say how many of them you have final data for. Do not read the pilot as a measure of job outcomes; it measures progress through the course.

## Privacy

Exports are pseudonymous, not anonymous. Pseudonymous means there is no name or contact details, but a random id and an activity pattern could still point to one person. In a pilot of 20 to 100 people that risk is real: someone who knows a learner started in a given week, or passed a given lesson, may be able to pick out their export, especially a full one with a lasting pilot id, exact dates, tries per lesson, scores and the course commit.

- Default is no data. Learners who never run `export` or open an issue share nothing.
- Coarse for public, full only in private. Anything pasted in a GitHub issue on a public repo is visible to everyone and copies can outlive an edit or a deletion. Ask for coarse exports in public issues. Ask for full exports only through a private channel to you, and only if you need the extra detail (tries per lesson, score changes).
- Exports carry no free text, but issue forms do. If someone pastes a name, email or a path with their user name, edit the issue to remove it. If someone pastes a full export in a public issue, offer to remove it and suggest a coarse one instead.
- Do not publish per-learner exports, in the repo, an issue, a report or a slide. Publish only aggregate counts, and do not report a count small enough to point to one person (for example "1 of 20 passed lesson 07-03").
- Do not ask learners which pilot id is theirs, and do not join exports to GitHub user names or other data in your analysis.
- Retention: keep the folder of exports private, outside the repo, and delete it when the pilot is over (say the date up front, for example 30 days after the last week). Delete any copies, such as the JSON in closed issues, at the same time.
- Deletion on request: a learner can ask you to delete their data at any time by sending their pilot id (it is in the `pilot_id` field of their full export and in `.learner/profile.json`). Delete every file with that id and confirm. Coarse exports have no lasting id, so a learner asking for deletion should send the `export_id` of each coarse export they shared, or you can remove the check-in issues they opened.

## After the pilot

Write down, for each metric, the number, the n, and the decision it led to (or "no change"). Fix the lessons named most often in "where people get stuck" and in stuck issues first, then run the same plan again on the new course version.
