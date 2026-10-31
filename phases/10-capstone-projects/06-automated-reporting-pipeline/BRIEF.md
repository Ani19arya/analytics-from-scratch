# Brief: make the weekly business review run itself

The request below is how a stakeholder would send it. It is part of capstone [10-06](README.md). Parcelwick and everyone in it are fictional, and the data is synthetic.

---

**From:** Owen Marsh, COO, Parcelwick
**To:** you (analyst)
**Date:** Tuesday 27 October 2026
**Subject:** The Monday WBR, before Femi leaves on 6 November

Hi,

Every Monday Femi builds the weekly business review (WBR) by hand from the courier system's drop: parcels, delivered, on time, failed, returned, revenue, by site. It goes to the leadership list by 9am. Femi leaves us on Friday 6 November and nobody else knows how to build it.

I want it to run itself: every Monday at 7am, build from the drop, check the data, and send. Three things matter more to me than how it looks:

1. **Never send wrong numbers quietly.** If the data is broken, do not send the report; tell the analytics team instead, and say what is wrong.
2. **Never send twice.** If the job is re-run by mistake, nobody should get a second email.
3. **Tell us when numbers change.** Three weeks in a row, the numbers in Monday's email did not match the ones Femi showed for the same week at Thursday's ops meeting. If last week's numbers moved, the email should say so, by how much.

Also, I keep hearing that Bedminster has been worse since we changed courier contract there on 21 September. I would like the report to make that visible without anyone having to ask.

Please hand over something Femi's replacement can run and fix: the code, a runbook, and the last two weeks' emails as the job would have sent them.

Thanks,
Owen

---

## Notes from the data team

Femi sent these before writing the handover.

- The courier system drops one file every **Monday at 06:00** into `data/drops/`, named `parcels_YYYY-MM-DD.csv` (the Monday's date). It holds every parcel outcome recorded in the seven days before. The first drop is 3 August 2026, the latest 26 October 2026. `data/sites.csv` lists the five locker sites.
- Columns: `parcel_id`, `site_id`, `promised_date` (the day the customer was promised), `outcome`, `outcome_date` (the day it happened), `fee_gbp` (what the sender pays us for a delivered parcel; 0.00 otherwise).
- **Late rows.** About one row in twenty misses its Monday and arrives in the next drop. A parcel delivered late is recorded when it is delivered, not when it was promised.
- **The courier app changed on 14 September.** Until then the old app wrote codes, `D` (delivered), `F` (failed attempt) and `R` (returned to sender), and wrote a row for every attempt, so a parcel can have an `F` row and a later `D` row. From the drop of 14 September the new app writes words, `delivered`, `failed` and `returned`, and writes only the final outcome. The latest outcome of a parcel is the truth.
- The 12 October drop was sent twice by mistake: `parcels_2026-10-12_resend.csv` is a copy.
- Femi counted a parcel in the week its latest outcome happened (by `outcome_date`), and on time as delivered on or before `promised_date`.
- "Sending" for this project means writing the email as an `.eml` file to an outbox folder. In production a mail relay picks up files from that folder; nothing in the project touches the network. Addresses and thresholds are in `report_config.json`.
