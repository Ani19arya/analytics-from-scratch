# Brief: a churn model finance can plan 2027 with

The request below is how a stakeholder would send it. It is part of capstone [10-04](README.md). Shiftwren and everyone in it are fictional, and the data is synthetic.

---

**From:** Ciara Brennan, CFO, Shiftwren
**To:** you (analyst)
**Date:** Thursday 29 October 2026
**Subject:** Churn model for the 2027 plan, by Friday 6 November please

Hi,

We start the 2027 budget on Tuesday 10 November. I need a churn model I can put in the plan, and I need it by Friday 6 November so Declan in FP&A can wire it into the revenue sheet.

Where we are:

1. Our MRR chart has been falling since April: 187,610 EUR at the end of April, 173,542 at the end of September. Sales say the customer base is growing and new bookings are fine. One of them is wrong and I need to know which, before I tell the board.
2. In the plan we have always used one churn rate: about 3% of MRR a month, taken from the logo churn in the month-end close. Is that the right number to plan with? If it is not, what should we use instead, and does it differ by plan?
3. What MRR will today's customers give us from October to March, before any new sales? Declan adds new bookings separately, so I only want the existing book.
4. How far can I trust the model? If you tested it on the past, tell me how wrong it was.

Please keep it to something Declan can rebuild: a few rates, how they were measured, and the forecast. One page for me, the detail for him.

Thanks,
Ciara

---

## Notes from the data team

Tomas, the data engineer, sent these with the export.

- The export was taken on **31 October 2026**. It holds every billing event that took effect on or before **30 September 2026**, as loaded into the warehouse by 31 October. Three files: `accounts.csv`, `subscription_events.csv`, `finance_close.csv`.
- `subscription_events.csv` is the billing system's event log. `event_type` is `start`, `change` (upgrade or downgrade), `cancel` or `reactivate`. `plan`, `locations` and `amount` describe the subscription **after** the event; a cancel has amount 0. `requested_on` is when the customer asked, `effective_on` is when it applies, `loaded_on` is when the row reached the warehouse.
- Each event has one `event_id`. A re-load in September wrote some events twice. Where the two loads differ, the later load is a correction (usually the number of locations).
- **Definition change.** Until 31 March 2026 the billing system stored the **annual contract value** in `amount` for customers on annual billing. From 1 April 2026 (by `requested_on`) it stores the **monthly** amount for everyone. Monthly customers were always stored monthly. Nobody has restated the old rows.
- Monthly customers who cancel keep the service to the end of the month: the cancel takes effect on the 1st of the next month. Annual customers cannot leave mid-term; if they do not renew, a cancel is recorded on the anniversary of their start date.
- `accounts.csv` comes from the CRM. A re-sync wrote some accounts twice, with the id in lower case and a trailing space. The same messy ids appear in a few event rows. `billing` (monthly or annual) never changes for an account.
- `finance_close.csv` is what finance reported each month. The close is run on the 3rd of the next month, so it only sees rows loaded by then. Its churn rate is cancel rows that took effect in the month divided by all paying accounts at the month end.
- Prices (EUR a location a month): starter 39, pro 89, business 189 on monthly billing; 33, 76 and 161 on annual billing.
- Shiftwren started selling in January 2025, so the export holds the whole history.
