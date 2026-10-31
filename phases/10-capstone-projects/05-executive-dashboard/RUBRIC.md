# Rubric: capstone 10-05, the Kettlemoor CEO dashboard

The test checks the model and the KPI numbers. This rubric scores everything else in [DELIVERABLES.md](DELIVERABLES.md). Score each row 0, 1 or 2. Out of 14: 12 or more is ready for the leadership meeting; 8 to 11 needs one more pass; below 8, go back to the model and the metric sheet.

| Area | 0 points | 1 point | 2 points |
|---|---|---|---|
| 1. Framing | A page of charts with no question behind them | Answers "against target" but not "are we growing", or the reverse | Each of Hannah's four needs maps to one element of the dashboard, and the note answers them in her order |
| 2. Model | Charts built straight on the raw export | A clean table, but no grain stated, or no checks, or the till change missed | A star schema with the grain of each table stated, the cleaning rules named, and the model checks shown passing; the missing day found by a check, not by eye |
| 3. KPI choice and comparisons | Revenue only, or growth quoted as +23% with no qualifier | LFL computed but the headline still leads with YoY, or targets shown without a status rule | LFL leads, YoY is shown with its reason, every card has one comparison (target or last year), and status thresholds are written on the dashboard |
| 4. Visual design | Pie charts, 3D, axis not from zero, or more than one screen | One screen, but the reading order is unclear or colour carries meaning without a label | Four cards on top in reading order, a trend from zero, a shop table; colour only for status and always with the word; works on a phone |
| 5. Honesty about the data | Missing data not mentioned | Mentioned in the note but not on the dashboard, or mentioned without its effect | The dashboard footer names the missing York day; the note sizes its effect (York amber, not red; company still red) |
| 6. Recommendation | "Monitor performance" | An action without an owner or a date | One or two actions, each with an owner and a date: Harrogate cost and price review before November; the missing day chased and the checks run before every refresh |
| 7. Metric sheet | None | Definitions, but with jargon or no limits | One line per KPI in plain words, the formula, and a known limit, so a shop manager can answer "why is my number different from my spreadsheet?" |

## Checks before you send

- July to September net revenue does not subtract discounts a second time.
- AOV and margin are computed over the whole month, not averaged across shops or days.
- Like-for-like leaves out Ripon (new) and Leeds (closed for a week last September), and the dashboard says so.
- The numbers in your note match the cards exactly.
- If you used a BI tool, `exports/kpis_from_tool.csv` matches the model (the test checks it).
