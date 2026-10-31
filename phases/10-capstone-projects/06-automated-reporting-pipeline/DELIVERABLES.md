# Deliverables: what to hand in

Part of capstone [10-06](README.md). Read [BRIEF.md](BRIEF.md) first.

## 1. The pipeline (checked by the test)

Fill in every function under "yours" in `exercise.py`, then run `python3 test_lesson.py` from this folder. The test checks your functions on the committed data, on a second dataset built from another seed, and on small hand-made drops; and it runs your `run` end to end in temporary folders. These are the rules the test holds you to.

| Rule | Definition |
|---|---|
| Drop date | The date in the file name, `parcels_YYYY-MM-DD*.csv`. A run for the week starting Monday W reads every drop up to and including W + 7 days |
| Outcome | `D`, `F`, `R` or `delivered`, `failed`, `returned`, in any case and with spaces trimmed. Anything else is unknown |
| Latest outcome | Per `parcel_id`: the row with the latest `outcome_date`, then the latest drop, then the later row. Rows with an unknown outcome are skipped |
| Week of a parcel | The Monday to Sunday week of its latest `outcome_date` |
| KPIs of a week | parcels; delivered; on time = delivered with `outcome_date` on or before `promised_date`; on_time_pct = 100 x on time / parcels (2 decimals, None with no parcels); failed; returned; revenue_gbp = fees of delivered parcels (2 decimals); the same by site |
| Errors (block sending) | schema: a required column missing from a drop file; outcome: any row with an unknown outcome; empty: no parcels in the week; volume: parcels below `min_volume_ratio` x the mean of the 4 weeks before (when all 4 have parcels) |
| Warnings (go in the report) | site_silent: a site with no parcels this week but parcels in each of the `outage_lookback_weeks` weeks before; unknown_site: rows with a `site_id` not in `sites.csv` |
| Sent | `outbox/<week>_wbr.eml` to `to` from `report_config.json`, subject `Parcelwick WBR, week of <week>: on time <on_time_pct to 1 decimal>%`, body starting with the summary block in `render_report`'s docstring; the week and its summary numbers recorded in `outbox/state.json` |
| Blocked | `outbox/alerts/<week>_blocked.eml` to `alert_to`, listing every error; nothing sent to leadership; the state is not changed, so the next run tries again |
| Skipped | The week is already in the state: nothing written |
| Restated | When last week's parcels or on_time_pct as known now differ from what the state says was sent, the email says both |
| Deterministic | The same data and config write the same email, byte for byte (use the given `write_email`) |

## 2. Two weeks of email, as the job would have sent them

Run the weeks of 12 and 19 October 2026 in that order into an empty outbox (`python3 exercise.py --week 2026-10-12 --outbox outbox`, then `--week 2026-10-19`), then run 19 October again. Hand in the outbox: two emails, the state file, and the "skipped" from the third run. Then break a copy of the data (for example, remove the `outcome` column from the latest drop) and show the alert your pipeline writes instead of the report.

## 3. A runbook

Half a page for Femi's replacement:

- how the job is scheduled (for example a cron line or a scheduled CI job; mark any syntax as "check your scheduler's docs");
- what each check does and what to do when the job is blocked;
- how to re-send a week on purpose, and how to re-run a week that was blocked;
- where the outbox, alerts and state live, and what to back up.

## 4. A design note

At most one page: why a parcel counts in the week of its latest outcome, why last week's numbers change and how the email handles it, which problems block sending and which only warn (and why that line is where it is), and one thing about the report itself that you would change after the first month.

## 5. Optional: a chart

An 8-week on-time trend attached to the email. `solution/solution.py` attaches a small standard-library SVG; read it after you try your own.

Score it all with [RUBRIC.md](RUBRIC.md). Then read [solution/WRITEUP.md](solution/WRITEUP.md) and compare, and open `solution/sample_outbox/` to see the emails the worked solution writes.
