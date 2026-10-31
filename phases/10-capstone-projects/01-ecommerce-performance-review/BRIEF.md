# Brief: the Q3 2026 quarterly business review

The request below is how a stakeholder would send it. It is part of capstone [10-01](README.md). Pottlemere and everyone in it are fictional, and the data is synthetic.

---

**From:** Anjali Rao, CEO, Pottlemere
**To:** you (analyst)
**Date:** Monday 26 October 2026
**Subject:** Q3 QBR, numbers by Monday 2 November please

Hi,

The quarterly business review with the board is on Thursday 5 November. I need the Q3 pack from you by Monday 2 November so I can read it before the pre-read goes out.

What I need to be able to say:

1. How Q3 (July to September) went against Q2: revenue, orders, customers, basket. One table I can trust.
2. What drove it. The board will ask "why", not just "how much".
3. The August question. The dashboard shows August revenue down about 15% on July. Our board member Rohit thinks the new checkout platform we moved to on 1 August is losing sales and wants us to roll back to the old one. I need a straight answer: did the platform hurt sales, yes or no, and how sure are you?
4. What we should focus on in Q4. One or two things, not ten.

Last quarter the Q2 numbers in the pack changed after the meeting, which was embarrassing. If anything in Q2 has moved since we reported it, tell me by how much and why, before the board finds it.

Thanks,
Anjali

---

## Notes from the data team

Vikram, the data engineer, sent these with the export.

- The three files are the raw warehouse tables as of the export on **26 October 2026**: `orders.csv`, `refunds.csv`, `customers.csv`. Each row is one load: the nightly job writes a row when a record arrives and writes it again when the source system sends it again (for example when an order's status changes). Nobody has cleaned them.
- Orders: `status` is `completed` or `cancelled`. Only completed orders are sales.
- Checkout platform: until 31 July 2026 orders went through the `legacy` platform; from 1 August through `v2`. On legacy, `amount` was stored **including** tax. On v2, `amount` is stored **excluding** tax. This data uses a flat tax rate of 12%, a made-up rate for this exercise. Finance reports revenue excluding tax.
- Refunds: `refund_amount` always excludes tax. Finance counts a refund in the quarter it was paid (`refund_date`), not the quarter of the order.
- Customers: synced from the CRM. The sync sometimes sends a customer twice, and a few customers never arrived. `acquisition_channel` is where the customer first came from: `search`, `social` (paid social ads) or `referral`.
- The Q2 pack was built from the warehouse as it stood on **3 July 2026** (rows with `loaded_at` on or before that date).
- Marketing paused paid social ads for Q3 to save budget. We do not have ad spend in this export.
- Pottlemere opened on 1 January 2026, so the export holds the whole history.
