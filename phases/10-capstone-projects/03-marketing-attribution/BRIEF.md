# Brief: next quarter's marketing budget

The request below is how a stakeholder would send it. It is part of capstone [10-03](README.md). Brambletoe and everyone in it are fictional, and the data is synthetic.

---

**From:** Sana Mirza, CFO, Brambletoe
**To:** you (analyst)
**Cc:** Daniel Okoro (head of marketing)
**Date:** Monday 12 October 2026
**Subject:** Q4 paid budget, decision on Thursday 22 October

Hi,

We are keeping next quarter's paid media budget the same as Q3's in total. The question is how to split it between paid search, paid social and display.

Our display agency sent their Q3 report. On their numbers display has the lowest cost per order of any paid channel, and they propose moving a third of the search budget into display. Daniel is inclined to agree. I am not convinced: their report gives display credit for every order where display was the last ad someone saw, and plenty of those people were coming back to buy anyway.

Daniel's team ran a holdout test on display in August: a random half of a test audience saw no display ads for four weeks. I have not seen anyone read it properly.

What I need by Tuesday 20 October:

1. A split of the Q4 paid budget across the three channels that you would defend in the meeting, and what it should do to orders.
2. Why that split and not the agency's. I will be asked "which attribution model did you use and why should we trust it?"
3. How sure you are, and what we should measure in Q4 so that the Q1 budget is easier.

Constraints: email stays as it is (it is a fixed platform fee). Daniel will not accept moving any channel by more than half of its Q3 spend in one quarter.

Thanks,
Sana

---

## Notes from the data team

Joseph, the marketing analyst, sent these with the export of **12 October 2026**.

- Brambletoe plans in 13-week quarters. Q3 2026 is the 13 weeks starting Monday 29 June 2026, so 29 June to 27 September.
- `spend.csv`: weekly spend per channel, from each platform's export. The exports overlapped, so some weeks may be there twice. Display spend changed meaning from the week starting **17 August 2026**: before it, the agency reported media cost only, **excluding** its 15% fee; from that week, spend **includes** the fee. Finance counts spend including the fee. Email is a fixed fee of Rs 8,000 a week.
- `touchpoints.csv`: every ad click or view and every email open we can tie to a user, with its time. It includes emails sent after a purchase (order confirmations and follow-ups) and some old touches.
- `orders.csv`: one row per order event from the website pixel. The pixel sometimes fires twice for one order. `loaded_at` is when the row reached the warehouse; some arrive days late. The file includes orders from just before and just after Q3.
- Marketing's attribution rule: a touch can get credit for an order if it happened in the 30 days up to and including the order time.
- `display_test.csv`: the August holdout test. Every user in a test audience was randomly put in `exposed` (display ads as usual) or `holdout` (no display ads) for 3 to 30 August 2026. Their orders are in `orders.csv` like everyone else's.
