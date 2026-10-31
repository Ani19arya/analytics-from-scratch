# Brief: where does retention break?

The request below is how a stakeholder would send it. It is part of capstone [10-02](README.md). Chordwhistle and everyone in it are fictional, and the data is synthetic.

---

**From:** Lucia Ferrante, CEO, Chordwhistle
**To:** you (analyst)
**Cc:** Tomas Reyes (head of product), Priyanka Sood (head of growth)
**Date:** Monday 5 October 2026
**Subject:** Retention, before the planning offsite on 16 October

Hi,

Our retention dashboard shows a cliff: the share of users still active dropped hard around June, for almost every sign-up month. I am hearing two stories and I need one answer.

- Tomas thinks the app redesign we shipped on 2 June made people stop practising, and wants to bring back the old lesson screen.
- Priyanka thinks retention is fine and wants to double the paid social budget for the holiday campaign, repeating what we did in April and May.

What I need from you by Tuesday 13 October:

1. Where retention actually breaks: at which month after sign-up, and for whom.
2. Which sign-up cohort the product team should study first. They have time for one round of user interviews and one onboarding experiment this quarter, so pick one and say why.
3. Whether the June redesign is to blame.
4. What this means for the holiday campaign.

I need to be able to defend this at the offsite, so tell me how sure you are.

Thanks,
Lucia

---

## Notes from the data team

Ana, the analytics engineer, sent these with the export.

- `users.csv` and `activity.csv` are raw warehouse tables exported on **5 October 2026**. Nobody has cleaned them. Both tables can hold the same record twice when a load job was re-run.
- `users.csv`: one row per sign-up. `source` is how the user arrived: `organic` (app store search), `referral` (a friend's invite link) or `paid_social` (paid social ads). `account_type` is `customer` or `staff`; staff accounts are our own team testing the app.
- `activity.csv`: one row per user and month, with `lessons_completed` in that month. `loaded_at` is when the row arrived.
- The activity job changed on 1 June 2026. Until May it wrote a row for every user who **opened** the app in the month, even if they completed no lesson (so `lessons_completed` can be 0). From June it writes a row only when the user completed at least one lesson. Product has always defined an active user as someone who completed at least one lesson in the month.
- October rows are month-to-date: they were loaded on 5 October and cover only the first days of the month.
- We do not have ad spend or revenue in this export.
