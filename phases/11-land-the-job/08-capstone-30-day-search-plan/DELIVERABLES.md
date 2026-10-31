# Deliverables: what to hand in

Part of capstone [11-08](README.md). Read [BRIEF.md](BRIEF.md) first.

## 1. The functions and the plan (checked by the test)

Fill in every function marked TODO in `exercise.py`, then run `python3 test_lesson.py` from this folder. The test checks your functions on the committed data, on a second dataset built from another seed, and on small hand-made cases, and it checks the plan your `build_plan` returns against every rule below. Then run `python3 exercise.py`: it writes your plan to `plan.json`, the machine-readable file you hand in, and the test checks that file too.

### The rules (the test uses exactly these)

| # | Rule | Definition |
|---|---|---|
| 1 | Eligible | Remote: `remote_regions` names one of `IN`, `APAC`, `WORLDWIDE`. On site or hybrid in India: the city is Pune, Bengaluru or Mumbai. On site or hybrid anywhere else: `sponsorship_stated(description)` is `"yes"` |
| 2 | Sponsorship stated | `"no"` if the description contains any `SPONSOR_NO` phrase, else `"yes"` if any `SPONSOR_YES` phrase, else `"not_stated"`. Case does not matter |
| 3 | Stale | `posted_date` more than 30 days before 2 November 2026 (so 3 October is fresh, 2 October is stale), or `closes_on` before 2 November |
| 4 | Red flag | The description contains any `RED_FLAGS` phrase, any case |
| 5 | Title family | The first family in `FAMILY_ORDER` (bi, product, business, data) with a synonym inside the lowercased title; `None` if none |
| 6 | Role | `(company, title, city)`, each trimmed and lowercased |
| 7 | Usable posting | Eligible, not stale, no red flag, family in Kavya's targets, and its role is not a role in the log (under any posting id). One per role: the newest `posted_date`, then the smallest `posting_id`. Sorted by `posting_id` |
| 8 | Plan window | `start` 2026-11-02, `end` 2026-12-01 (start + 29 days). Every task date inside it |
| 9 | Week | `week = (date - start) in days // 7 + 1`. Weeks 1 to 4 are full; week 5 is 30 November and 1 December |
| 10 | Hours | Each task has at least the time-card hours for its kind. Per week, the sum is at most 10 hours; week 5 at most 10 x 2 / 7 |
| 11 | Applications | Every `apply` task names a usable posting, dated on or before its `closes_on`. No role twice. At least 16 applications (or every usable posting, if there are fewer) |
| 12 | Search terms | Every term is a synonym from `TITLE_FAMILIES` for a target family, each target family has at least two terms, and every usable posting's title contains at least one term |
| 13 | Reviews | At least one `review` task in each of weeks 1 to 4. The earliest review carries `funnel`: the funnel of last week's log, computed as below |

### The funnel (rule 13)

| Key | Definition |
|---|---|
| applications | Distinct `application_id` in the log |
| responses | Applications with any event other than `applied` |
| screens | Applications that reached `screen` (or `phone_screen`, the old name), `interview` or `offer` |
| interviews | Applications that reached `interview` or `offer` |
| offers | Applications with `offer` |
| rejections | Applications with `rejected` |
| no_reply | applications - responses |
| response_rate, screen_rate | responses / applications, screens / applications; `None` with no applications |
| interview_rate | interviews / screens; `None` with no screens |
| by_channel | For each channel (a blank channel is `"unknown"`): `{"applications", "screens", "screen_rate"}` |

A row typed twice is one event. Rates are not rounded.

### The plan structure

```
{"seeker": "Kavya Menon", "start": "2026-11-02", "end": "2026-12-01", "hours_per_week": 10,
 "search_terms": ["business intelligence", ...],
 "tasks": [{"date": "2026-11-02", "week": 1, "kind": "review", "hours": 1.0, "note": "...", "funnel": {...}},
           {"date": "2026-11-03", "week": 1, "kind": "apply", "hours": 1.5, "note": "...", "posting_id": "P0219"},
           ...]}
```

Task kinds: `apply`, `network`, `search`, `follow_up`, `review`, `skill`.

### plan_problems

`plan_problems(plan, postings, log, profile)` returns the sorted list of distinct codes for the rules the plan breaks, `[]` when it keeps them all:

| Code | When |
|---|---|
| window | `start` or `end` is wrong, or a task date is outside the 30 days |
| week | A task's `week` does not match its date |
| task_hours | A task has fewer hours than the time card, or an unknown kind |
| hours | A week inside the plan is over its budget (a task outside the plan is a `window` problem only) |
| ineligible | An application to an unknown posting id or a posting Kavya cannot be hired for |
| stale | An application to a stale posting, or dated after the posting's `closes_on` |
| red_flag | An application to a red-flagged posting |
| not_target | An application to a posting outside the target families |
| duplicate | Two applications to one role, or an application to a role already in the log |
| volume | Fewer applications than rule 11 asks |
| coverage | Rule 12 broken |
| review | A full week without a review |
| funnel | The earliest review has no funnel, or a wrong one |

## 2. The plan as a page Kavya can follow

A one-page calendar or table from your `plan.json`: week by week, what she does on which day and for how long, with the posting and company for each application. Any format.

## 3. The weekly review template

What Kavya looks at every Monday: the funnel keys above, for the week and for the search so far, and the one decision each number feeds (for example: if the referral screen rate stays above the job board's after 10 more applications, move one application slot a week to networking). Fill it in for week 1 from the log.

## 4. A one-page note to Kavya

At most one page, in this order:

1. The plan in two sentences: how many applications, where, and how the 10 hours are split.
2. What you left out and why, with counts: postings she cannot be hired for, stale or closed, red-flagged, reposts and roles she already applied to.
3. Last week in numbers (the funnel) and what it does and does not tell her.
4. The weekly review: what she checks and what she changes on each result.
5. Limits: what the plan cannot know, and what would change it.

Score it with [RUBRIC.md](RUBRIC.md). Then read [solution/WRITEUP.md](solution/WRITEUP.md) and compare.
