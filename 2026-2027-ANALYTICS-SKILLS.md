# Analytics skills for 2026 and 2027

What employers ask analysts for today, what is rising, what is still experimental, and what AI is making less special. Every claim here comes from one of two places:

1. **Live job postings.** 9,044 analyst postings on the Real Analyst Jobs feed on 29 October 2026, of which 6,226 had at least one recognised tool tag. Percentages below use 6,226 as the denominator unless stated. The tagger looks for 18 named tools, so skills it does not tag (statistics, A/B testing, Git, Databricks, AI terms inside descriptions) are *unmeasured*, not absent.
2. **Cited external sources**, each with a link and the date we read it (31 October 2026).

The full tables, method and every source are in [docs/audit/2026-10-31-skills-evidence.md](docs/audit/2026-10-31-skills-evidence.md). This page is refreshed when the evidence is.

## The short version

- **The core has not changed.** SQL is in 69.9% of postings, Python 48.4%, Excel 40.7%, Tableau 31.6% and Power BI 29.8%. 75.6% ask for SQL or Python. Entry-level postings lean harder on Excel (58.5%) and already ask for Python (47.2%).
- **AI is now part of the job description, not yet the job title.** 45% of data and analytics postings on Indeed mentioned AI in December 2025, the highest of any sector ([Indeed Hiring Lab](https://hiringlab.indeed.com/2026/01/22/january-labor-market-update-jobs-mentioning-ai-are-growing-amid-broader-hiring-weakness/)). Only 3.3% of our 9,044 titles contain an AI word.
- **The scarce skill is checking, not typing.** 72% of analytics engineers prioritise AI-assisted coding, and 71% name hallucinated output reaching stakeholders as a top concern ([dbt Labs, 2026 State of Analytics Engineering](https://www.getdbt.com/blog/new-dbt-labs-report-finds-ai-driven-acceleration-is-outpacing-trust-and-governance)). 66% of developers report AI answers that are almost right but not quite ([Stack Overflow 2025](https://survey.stackoverflow.co/2025/ai)).
- **Seniority adds the warehouse layer.** Snowflake rises from 8.7% of entry-level postings to 20.3% of senior ones, and dbt from 2.8% to 11.0%.

## Skills by tier

### Tier 1: essential now

| Skill | Evidence | Where the course teaches it |
|---|---|---|
| SQL: joins, aggregation, windows, CTEs, and reading other people's queries | 69.9% overall, 65.0% at entry level, 83.7% of data analyst and 84.6% of product analyst postings | Phases 00 and 01 |
| Spreadsheets | 40.7% overall, 58.5% at entry level, 63.8% of financial analyst postings | Phase 04 lessons 05 and 06 |
| One BI tool in depth | Any BI tool 46.8%. Power BI 59.6% of BI analyst postings (Amazon excluded) | Phase 04 |
| Python for analysis | 48.4% overall, 66.2% of data analyst postings, 27.0% of business analyst postings | Phases 00 and 05 |
| Defining metrics and framing the business question | Not countable by our tagger. dbt Labs 2026: trust as a priority rose from 66% to 83%; 41% are blocked by unclear data ownership | Phases 00 and 03 |
| Statistics and reading experiments | Not countable by our tagger (an evidence gap we name). Kept in tier 1 on judgment, especially for product and growth roles | Phase 02 |
| Explaining findings to non-technical people | [WEF Future of Jobs 2025](https://www.weforum.org/press/2025/01/future-of-jobs-report-2025-78-million-new-job-opportunities-by-2030-but-urgent-upskilling-needed-to-prepare-workforces/): growth skills pair technology with human skills | Every lesson's "what to tell the stakeholder", phase 07 |

### Tier 2: emerging, with evidence

| Skill | Evidence | Where |
|---|---|---|
| Cloud warehouses (Snowflake, BigQuery) | Snowflake 12.2% overall, 20.3% at senior level; BigQuery 6.8% | Phase 08 |
| dbt and tested, version-controlled SQL | dbt 7.2% overall; 14.3% of data analyst and 15.8% of product analyst postings | Phase 08 |
| Semantic layers and governed metrics | Vendors now route AI through them: [dbt Semantic Layer](https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl), [Power BI Copilot](https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-introduction), [LookML](https://docs.cloud.google.com/looker/docs/what-is-lookml). Looker appears in 27.2% of product analyst postings | Phase 04 lesson 09 |
| AI-assisted analysis with verification | Indeed 45%, dbt 72% and 71%, Stack Overflow 66% (all above) | Phase 06, plus a review lesson in SQL and BI |
| Data quality checks and reconciliation | dbt Labs 2026: 71% fear wrong output reaching stakeholders | Phases 01, 05 and 08 |
| Business analysis for AI adoption | Most of our 299 AI-titled roles are business analyst or strategy roles | Phases 06 and 09 |

### Tier 3: experimental, worth exploring

| Skill | Evidence | Where |
|---|---|---|
| MCP: giving an assistant safe access to data | An open standard supported by major AI clients ([modelcontextprotocol.io](https://modelcontextprotocol.io/docs/getting-started/intro)); zero mentions in our job titles | Phase 06 lesson 15 |
| Structured outputs and tool use | Documented by [Anthropic](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) and [OpenAI](https://developers.openai.com/api/docs/guides/structured-outputs); no hiring count yet | Phase 06 |
| Agentic analysis workflows | 30.9% of developers use agents at work, and 24.9% of those use them for data and analytics ([Stack Overflow 2025](https://survey.stackoverflow.co/2025/ai)); 16 "agentic" titles in our feed | Phase 06, capstone 08 |
| Evaluating text-to-SQL | The best agent solved 21.3% of enterprise tasks in the [Spider 2.0 paper](https://arxiv.org/abs/2411.07763) (March 2025); today's [leaderboard](https://spider2-sql.github.io/) shows higher, self-reported, undated scores. Treat benchmark scores as direction, not a promise on your data | Phase 06 lessons 02 and 10 |
| Orchestration and Spark | Airflow 2.8%, Spark 4.4%: mostly data engineering | Phase 08 (concepts only) |

### Tier 4: less of a differentiator because of AI

Still worth knowing. An analyst must read, check and fix this work. What is changing is that doing it by hand from memory sets you apart less. The reasoning is ours, labelled as inference.

| Skill | Why | What to get good at instead |
|---|---|---|
| Writing routine SQL from a blank page | Assistants draft it (dbt Labs: 72% prioritise AI-assisted coding). SQL is still the most requested skill, so learn it fully | Reviewing a query: grain, join fan-out, NULLs, filters, reconciling to a known total |
| First-draft charts and dashboards | Power BI Copilot creates report pages | Choosing what to show for a decision, and the model underneath |
| Hand-written DAX, LookML and measure descriptions | Copilot writes DAX and descriptions | Modelling and naming that a person and an AI read the same way |
| Formula recall (VLOOKUP, pivots) on its own | Assistants handle syntax; Excel is still in 40.7% of postings | Auditable spreadsheet models |
| Summarising a report in prose | Copilot drafts summaries | The recommendation, the trade-off and the caveat |

## What is established and what is speculation

Established, because someone measured it:
- AI is mentioned in a large minority of data job ads, and job titles have barely moved.
- Practitioners already use AI to write analytics code.
- Trust, not access, is the bottleneck.
- SQL, a spreadsheet, a BI tool and Python still cover most postings.

Not established, so this course does not claim it:
- That AI will shrink analyst hiring. The US Bureau of Labor Statistics projects growth to 2035 for every nearby occupation: data scientists 35%, operations research analysts 12%, management analysts 10%, financial analysts 7% ([BLS](https://www.bls.gov/ooh/math/data-scientists.htm)). Those projections may not fully reflect AI.
- That benchmark text-to-SQL scores hold on messy company data.
- That MCP or agent skills will become hiring requirements for analysts.

## Skills by role

| Role | What sets it apart |
|---|---|
| Data analyst | Most Python (66.2%) and R (25.9%), most warehouse exposure (Snowflake 17.2%, dbt 14.3%) |
| Business analyst | Least Python (27.0%), Excel 43.2%, requirements and process work, most of the AI-adoption roles |
| Product analyst | Most SQL (84.6%), Looker 27.2%, experiments and product metrics |
| BI analyst | Power BI 59.6%, Tableau 43.9%, semantic models |
| Growth or marketing analyst | SQL 83.9%, Tableau 49.3%, attribution and experiments |
| Analytics manager | Still hands-on (SQL 83.2%, Python 58.0%), plus data ownership and AI governance |

The [learning roadmap](LEARNING_ROADMAP.md) turns this into a lesson order for each role.
