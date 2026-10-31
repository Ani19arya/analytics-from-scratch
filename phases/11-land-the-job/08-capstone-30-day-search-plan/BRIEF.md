# Brief: Kavya's next 30 days

The request below is how a job seeker would send it to someone helping her. It is part of capstone [11-08](README.md). Kavya, Nikhil, Lanternway Courses and every company in `data/` are fictional, and the postings and the application log are synthetic.

---

**From:** Kavya Menon
**To:** you (a friend from her analytics course, who offered to help)
**Cc:** Nikhil, career coach at Lanternway Courses
**Date:** Sunday 1 November 2026
**Subject:** Can you help me turn this into a plan?

Hi,

I spent last week applying to everything that looked right, and I am already tired. I got a few recruiter calls, one interview and a lot of silence. Nikhil says I need a plan I can follow for a month and check every week, not more late nights. Could you build it with me?

About me:

- I live in Pune, India, and I am an Indian citizen. I have no work visa for any other country.
- I can work on site or hybrid in Pune, Bengaluru or Mumbai. I am not moving anywhere else in India right now.
- I would move abroad, but only for an employer that sponsors the visa. I cannot pay for that myself.
- Remote is great if the employer can actually hire someone in India.
- I work full time as an MIS executive (two years, mostly Excel and SQL reports), so I have **10 hours a week** for the search, no more. Evenings and Saturdays.
- My tools: SQL, Excel, Tableau, some Python.
- I want analyst roles: data analyst, business analyst, product analyst or BI analyst, under whatever title the company uses.

What I need:

1. A plan for the 30 days from **Monday 2 November to Tuesday 1 December 2026**: what to do on which day, and how long it takes.
2. Only postings I can really be hired for. Last week I applied to a "remote" role and the recruiter told me it was US only.
3. Nothing old, closed or dodgy. One posting asked for a "registration fee".
4. A way to know if it is working: a check every week with the numbers, starting with last week's.

I saved every posting I found into a spreadsheet, and I kept a log of last week. Both are attached.

Thanks,
Kavya

---

## Notes from Nikhil

- `data/postings.csv` is Kavya's saved list as of Sunday 1 November, 246 rows. She saved some roles twice, from a job board and from the company's careers page, sometimes under two ids. A role is a company, a title and a city; the same role twice is one role. Where a role was saved twice, apply through the newest posting.
- `remote_regions` is the list of countries or regions a remote posting says it hires from (`IN`, `APAC`, `WORLDWIDE`, `US`, `GB;IE` and so on). Empty means the posting does not say. Do not guess: until the listing says it hires from India, it is not a target. Kavya can ask the recruiter, but that is a task, not an application.
- Sponsorship: read what the posting says in its own words. The phrases to look for are in `exercise.py` (`SPONSOR_YES`, `SPONSOR_NO`). If a posting says both, believe the no. Silence is not a yes.
- Stale: a posting first posted more than 30 days before 2 November is stale, and so is one whose `closes_on` date is before 2 November. If a posting closes during the plan, the application must be on or before that date.
- Red flags: any phrase in `RED_FLAGS` (a fee, a deposit, a "guaranteed job", a chat-app-only contact). Skip the posting. Real employers do not charge you to apply.
- Titles: the synonym families are in `TITLE_FAMILIES`. Kavya searched for "data analyst" only, which is why her list is short on the other three families.
- `data/app_log.csv` is her log for 26 October to 1 November, one row per event. She typed some rows twice. On 29 October she switched tracker templates, and the stage `phone_screen` became `screen`: the same stage under a new name.
- Time card (how long each task takes, at least): a tailored application 1.5 hours, a weekly review 1 hour, a skill block 1 hour, a referral or networking message 0.5 hours, a search refresh 0.5 hours, a follow-up 0.25 hours. Ten hours a week is the ceiling; the last two days of the plan get their share (10 x 2 / 7 = 2.86 hours).
- Last week, 4 applications came through a referral and 2 of them got a screen. That is 4 data points, not a rate to bank on, but it is a reason to spend some hours asking people.
