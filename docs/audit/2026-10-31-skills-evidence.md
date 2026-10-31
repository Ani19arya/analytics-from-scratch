# Analyst skills matrix 2026-2027: evidence pack

For the open-source course github.com/Ani19arya/analytics-from-scratch.
Prepared 31 Oct 2026. Job-feed snapshot: 29 Oct 2026. External sources accessed 31 Oct 2026.

---

## 0. How to read this (method and caveats)

**Source A: our job feed.** 9,044 live analyst postings in the public realanalystjobs.com feed, pulled 29 Oct 2026 (`dateScraped` ranges 29 Jul to 28 Oct 2026: a posting stays live until it closes, so some were first seen earlier). Fields used: title, experience, country, techStack.

Caveats that matter for every number below:

1. **techStack is a fixed 18-tag vocabulary**, not a full read of the description. The tagger (`lib/tech-stack.ts` in the site repo, mirrored in the scraper) only looks for: SQL, Python, Tableau, Power BI, Looker, dbt, Snowflake, BigQuery, Redshift, Excel, G-Sheets, AWS, Azure, Spark, Airflow, QuickSight, Metabase, R. Three stray tags appear once each (Google Analytics, Amplitude, Statistics) and are ignored.
   - So **Databricks, GCP, Git, statistics, A/B testing, experimentation and AI/ML/LLM/GenAI terms cannot be measured from techStack.** They are not zero; they are unmeasured. The only AI signal we have is job titles (section 1.6).
   - The tagger is whole-word with context rules (it rejects "excel at", "laws" for AWS, NoSQL for SQL, "snowflake schema"), so tags are conservative. A tag means the tool is named in the title or description.
2. **6,226 of 9,044 postings (68.8%) have at least one tag.** The other 2,818 either had no description scraped or named none of the 18 tools. Tool shares use **n = 6,226** as the denominator unless stated. Lower-bound shares over all 9,044 are given in table 1.1.
3. **Experience** is the feed's parsed level: Not Specified 3,790; Mid Level 2,623; Entry Level 1,093; Lead / Staff 973; Senior 565.
4. **Title families** are assigned by keyword rules on the title, checked in this order: BI analyst (BI, business intelligence, Power BI, Tableau, reporting, dashboard, visualisation + analyst/developer/engineer/specialist/consultant), Product analyst, Financial/risk analyst (financial, finance, FP&A, investment, credit, risk, treasury), Business analyst, Data analyst, Other. Two extra overlapping cuts across all titles: Marketing/growth (marketing, growth, CRM, customer, e-commerce) and Analytics manager/lead (manager/head/director/lead + analytics).
5. **Company concentration:** Amazon has 567 postings (6.3% of the feed) and drives almost all QuickSight tags (174 of 196), and much of the AWS/Redshift signal in the BI family (100 of 437 tagged BI postings; 98 of 836 tagged Entry Level postings). Treat QuickSight and Redshift as Amazon-specific.
6. **Duplicates:** 7,946 unique title+company pairs among 9,044 postings (same role in several cities). Shares are per posting.
7. **Country mix:** US 3,110; India 1,384; blank 761; UK 607; France 358; Canada 266; Germany 228; Poland 223. This is a global, US-heavy sample, not a census.

Reproduce: `python3 -I tools/skills_evidence/analyze.py jobs.json out.json`, where jobs.json is every row of the public feed (https://realanalystjobs.com/api/job-feed, paged 100 at a time) saved as one JSON array.

**Source B: external.** Only sources actually opened or found on 31 Oct 2026 are cited, with URL. Where I could only find secondary coverage, it says so.

---

## 1. Job-feed numbers (29 Oct 2026)

### 1.1 Overall tool share

| Tool | Postings naming it | Share of tagged (n=6,226) | Lower bound, share of all (n=9,044) |
|---|---|---|---|
| SQL | 4,355 | 69.9% | 48.2% |
| Python | 3,013 | 48.4% | 33.3% |
| Excel | 2,531 | 40.7% | 28.0% |
| Tableau | 1,966 | 31.6% | 21.7% |
| Power BI | 1,857 | 29.8% | 20.5% |
| R | 878 | 14.1% | 9.7% |
| AWS | 851 | 13.7% | 9.4% |
| Snowflake | 758 | 12.2% | 8.4% |
| Azure | 723 | 11.6% | 8.0% |
| Looker | 698 | 11.2% | 7.7% |
| dbt | 447 | 7.2% | 4.9% |
| BigQuery | 422 | 6.8% | 4.7% |
| Redshift | 279 | 4.5% | 3.1% |
| G-Sheets | 278 | 4.5% | 3.1% |
| Spark | 275 | 4.4% | 3.0% |
| QuickSight | 196 | 3.1% (Amazon 174) | 2.2% |
| Airflow | 174 | 2.8% | 1.9% |
| Metabase | 58 | 0.9% | 0.6% |
| Databricks, GCP, Git, statistics, A/B testing, AI/ML/LLM/GenAI | not in tagger vocabulary | unmeasured | unmeasured |

Grouped (n=6,226):

| Group | Postings | Share |
|---|---|---|
| SQL or Python | 4,706 | 75.6% |
| SQL and Python | 2,662 | 42.8% |
| Any BI tool (Power BI, Tableau, Looker, QuickSight, Metabase) | 2,912 | 46.8% |
| Any modern data stack tool (Snowflake, BigQuery, Redshift, dbt, Spark, Airflow) | 1,525 | 24.5% |
| Any cloud (AWS or Azure; GCP not tagged) | 1,170 | 18.8% |
| Spreadsheet only (tags are only Excel and/or G-Sheets) | 746 | 12.0% |

Number of distinct tags per tagged posting: 1 tag 1,489; 2 tags 1,310; 3 tags 1,083; 4 tags 902; 5 tags 597; 6 or more 845.

### 1.2 By experience level (share of tagged postings in each level)

| Tool | Entry Level (n=836 of 1,093) | Mid + Senior + Lead (n=3,462 of 4,161) | Senior + Lead only (n=1,259 of 1,538) | Not Specified (n=1,928 of 3,790) |
|---|---|---|---|---|
| SQL | 543 (65.0%) | 2,529 (73.1%) | 926 (73.6%) | 1,283 (66.5%) |
| Python | 395 (47.2%) | 1,741 (50.3%) | 657 (52.2%) | 877 (45.5%) |
| Excel | 489 (58.5%) | 1,267 (36.6%) | 381 (30.3%) | 775 (40.2%) |
| Power BI | 250 (29.9%) | 988 (28.5%) | 398 (31.6%) | 619 (32.1%) |
| Tableau | 266 (31.8%) | 1,205 (34.8%) | 398 (31.6%) | 495 (25.7%) |
| Looker | 89 (10.6%) | 434 (12.5%) | 157 (12.5%) | 175 (9.1%) |
| R | 136 (16.3%) | 502 (14.5%) | 156 (12.4%) | 240 (12.4%) |
| dbt | 23 (2.8%) | 318 (9.2%) | 138 (11.0%) | 106 (5.5%) |
| Snowflake | 73 (8.7%) | 532 (15.4%) | 255 (20.3%) | 153 (7.9%) |
| BigQuery | 33 (3.9%) | 261 (7.5%) | 105 (8.3%) | 128 (6.6%) |
| Redshift | 34 (4.1%) | 202 (5.8%) | 59 (4.7%) | 43 (2.2%) |
| Spark | 36 (4.3%) | 164 (4.7%) | 84 (6.7%) | 75 (3.9%) |
| Airflow | 18 (2.2%) | 116 (3.4%) | 48 (3.8%) | 40 (2.1%) |
| AWS | 92 (11.0%) | 578 (16.7%) | 247 (19.6%) | 181 (9.4%) |
| Azure | 73 (8.7%) | 448 (12.9%) | 255 (20.3%) | 202 (10.5%) |
| QuickSight | 50 (6.0%) | 114 (3.3%) | 20 (1.6%) | 32 (1.7%) |
| G-Sheets | 34 (4.1%) | 159 (4.6%) | 33 (2.6%) | 85 (4.4%) |

Read: entry roles lean on Excel (58.5% vs 36.6%) and are as Python-heavy as mid roles (47.2% vs 50.3%). The warehouse and transformation layer grows with seniority: dbt 2.8% entry to 11.0% senior+, Snowflake 8.7% to 20.3%, Azure 8.7% to 20.3%. Entry QuickSight (6.0%) is Amazon.

### 1.3 By title family (share of tagged postings in each family)

| Tool | Data analyst (n=1,034 of 1,367) | Business analyst (n=834 of 1,949) | Financial/risk analyst (n=968 of 1,330) | Product analyst (n=228 of 362) | BI analyst (n=437 of 521) | Other (n=2,725 of 3,515) |
|---|---|---|---|---|---|---|
| SQL | 865 (83.7%) | 551 (66.1%) | 502 (51.9%) | 193 (84.6%) | 335 (76.7%) | 1,909 (70.1%) |
| Python | 685 (66.2%) | 225 (27.0%) | 239 (24.7%) | 114 (50.0%) | 223 (51.0%) | 1,527 (56.0%) |
| Excel | 277 (26.8%) | 360 (43.2%) | 618 (63.8%) | 47 (20.6%) | 150 (34.3%) | 1,079 (39.6%) |
| Power BI | 405 (39.2%) | 250 (30.0%) | 269 (27.8%) | 53 (23.2%) | 215 (49.2%) | 665 (24.4%) |
| Tableau | 425 (41.1%) | 202 (24.2%) | 258 (26.7%) | 73 (32.0%) | 230 (52.6%) | 778 (28.6%) |
| Looker | 187 (18.1%) | 54 (6.5%) | 51 (5.3%) | 62 (27.2%) | 51 (11.7%) | 293 (10.8%) |
| R | 268 (25.9%) | 78 (9.4%) | 45 (4.6%) | 47 (20.6%) | 96 (22.0%) | 344 (12.6%) |
| dbt | 148 (14.3%) | 18 (2.2%) | 18 (1.9%) | 36 (15.8%) | 25 (5.7%) | 202 (7.4%) |
| Snowflake | 178 (17.2%) | 48 (5.8%) | 43 (4.4%) | 40 (17.5%) | 48 (11.0%) | 401 (14.7%) |
| BigQuery | 143 (13.8%) | 20 (2.4%) | 13 (1.3%) | 26 (11.4%) | 37 (8.5%) | 183 (6.7%) |
| Redshift | 43 (4.2%) | 16 (1.9%) | 13 (1.3%) | 12 (5.3%) | 89 (20.4%) | 106 (3.9%) |
| Spark | 118 (11.4%) | 5 (0.6%) | 17 (1.8%) | 7 (3.1%) | 15 (3.4%) | 113 (4.1%) |
| Airflow | 62 (6.0%) | 4 (0.5%) | 8 (0.8%) | 17 (7.5%) | 11 (2.5%) | 72 (2.6%) |
| AWS | 129 (12.5%) | 86 (10.3%) | 69 (7.1%) | 16 (7.0%) | 126 (28.8%) | 425 (15.6%) |
| Azure | 122 (11.8%) | 115 (13.8%) | 34 (3.5%) | 19 (8.3%) | 47 (10.8%) | 386 (14.2%) |
| QuickSight | 5 (0.5%) | 34 (4.1%) | 21 (2.2%) | 5 (2.2%) | 83 (19.0%) | 48 (1.8%) |

BI family excluding Amazon (n=337 tagged): SQL 72.7%, Power BI 59.6%, Tableau 43.9%, Python 39.8%, Excel 35.6%, Looker 15.1%, Snowflake 14.2%, AWS 13.1%, dbt 7.4%, Redshift 2.1%, QuickSight 1.2%. Use these for BI teaching, not the raw row.

"Other" (3,515 titles) is mostly operations, revenue operations, compliance, security operations, marketing, pricing, quantitative and analytics-management titles.

### 1.4 Overlapping cuts for growth and analytics-manager roles

| Tool | Marketing/growth titles (n=355 tagged of 439) | Analytics manager/lead titles (n=500 tagged of 680) |
|---|---|---|
| SQL | 298 (83.9%) | 416 (83.2%) |
| Python | 197 (55.5%) | 290 (58.0%) |
| Tableau | 175 (49.3%) | 216 (43.2%) |
| Excel | 114 (32.1%) | 130 (26.0%) |
| R | 94 (26.5%) | 121 (24.2%) |
| Power BI | 85 (23.9%) | 164 (32.8%) |
| Looker | 81 (22.8%) | 64 (12.8%) |
| Snowflake | 67 (18.9%) | 84 (16.8%) |
| dbt | 49 (13.8%) | 39 (7.8%) |
| BigQuery | 49 (13.8%) | 41 (8.2%) |

### 1.5 Most common tool combinations (n=6,226 tagged)

Pairs (postings naming both):

| Pair | Postings | Share |
|---|---|---|
| Python + SQL | 2,662 | 42.8% |
| SQL + Tableau | 1,669 | 26.8% |
| Power BI + SQL | 1,364 | 21.9% |
| Excel + SQL | 1,331 | 21.4% |
| Python + Tableau | 1,164 | 18.7% |
| Power BI + Tableau | 1,108 | 17.8% |
| Power BI + Python | 981 | 15.8% |
| Excel + Power BI | 883 | 14.2% |
| Python + R | 823 | 13.2% |
| Excel + Python | 808 | 13.0% |

Triples:

| Triple | Postings | Share |
|---|---|---|
| Python + SQL + Tableau | 1,099 | 17.7% |
| Power BI + SQL + Tableau | 938 | 15.1% |
| Power BI + Python + SQL | 902 | 14.5% |
| Python + R + SQL | 748 | 12.0% |
| Power BI + Python + Tableau | 718 | 11.5% |
| Excel + Python + SQL | 716 | 11.5% |
| AWS + Python + SQL | 504 | 8.1% |
| Looker + SQL + Tableau | 474 | 7.6% |

Exact full stacks (the posting names exactly these tools and nothing else from the vocabulary):

| Exact stack | Postings |
|---|---|
| Excel only | 677 |
| SQL only | 434 |
| Python + SQL | 389 |
| Excel + SQL | 187 |
| Excel + Power BI | 170 |
| Excel + Python + SQL | 117 |
| Python only | 117 |
| Python + R + SQL | 111 |
| Power BI only | 84 |
| Excel + Power BI + SQL + Tableau | 83 |
| SQL + Tableau | 83 |
| Excel + Power BI + Python + SQL + Tableau | 77 |
| AWS + Azure + Python + SQL | 76 |

Note: 1,108 postings name both Power BI and Tableau ("Power BI or Tableau" phrasing). Employers usually want one BI tool well, not both.

### 1.6 AI words in job titles (all 9,044 postings)

Pattern (case-insensitive, whole word): AI, A.I., ML, machine learning, LLM(s), GenAI, gen AI, generative, artificial intelligence, GPT, NLP, prompt, agentic, agent(s).

**299 of 9,044 titles (3.3%) match** (279 unique title+company pairs).

| Term | Titles |
|---|---|
| AI | 288 |
| agentic | 16 |
| ML | 15 |
| generative | 5 |
| agent | 3 |
| gen AI | 1 |
| LLM, GenAI, machine learning, prompt, copilot | 0 |

By family: Product analyst 20/362 (5.5%); Data analyst 61/1,367 (4.5%); Other 143/3,515 (4.1%); Business analyst 56/1,949 (2.9%); Financial/risk 14/1,330 (1.1%); BI analyst 5/521 (1.0%).
By level: Senior 32/565 (5.7%); Lead / Staff 50/973 (5.1%); Entry 38/1,093 (3.5%); Mid 78/2,623 (3.0%); Not Specified 101/3,790 (2.7%).
By country: US 104, India 65, blank 21, UK 17, Germany 11, Poland 9.
"Automation" appears in 72 titles.

Typical AI titles: "AI Business Analyst", "AI-Enabled Business Analyst", "Data & AI Strategy Analyst", "Manager, Data Analytics - AI Enablement", "AI Product Analyst". Most are business-analysis or strategy roles around AI adoption, not model-building roles.

Other title signals (all 9,044): "operations" 782; "manager/lead/head/director" 1,315; "reporting" 205; "insights" 154; "data quality/governance" 76; "data scientist" 53; "SQL" 43; "Python" 27; "experiment/A/B" 10; "statistic" 2; "analytics engineer" 0.

**Title share is a floor, not the AI demand rate.** Indeed Hiring Lab measures AI terms in full descriptions and finds about 45% of data and analytics postings mention them (section 2). Our 3.3% only counts roles that put AI in the title. A description-level AI tag is the single most useful addition to our tagger before the next run.

---

## 2. External evidence found (accessed 31 Oct 2026)

| # | Source | What it says (only figures I saw) | URL |
|---|---|---|---|
| E1 | US BLS OOH, Data Scientists | 35% employment growth 2025-2035; median pay $120,230 (May 2025); 275,600 jobs (2025); about 24,800 openings a year | https://www.bls.gov/ooh/math/data-scientists.htm |
| E2 | US BLS OOH, Operations Research Analysts | 12% growth 2025-2035; median $88,940 (May 2025); 113,100 jobs; about 7,500 openings a year | https://www.bls.gov/ooh/math/operations-research-analysts.htm |
| E3 | US BLS OOH, Management Analysts | 10% growth 2025-2035; median $101,860 (May 2025); 1,077,100 jobs; about 94,100 openings a year | https://www.bls.gov/ooh/business-and-financial/management-analysts.htm |
| E4 | US BLS OOH, Financial Analysts | 7% growth 2025-2035; median $103,570 (May 2025); 443,100 jobs; about 29,500 openings a year | https://www.bls.gov/ooh/business-and-financial/financial-analysts.htm |
| E5 | Indeed Hiring Lab, January 2026 labor market update (22 Jan 2026) | Indeed AI Tracker hit 4.2% of all US postings in Dec 2025; as of Dec 2025, 45% of data & analytics postings mentioned AI, the highest of any sector analyzed (still a minority); marketing 14.9%, HR 8.8%, accounting about 6% | https://hiringlab.indeed.com/2026/01/22/january-labor-market-update-jobs-mentioning-ai-are-growing-amid-broader-hiring-weakness/ |
| E6 | Indeed Hiring Lab, Feb 2025 (via search result summary) | US postings mentioning GenAI terms rose 170% Jan 2024 to Jan 2025; software, data science and related roles dominate. GenAI terms were below 0.3% of postings in several countries in Jan 2025 | https://www.hiringlab.org/2025/02/27/ai-at-work-rise-of-the-genai-consultant/ and https://www.hiringlab.org/en-ca/2025/02/12/genai-still-rarely-mentioned-in-white-collar-job-postings/ (summaries; not opened in full) |
| E7 | dbt Labs, 2026 State of Analytics Engineering (14 Apr 2026, n=363) | 72% prioritise AI-assisted coding; only 24% prioritise AI-assisted pipeline management (testing, observability); 71% cite incorrect or hallucinated outputs reaching stakeholders as a top concern; trust as a priority rose 66% to 83%; 41% blocked by ambiguous data ownership | https://www.getdbt.com/blog/new-dbt-labs-report-finds-ai-driven-acceleration-is-outpacing-trust-and-governance |
| E8 | Stack Overflow Developer Survey 2025 (AI section) | 84% use or plan to use AI tools; 47.1% daily; 45.7% distrust AI accuracy vs 32.7% trust; 66% cite answers that are almost right but not quite; 30.9% use AI agents at work; 24.9% of agent users apply them to data and analytics | https://survey.stackoverflow.co/2025/ai |
| E9 | Stack Overflow Developer Survey 2026 (published 6 Oct 2026, 30,000+ respondents) | 66% of AI users use coding agents, 63% chatbots; 73% of assistant/agent users use them daily; 93% say source attribution is needed to trust AI output; SQL now second most used language (SQL, HTML/CSS and Python each about 58%) | https://stackoverflow.blog/2026/10/06/the-results-of-the-2026-developer-survey-are-here/ |
| E10 | LinkedIn Skills on the Rise 2026 (secondary coverage only; primary not verified) | Postings requiring AI literacy reportedly grew over 70% year over year; LinkedIn does not publish the base share | https://finance.yahoo.com/news/ai-engineering-tops-list-demand-160600138.html and https://ppc.land/linkedin-members-with-ai-literacy-skills-78-more-likely-to-be-hired/ |
| E11 | WEF Future of Jobs Report 2025 (7 Jan 2025) | AI and big data are the fastest-growing skills to 2030, then networks/cybersecurity and technology literacy; growth skills pair tech with human skills such as cognitive skills and collaboration | https://www.weforum.org/press/2025/01/future-of-jobs-report-2025-78-million-new-job-opportunities-by-2030-but-urgent-upskilling-needed-to-prepare-workforces/ |
| E12 | Anthropic Economic Index (10 Feb 2025) | 37.2% of Claude queries in computer and mathematical tasks; 57% augmentation vs 43% automation; about 36% of occupations used AI for at least 25% of their tasks; data scientists named among heavy users (data analysts not named) | https://www.anthropic.com/news/the-anthropic-economic-index |
| E13 | Spider 2.0 paper (ICLR 2025, v2 17 Mar 2025) | 632 enterprise text-to-SQL workflow tasks; best agent (o1-preview) solved 21.3%, vs 91.2% on Spider 1.0 and 73.0% on BIRD | https://arxiv.org/abs/2411.07763 |
| E14 | Spider 2.0 leaderboard (read 31 Oct 2026; entries undated, self-submitted) | Top Spider 2.0-Snow 96.70; Spider 2.0-Lite 76.23; Spider 2.0-DBT 65.6 | https://spider2-sql.github.io/ |
| E15 | Model Context Protocol docs | MCP is an open-source standard for connecting AI applications to external systems, including databases; supported by Claude, ChatGPT, VS Code, Cursor | https://modelcontextprotocol.io/docs/getting-started/intro |
| E16 | dbt Semantic Layer docs | Defines metrics once in the modeling layer so every tool uses the same definition; AI tools like Claude and ChatGPT can connect through the dbt MCP server so answers use governed metrics | https://docs.getdbt.com/docs/use-dbt-semantic-layer/dbt-sl |
| E17 | Microsoft Learn, Copilot for Power BI (updated Aug 2026) | Copilot creates reports, writes DAX, summarises reports, adds measure descriptions; "prepare your semantic model" for AI or Copilot can misinterpret data | https://learn.microsoft.com/en-us/power-bi/create-reports/copilot-introduction |
| E18 | Looker docs, What is LookML | LookML is the language used in Looker to create semantic data models; Looker generates SQL from the model | https://docs.cloud.google.com/looker/docs/what-is-lookml |
| E19 | Anthropic tool use docs | Tool use lets Claude call functions you define and return a structured call; `strict: true` guarantees schema conformance | https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview |
| E20 | OpenAI Structured Outputs docs | Structured Outputs make the model's response adhere to a supplied JSON Schema | https://developers.openai.com/api/docs/guides/structured-outputs |

Not found or not used: no BLS occupation called "data analyst" or "business analyst" exists in the OOH, so E1 to E4 are the nearest proxies. No primary LinkedIn Economic Graph figure for analyst roles. No official Anthropic Economic Index figure for data analysts.

---

## 3. Skills matrix

Roles: **DA** data analyst, **BA** business analyst, **PA** product analyst, **BI** BI analyst, **GA** growth/marketing analyst, **AM** analytics manager. Financial analyst numbers are shown where they differ, since that family is 15% of the feed.

Evidence strength: **Strong** = our feed share and/or a primary external source; **Medium** = vendor docs or survey of practitioners, not hiring data; **Weak** = little or no hiring evidence.

### Tier 1. Essential now (employers name it today)

| Skill | Evidence | Strength | Roles |
|---|---|---|---|
| SQL (joins, aggregation, window functions, CTEs, reading other people's queries) | 69.9% of tagged postings (4,355/6,226); 83.7% DA, 84.6% PA, 83.9% GA, 83.2% AM, 76.7% BI, 66.1% BA, 51.9% financial; 65.0% even at entry. SO 2026: SQL is now the 2nd most used language (E9) | Strong | All six |
| Spreadsheets (Excel; Google Sheets less often) | 40.7% overall; 58.5% of entry postings; 63.8% of financial, 43.2% of BA. Excel-only is the most common exact stack (677) | Strong | BA, financial, entry DA, AM; less for PA (20.6%) |
| One BI tool in depth (Power BI or Tableau; Looker for product/growth) | Any BI tool 46.8% (2,912/6,226). Power BI 29.8%, Tableau 31.6%. BI family (excl. Amazon) Power BI 59.6%; India Power BI 39.0% vs US 24.3%; GA Tableau 49.3%; PA Looker 27.2% | Strong | BI, DA, GA, AM; BA and PA moderate |
| Python for analysis (pandas, notebooks, basic scripting) | 48.4% overall; 66.2% DA, 50.0% PA, 51.0% BI, 55.5% GA, 58.0% AM; 27.0% BA, 24.7% financial. Entry 47.2% vs mid+ 50.3%: entry roles already ask for it | Strong | DA, PA, GA, AM, BI; optional for BA and financial |
| SQL + Python together | 42.8% name both (2,662). Most common pair | Strong | DA, PA, GA, AM |
| Metric definition and business framing (what is counted, why, for whom) | Not measurable with our tagger. External: dbt 2026 says trust is the top rising priority (66% to 83%) and 41% are blocked by ambiguous ownership (E7); Power BI says Copilot misreads unprepared models (E17) | Medium (no hiring count) | All; central for BA, PA, AM |
| Statistics fundamentals and experiment reading (distributions, confidence intervals, A/B tests) | **Evidence gap**: not in our tagger vocabulary; only 10 titles say experiment/A/B and 2 say statistic. R (a stats-heavy proxy) is 14.1% overall, 25.9% DA, 26.5% GA, 20.6% PA. Kept in Tier 1 for PA/GA on curriculum judgment, flagged for a description-level re-check | Weak in our data | PA, GA, DA; lighter for BA/BI |
| Communication of findings to non-technical people | WEF 2025: growth skills pair technology with human skills (E11). Our feed cannot measure soft skills | Medium (survey of employers) | All; AM most |

### Tier 2. Emerging (rising, with evidence)

| Skill | Evidence | Strength | Roles |
|---|---|---|---|
| Cloud warehouse querying (Snowflake, BigQuery; Databricks unmeasured) | Snowflake 12.2% overall, rising from 8.7% entry to 20.3% senior+; DA 17.2%, PA 17.5%, GA 18.9%. BigQuery 6.8%, UK 10.2% | Strong (cross-section, not a time series) | DA, PA, GA, AM, BI |
| dbt / analytics-engineering basics (version-controlled SQL models, tests) | dbt 7.2% overall; 2.8% entry to 11.0% senior+; DA 14.3%, PA 15.8%, GA 13.8%. dbt 2026: only 24% prioritise AI for testing/observability (E7), so testing skill is scarce | Strong for senior DA/PA; low for entry | DA, PA, GA, AM |
| Semantic layer and governed metrics (dbt Semantic Layer, LookML, Power BI semantic models) | Vendor docs now position the semantic layer as what AI tools query (dbt via MCP, E16; Power BI "prepare data for AI", E17; LookML, E18). Looker named in 11.2% overall, 27.2% PA. No direct hiring count for "semantic layer" | Medium | BI, DA, PA, AM |
| Cloud platforms (AWS, Azure) | AWS 13.7%, Azure 11.6% overall; Azure 20.3% senior+; India AWS 19.8%, Azure 18.3% | Strong (but Amazon inflates AWS) | BI, DA, BA (Azure 13.8%), AM |
| AI-assisted analysis with verification (using an assistant to draft SQL/Python, then checking it) | Indeed: 45% of data & analytics postings mention AI (E5). dbt: 72% prioritise AI-assisted coding (E7). SO 2025: 66% hit almost-right answers, 45.7% distrust accuracy (E8). Our titles: 3.3% (299/9,044), so title-level demand is still small | Strong external, weak in our titles | All |
| Data quality checks and reconciliation | dbt: 71% name hallucinated outputs reaching stakeholders a top concern (E7). 76 titles name data quality/governance | Medium | DA, BI, AM |
| AI-adoption business analysis (requirements, process mapping, evaluation for AI features) | Most of our 299 AI titles are BA/strategy roles ("AI Business Analyst", "AI Enablement"). PA 5.5% and senior 5.7% of titles mention AI | Medium (small n) | BA, PA, AM |

### Tier 3. Experimental (worth exploring, little hiring evidence yet)

| Skill | Evidence | Strength | Roles |
|---|---|---|---|
| MCP: connecting an AI assistant to a database or semantic layer | MCP is an open standard supported by Claude, ChatGPT, VS Code, Cursor (E15); dbt ships an MCP server for the Semantic Layer (E16). Zero titles in our feed; not in tagger | Weak hiring, strong tooling | DA, BI, AM |
| LLM structured outputs and tool use for analysis tasks (classifying free text into a fixed schema, extracting fields) | Documented by Anthropic (strict tool use, E19) and OpenAI (JSON Schema adherence, E20). No hiring count | Weak hiring | DA, GA, PA |
| Agentic analysis workflows (agent writes and runs queries, analyst reviews) | SO 2025: 30.9% of developers use agents at work, 24.9% of agent users apply them to data and analytics (E8). 16 titles in our feed say "agentic" | Weak | DA, AM |
| Text-to-SQL evaluation (checking whether an AI-written query answers the question) | Spider 2.0 best was 21.3% in Mar 2025 (E13); leaderboard tops now 96.70 Snow, 76.23 Lite, 65.6 DBT (E14). Entries are self-submitted and undated, so treat as direction, not a guarantee on your data | Medium (benchmarks, not jobs) | DA, BI, AM |
| Orchestration (Airflow) and Spark for analysts | Airflow 2.8%, Spark 4.4% overall (Spark 11.4% DA). Niche: belongs to data engineering more than analysis | Strong evidence that it is niche | DA (large-data teams) only |

### Tier 4. Less differentiating because of AI automation

These are not "do not learn". An analyst must still read, check and fix this work. The claim is only that doing it by hand from memory is becoming less of a hiring differentiator. Each line gives the reason, and says where it is my inference.

| Skill | Reasoning and evidence | What to teach instead |
|---|---|---|
| Writing routine SQL from a blank page, syntax memorisation | SQL is still the top requirement (69.9%), so SQL literacy stays essential. But AI drafting is now mainstream among practitioners (dbt 72%, E7) and benchmark success on enterprise text-to-SQL rose from 21.3% (E13) to self-reported 96.70 on one variant (E14). Inference: the value moves from typing queries to specifying, reading and verifying them | Query review: grain, join fan-out, NULLs, filters, reconciliation to a known total |
| Building standard charts and first-draft dashboards | Power BI Copilot creates and edits report pages and summaries (E17). Our feed still asks for BI tools in 46.8%, so the tool remains a requirement. Inference: layout labour shrinks; deciding what to show does not | Dashboard design for a decision, metric definitions, the semantic model underneath |
| Writing DAX/LookML/measure descriptions and documentation by hand | Copilot writes DAX and adds measure descriptions (E17); Looker docs list natural-language LookML authoring in navigation (E18, not verified in body) | Modelling choices and naming that an AI can read correctly |
| Excel formula recall (VLOOKUP/XLOOKUP, pivots) as a standalone skill | Excel remains common (40.7%; 58.5% entry; 63.8% financial), so this is not obsolete. Inference only: assistants handle formula syntax; spreadsheet modelling judgment is what remains scarce | Building auditable models, checking assumptions |
| Summarising a report in prose | Power BI Copilot summarises reports and adds summaries to subscriptions (E17). Inference: the first draft is cheap; the "so what" and the recommendation are not | Writing the recommendation and the caveat |

---

## 4. AI in analyst work: what is established vs speculative

**Established (measured by someone):**
1. Employers mention AI in a large minority of data job ads: 45% of data & analytics postings on Indeed in Dec 2025, the highest sector (E5). Across all US postings it is 4.2% (E5).
2. Analysts' titles have barely changed: 3.3% of our 9,044 titles contain an AI word, mostly "AI" and mostly in BA/strategy roles. LLM and GenAI appear in zero titles (section 1.6).
3. Practitioners already use AI to write analytics code: 72% of dbt's respondents prioritise AI-assisted coding (E7); 84% of developers use or plan to use AI tools (E8).
4. Trust is the bottleneck, not access: 71% fear hallucinated outputs reaching stakeholders (E7); 45.7% of developers distrust AI accuracy and 66% hit almost-right answers (E8); 93% need source attribution to trust output (E9).
5. Vendors are routing AI through semantic layers: dbt (via MCP), Power BI Copilot and Looker all tie AI answers to a governed model (E16, E17, E18).
6. The core stack has not changed: SQL, a spreadsheet, a BI tool and Python cover the large majority of tagged postings (SQL or Python 75.6%; any BI tool 46.8%).

**Speculative (plausible, not yet measured in hiring):**
1. That AI will cut analyst headcount. BLS still projects growth for every proxy occupation through 2035 (data scientists 35%, operations research 12%, management 10%, financial 7%; E1 to E4). These projections may not fully price in AI.
2. That benchmark text-to-SQL scores transfer to messy company data. Leaderboard entries are self-submitted and undated (E14).
3. That MCP or agent skills will become hiring requirements for analysts. Strong tooling support (E15, E16), almost no hiring signal (16 "agentic" titles).
4. That "AI literacy" job requirements grew 70% (E10): secondary coverage only, no base rate.
5. Exactly which tasks AI automates for analysts. The Anthropic Economic Index found 57% augmentation vs 43% automation across all usage and named data scientists, not data analysts (E12).

---

## 5. Shared vs role-specific skills

**Shared core (teach once, to everyone):**
- SQL (51.9% to 84.6% across every family).
- Spreadsheet fluency (20.6% to 63.8%; highest at entry level).
- One BI tool (any BI tool 46.8% overall).
- Metric definition, data quality checks, and verifying AI-drafted work (dbt E7, SO E8/E9).
- Explaining findings and recommendations to non-technical people (WEF E11).

**Role-specific (the modules that differ):**

| Role | What sets it apart in the evidence |
|---|---|
| Data analyst | Highest Python (66.2%) and R (25.9%); most warehouse/engineering exposure: Snowflake 17.2%, dbt 14.3%, BigQuery 13.8%, Spark 11.4% |
| Business analyst | Lowest Python (27.0%); Excel 43.2%; Azure 13.8%; leads the AI-title roles (56 titles: requirements and process work for AI adoption). Requirements, process mapping and stakeholder work are core but not measurable by our tagger |
| Product analyst | SQL 84.6% (highest); Looker 27.2% (highest); dbt 15.8%; R 20.6%; highest AI-title share (5.5%). Experimentation is the expected specialism, but our tagger cannot count it |
| BI analyst | Power BI 59.6% and Tableau 43.9% (excl. Amazon); semantic models and governed metrics are where AI tools plug in (E16, E17) |
| Growth / marketing analyst | SQL 83.9%, Tableau 49.3%, Looker 22.8%, R 26.5%, BigQuery 13.8%: product-style stack plus attribution and experiments |
| Analytics manager | SQL 83.2% and Python 58.0%, so managers are still hands-on; Power BI 32.8%, Tableau 43.2%; plus team-level AI governance and data ownership (dbt E7: 41% blocked by unclear ownership) |
| Financial analyst (for reference) | Excel 63.8% (highest); SQL 51.9% (lowest); Python 24.7%; almost no warehouse tools (dbt 1.9%) |

**Seniority gradient (all roles):** entry roles weight Excel and SQL, and already ask for Python; senior roles add the warehouse and transformation layer (Snowflake 20.3%, dbt 11.0%, Azure 20.3% at senior+).

---

## 6. Gaps to close before the next refresh

1. Add description-level tags for AI/LLM/GenAI, statistics/A-B testing, Databricks, GCP and Git to the tagger, then rerun. Today these are unmeasured, not absent.
2. Re-pull this snapshot monthly to turn the seniority cross-section into a real trend.
3. Try to verify LinkedIn's AI-literacy figure (E10) from a primary LinkedIn source before quoting it in course material.
