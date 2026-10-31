# Brief: the CEO dashboard

The request below is how a stakeholder would send it. It is part of capstone [10-05](README.md). Kettlemoor and everyone in it are fictional, and the data is synthetic.

---

**From:** Hannah Okoro, CEO, Kettlemoor
**To:** you (analyst)
**Date:** Friday 2 October 2026
**Subject:** One dashboard for the leadership meeting, by Wednesday 7 October please

Hi,

Every month the four shop managers, our finance lead and I spend the first half hour of the leadership meeting arguing about which spreadsheet is right. I want one dashboard that everyone opens, with numbers we stop arguing about. September is the first month it should cover; the meeting is Wednesday 7 October.

What I need on it:

1. How the month went against target, for the business and for each shop, and whether I need to worry.
2. Are we actually growing? Last month's spreadsheet said "+23% on last year" and the York manager said that cannot be right for her shop.
3. Margin. Our flour and butter costs went up in the spring and I want to see where it is hurting.
4. A trend, so a bad month does not look like a disaster or a good one like a miracle.

Use whatever tool you like. We pay for Power BI, but Leila in finance says half the team cannot open it on their phones, so a picture that works anywhere is fine too. What matters to me is that the numbers are right, the same every time, and that you tell me when something is missing.

Thanks,
Hannah

---

## Notes from the data team

Sam, who looks after the till system exports, sent these with the files.

- The export was taken on **2 October 2026** and covers **1 September 2025 to 30 September 2026**. Four files: `daily_sales.csv`, `stores.csv`, `store_closures.csv`, `targets.csv`.
- `daily_sales.csv` has one row per shop and day **as sent by the till**. A shop sometimes sends a day again after the evening till count, and the later send (`loaded_at`) is the right one. Most re-sends are identical; some carry corrected numbers.
- **Definition change.** We moved to new till software on **1 July 2026**. Before that, `gross_sales` is before discounts and net revenue is `gross_sales - discounts`. From 1 July, `gross_sales` is already **after** discounts; the `discounts` column is still filled in for information only. Finance reports net revenue (after discounts). Prices include no tax in either system.
- `cogs` is the cost of the ingredients and packaging sold that day. It is not affected by the till change. Gross margin is net revenue minus cogs.
- Shops: York (opened 2019), Harrogate (2021), Leeds (2023), and Ripon, which opened on **2 March 2026**. Leeds was shut for a refit from 8 to 14 September 2025; that is in `store_closures.csv`.
- The York till failed to send one day in September 2026. I am chasing it with the till supplier; it is not in this export.
- `targets.csv` holds the 2026 monthly net revenue target per shop, from the budget set in January. Ripon's targets start the month it opened.
