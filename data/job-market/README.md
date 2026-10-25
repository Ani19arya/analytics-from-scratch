# Analyst Job Market Data (monthly)

A free, open data drop of the analyst job market, published once a month by Real Analyst Jobs (https://realanalystjobs.com).

Unlike the course datasets, which are synthetic, these files are real: they are aggregates of live analyst job postings. They hold counts only. There are no company level or job level rows.

## Snapshots

| Folder | Snapshot date | Feed postings | Kept after exclusions |
|---|---|---|---|
| `2026-10/` | 2026-10-25 (run on 25 October 2026) | 8,313 | 8,158 |

## Method

1. `tools/build_job_market_snapshot.py` pages through the public feed `https://realanalystjobs.com/api/job-feed?limit=100&offset=N` until it has every posting.
2. It drops postings from Jobgether and Weekday. Both are reposting sites, so their listings repeat roles that exist elsewhere.
3. It drops any repeated posting (same slug) in case the live feed shifts between pages.
4. It counts postings per country, per country and skill, and per country and experience level.

To rebuild a month yourself (Python 3.9 or later, standard library only):

```
python3 tools/build_job_market_snapshot.py 2026-10-25
```

The feed is live, so a rerun on a later day will give slightly different numbers.

## Files and columns

### by_country.csv

| Column | Meaning |
|---|---|
| country | ISO 3166 two letter code as given by the feed. `UNKNOWN` means the feed had no country for the posting (often remote or multi location roles). |
| postings | Live analyst postings in that country. |
| companies | Distinct hiring companies in that country. |

### by_country_skill.csv

One row per country and skill, for SQL, Python, Excel, Tableau, Power BI, Looker, R and dbt.

| Column | Meaning |
|---|---|
| country | As above. |
| skill | The tool. Matching is an exact, case insensitive match on one item of the posting's comma separated tool list, so `R` does not match `Rust`. |
| postings_listing_skill | Postings in that country whose tool list includes the skill. |
| postings_listing_any_tool | Postings in that country that list at least one tool. This is the denominator. |
| share_pct | postings_listing_skill / postings_listing_any_tool, as a percentage with one decimal. Blank when no posting lists a tool. |

Shares are of postings that list tools, not of all postings. A posting that names no tools is left out of the denominator.

### by_country_seniority.csv

| Column | Meaning |
|---|---|
| country | As above. |
| experience | The feed's experience label: Entry Level, Mid Level, Senior, Lead / Staff, or Not Specified. |
| postings | Postings with that label in that country. |

## Limitations

- **One board.** These are the postings on Real Analyst Jobs only. It is not a census of all analyst jobs in any country.
- **Company career pages.** Postings are collected from company career pages and applicant tracking systems. Companies whose careers sites cannot be read are missing, so coverage is uneven across countries and industries.
- **A daily snapshot.** Each file is the state of the feed on one day. It shows what was live that day, not how many roles were posted during the month.
- **Labels are parsed from text.** Tools and experience levels are extracted from job titles and descriptions. Many postings say nothing about seniority, which is why Not Specified is large.
- **Small countries are noisy.** A country with a few dozen postings can move a lot from one month to the next.

## Updates

A new folder (`YYYY-MM/`) is added every month. Older folders are never edited, so you can compare months.

## License

CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). You may share and adapt the data for any purpose, including commercial use, if you give credit with this line:

> Real Analyst Jobs (realanalystjobs.com)

More analysis of the same feed: https://realanalystjobs.com/research/us-analyst-job-market-october-2026 and https://realanalystjobs.com/research/india-analyst-job-market-october-2026
