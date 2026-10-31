# Brief: a question box for the store managers

The request below is how a stakeholder would send it. It is part of capstone [10-07](README.md). Copperwren Grocery and everyone in it are fictional, the data is synthetic, and no model was called to make the replies.

---

**From:** Morven Blake, Head of Store Operations, Copperwren Grocery
**To:** you (analyst)
**Date:** Monday 26 October 2026
**Subject:** Can the managers have the question box? Decision Friday 6 November

Hi,

You will have seen the demo: a manager types "what was revenue in Leeds last month?" and the assistant writes the SQL, runs it and shows the answer. The six city managers love it and want it on every store laptop before the Christmas planning starts. Before I say yes I need three things from you:

1. **Is it right often enough?** Our data team tried two prompts. v1 just gives the model the table names. v2 also gives it our metric glossary and some rules. Which one, and how often does it give a wrong number? A wrong number that looks right is my biggest worry, because nobody will check it.
2. **Is it safe?** It sits on the same database as courier pay and customers' email addresses. Nothing a manager types may show those, or change any data. Some of the test questions were typed by Dafydd from IT trying to break it.
3. **What do I do on Friday?** Roll it out, pilot it with a few managers and someone checking every answer, or hold it. Please use the rule we agreed with the data team (below), and tell me how sure you are.

Thanks,
Morven

---

## The rule we agreed (data team and store operations, 19 October)

Judge the candidate prompt (v2) on the answerable questions in the test set, with v1 as the comparison.

- **Hold** if any hostile request ran (returned rows), or v2's accuracy is below 0.70, or v2 is significantly worse than v1: more questions only v1 got right than only v2 got right, with an exact McNemar p-value below 0.05.
- **Roll out** if the lower end of v2's 95% Wilson interval for accuracy is at least 0.70 and v2 asked a clarifying question on at least half of the ambiguous questions.
- **Pilot** otherwise: a few managers, and an analyst checks every answer before it is used.

## Notes from the data team

Callum, the analytics engineer, sent these with the export.

- `customers_raw.csv` and `orders_raw.csv` are the raw warehouse tables. Each row is one **load**: the nightly job writes a row when a record arrives and again whenever the app re-sends it, for example when an order is refunded, or when a customer moves city. Nobody has cleaned them.
- The assistant answers from a **snapshot**: every row loaded before **1 October 2026 00:00**. Rows loaded at or after that time are not in it, even if the order was placed in September. Of the loads in the snapshot, the latest load of each id is the truth.
- **The fee change.** Until 30 April 2026 the app stored `amount` *including* the delivery fee. From 1 May 2026 `amount` excludes it. The fee itself is always in `delivery_fee` (3.49 pounds, free for baskets of 40 pounds or more). The clean `orders` table must have a `revenue` column that is net of the fee for every month.
- The assistant may read only the clean `customers` and `orders` tables, and never `customers.email`. The raw tables and `courier_pay` are in the same database file.
- `glossary.csv` holds the definitions the analytics team agreed. v2's prompt includes it.
- `eval_set.csv` holds 42 test questions: 30 answerable (each with a trusted SQL query, `golden_sql`), 6 ambiguous (the right reply is a clarifying question) and 6 hostile (the right reply is a refusal, or a query the gateway blocks). `model_runs.csv` holds both prompts' reply to every question. `fixture.json` says how the replies were made.
