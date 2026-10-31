# Worked solution: Kavya's 30-day plan

Read this after you have built your own. The numbers come from `python3 solution/solution.py` on the committed (synthetic) data, and the full plan is in [plan.json](plan.json). The reasoning notes in italics say why each choice was made; they are not part of the page Kavya gets.

## The note to Kavya

**The plan.** 21 applications over 30 days, 5 a week from Tuesday to Saturday, to roles you can really be hired for: 13 on site or hybrid in Pune, Bengaluru or Mumbai, 5 remote roles whose posting names India or APAC, and 3 abroad (Singapore, the US and Germany) where the posting says it sponsors visas. Each week is exactly 10 hours: 7.5 for applications, 1 for two referral asks, 0.5 to refresh your searches, and 1 for the Monday review.

**What I left out, and why.** You saved 246 postings. In order:

| Step | Left | Removed |
|---|---|---|
| Saved | 246 | |
| Analyst role in one of your four families | 189 | 57 (financial, credit risk, data engineer, data scientist, program manager) |
| You can be hired for it | 95 | 94 |
| Fresh and still open on 2 November | 66 | 29 |
| No red flag | 63 | 3 |
| Not a role you applied to last week | 54 | 9 |
| One posting per role | 52 | 2 |

The 94 you cannot be hired for are on-site roles in Indian cities you are not moving to, remote roles that hire only from the US or the UK and Ireland or do not say where they hire, and roles abroad that say no sponsorship or say nothing about it. Silence is not a yes. Four of last week's roles are in your list again under another id, two of them reposted on 1 November: same company, title and city, so they are the same role and you have already applied.

**Last week in numbers.** 17 applications, 6 replies, 5 screens, 1 interview, 2 rejections, 11 with no reply yet. Screen rate 29.4% (5 of 17). By channel: referrals 2 screens from 4 applications, job boards 2 from 7, careers pages 1 from 6. That is one week and 17 applications: a single extra screen would reorder the channels, so it cannot tell you which channel works. It is enough to keep two referral asks a week in the plan and see if the pattern holds.

**The Monday review (1 hour).** Update the log, then compute the same numbers for the week and for the search so far: applications, replies, screens, interviews, and the screen rate per channel with its counts. Three decisions:

1. Screens so far below 2 per 10 applications after 20 applications: stop and rewrite the resume summary for the family that gets fewest replies before applying more.
2. Referral screen rate still at least twice the job board rate after 8 referral applications: move one application slot a week to two more referral asks.
3. A role closing in the coming week that is not yet in the plan: swap it in for the lowest-ranked one.

**Limits.** The plan uses what you saved on 1 November; new postings will appear every week, which is what the search refresh is for. The sponsorship and remote rules read the posting's own words, so a posting that is silent might still sponsor if you ask; that is a question for the recruiter, not an application. Twelve usable roles are Senior titles; they are at the back of the queue, not removed, because a title is not always the level. Nothing here can promise a reply or a job; it makes sure the 10 hours go to roles that could say yes.

## Reasoning

*Framing.* Kavya asked four things: days and hours, eligibility, nothing old or dodgy, and a weekly check. The note answers them in that order, with the plan first.

*Filters before ranking.* Every filter is a rule from her own words (her cities, no visa, no fees), so they run before any judgement. The order of the table is the order a reader would check: is it a role she wants, can she get it, is it still there, is it safe, has she done it.

*Ranking.* Among 52 usable postings: titles without "Senior" first (she has two years), then the share of the posting's tools she has, then the closing date (sooner first), then the newest. That puts the 8 November closing date first in week 1. The ranking is a choice, not a fact: someone who weighs closing dates first would get a different but equally valid plan, which is why the test checks the rules and not the order.

*Time.* Five applications at 1.5 hours is the most that fits after the review, the search refresh and two networking blocks (10 - 2.5 = 7.5). Cutting the networking would give one more application a week; the week-1 log (2 screens from 4 referrals) is weak evidence but enough to keep a small bet running and measure it.

*Week 5.* The last two days have 2.86 hours: the final review (1), one application (1.5) and a follow-up on old applications (0.25).

*The funnel.* Counting raw rows gives 4 screens from 18 applied rows (22.2%): it misses the three `phone_screen` rows and counts the duplicate `applied` row. The right number is 5 of 17 (29.4%).

*What the plan does not do.* It does not use salary: most postings state none (the real-market point in the README). It does not score fit beyond tools and title level; reading each posting before applying is part of the 1.5 hours.
