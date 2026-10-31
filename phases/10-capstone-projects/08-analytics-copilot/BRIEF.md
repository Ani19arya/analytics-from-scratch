# Brief: why did weekend rentals fall in September?

The request below is how a stakeholder would send it. It is part of capstone [10-08](README.md). Bramblequay Bikes and everyone in it are fictional, the data is synthetic, and no model was called to make the copilot's session.

---

**From:** Odile Marchetti, Chief Operating Officer, Bramblequay Bikes
**To:** you (analyst)
**Date:** Friday 2 October 2026
**Subject:** Weekend rentals, and the copilot. Ops meeting Thursday 8 October

Hi,

The September dashboard says weekend rentals fell by about a third. I asked the new analytics copilot why. It planned some queries, ran them, and drafted this:

> "Weekend rentals fell from 256 in August to 171 in September, a 49.7% drop. ... We recommend a temporary dock at the Riverside footbridge until the roadworks end, and a 15% weekend discount sent to the 52 casual riders who stopped riding."

Nadia reviewed each of its steps as it went, and she was not comfortable with all of them. I am not taking a discount to the ops meeting on the word of a chatbot. Before Thursday I need:

1. **A replay I can trust.** Rebuild the copilot's session from the recording, with nothing running unless Nadia approved it, exactly the SQL that ran written down, and the checks done by code, not by the model.
2. **Which of its numbers are right.** Every number in the draft, checked against the step it says it came from.
3. **Your recommendation.** Why weekend rentals fell, whether we need a discount, and what we should do, with how sure you are.

Thanks,
Odile

---

## How the copilot works (from the data team)

Theo, who set the copilot up, sent these notes with the recording.

- **Agents.** A planner writes a numbered plan; a query agent writes the SQL for each query step; a checker runs the check steps; a recommender writes the draft and must cite, for every number, the step and cell it came from. In this recording the planner's and query agent's output is `plan.json` and the recommender's is `draft.json`.
- **The human step.** Every step needs a decision from the reviewer before it runs, recorded in `approvals.csv`: `approve`, `edit` (run the reviewer's `edited_sql` instead) or `reject`. If a step has no decision, the copilot must stop and wait; it must never run past it. If a reviewer recorded more than one decision for a step, the last one counts.
- **The gateway.** Every query runs read-only behind an allowlist: tables `rentals` (the clean table), `stations`, `station_events` and `riders`, but never `riders.email`. A person approving a step does not lift this.
- **The budget.** At most 8 steps may run in one session.
- **Release.** The recommendation goes to Odile only if every check step ran and passed, every number in the draft matches its cited cell at the precision it is written, every cited step actually ran, and every other number is labelled as an assumption.

## Notes on the data

- `rentals_raw.csv` is the raw warehouse table: one row per **load** of a rental. The app re-sends some rentals, so a rental can be loaded twice.
- The session ran on a **snapshot**: rows loaded before **1 October 2026 00:00**. Rentals of 30 September load the next night, so they are not in it. Of the loads in the snapshot, the latest load of each rental wins.
- **The definition changed on 16 August.** Before, the app dropped "false starts" (a bike unlocked and re-docked within 2 minutes). From 16 August it logs them as rentals with `duration_min` 0 or 1. Finance counts a rental only if it lasted at least 2 minutes, so the clean `rentals` table keeps only those, in every month.
- `stations.csv` is maintained by hand. `station_events.csv` lists closures. Weekend means Saturday and Sunday.
