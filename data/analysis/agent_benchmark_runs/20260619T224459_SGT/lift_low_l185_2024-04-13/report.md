Now I have a comprehensive picture. Let me compile the report.

---

# Root Cause Analysis Report

## 1. Trigger

**Signal:** Lift (trailing 7-day +54.3%, day-over-day +38.4%)  
**Store:** l185 | **Date:** 2024-04-13 (Saturday)  
**Current Sales:** $49.40  
**Trailing 7-day Average:** $32.03  
**Previous Day (Friday) Sales:** $35.70  

The signal is a **strong lift**. Sales are well above both the recent trailing average and the immediate prior day.

## 2. Likely Drivers

- **Promotional activity** is the most plausible primary driver. Nearly half of sales (48.4%) came from promoted products, and 36.6% of all products were on some form of promotion.
- **Moderate discounting** (avg. discount ~8%, with 46.3% of products discounted) supports the activity-driven explanation, though no deep discounts were applied.
- **Weekend effect** (Saturday) may have contributed a modest natural lift, but the prior Saturday (2024-03-30) had sales of only $33.9, suggesting the weekend alone cannot explain the magnitude.
- **Stockouts are elevated** (68.3% of products had stockout hours, avg. 5.85 hours out-of-stock), but this is likely a **consequence** of higher-than-normal sales drawing down inventory, rather than a cause of the lift.

## 3. Evidence

| Evidence Source | Finding | Interpretation |
|---|---|---|
| **Signal & Sales History** | Sales $49.4 vs 7d avg $32.03 (+54%). Prior Saturdays: 2024-03-30 = $33.9, 2024-04-06 = $41.5 (both lower). | Clear upward break from recent pattern; Saturday alone cannot explain the full gap. |
| **Discounts** | Avg discount 0.9209 (~8% off); 46.3% of products discounted; no deep discounts. | Moderate discount breadth, not aggressive price-cutting. |
| **Activity (Promotions)** | 36.6% of products on promo; **48.4% of sales** from promoted products. | Strong promotional-pull: nearly half of revenue came from promoted items. |
| **Stockouts** | 68.3% of products saw stockout; avg 5.85 hrs out-of-stock; severe stockouts on 39% of products. | Elevated stockout levels are unusually high. Most consistent with inventory being depleted by strong demand rather than being a cause. |
| **Peer comparison** | Ranked #1 in its L-tier (5 stores, avg $40.06); #11 out of 15 overall (avg $116.82). | l185 outperformed its tier peers substantially (+23% vs tier avg), but is a small store overall. |
| **Calendar / Weather** | Saturday (weekend); light rain (2.18mm precip); mild temp 18.4C. | Weather is unremarkable — not likely a driver or detractor. |
| **Prior weekend (Apr 6) comparison** | Same promo rate ~34%, discount rate ~39%, but activity sales share was only 34.5% (vs 48.4% on Apr 13). | The promotion on Apr 13 was **more effective** at converting promoted sales, or the promotion mix shifted. |

**Causal inference:** The evidence is most consistent with a **promotional push** that succeeded in driving incremental demand. The combination of 48.4% of sales coming from promoted products, a higher activity-to-sales conversion than the prior Saturday, and a 23% outperformance versus tier peers, all point to promotional effectiveness as the root cause.

**Stockout counter-evidence:** The high stockout rate (68% of products) might seem problematic, but in the context of a sales lift, it is better interpreted as demand-driven depletion. If stockouts had caused the lift (e.g., customers panic-buying due to perceived scarcity), we would expect a different pattern. The data cannot support that causal direction without additional checks.

## 4. Caveats

- **No same-weekday-4w baseline** was available, so we cannot compare to the exact same weekday from 4 weeks prior. The comparison relies on the trailing 7-day average and the prior Saturday (Mar 30).
- **Discount depth is unknown in granular detail.** The average discount of ~8% is moderate, but without knowing which categories or SKUs were discounted, we cannot say whether the lift came from a few high-volume items or broad-based promotion.
- **Stockout evidence is ambiguous.** While likely a consequence, it is possible that some stockouts on high-demand items constrained what would have been even higher sales. We cannot measure lost sales from stockouts with the current data.
- **Peer context** shows l185 is a small store (#11 of 15 overall); the tier outperformance is notable but the absolute sales ($49.40) is still modest versus the overall average ($116.82).

## 5. Suggested Next Checks

1. **Category / SKU-level drill-down** — Identify which product categories or specific SKUs drove the lift (especially among promoted items) to confirm whether this was a targeted promotion or broad-based.
2. **Compare the promotion calendar** — Check whether 2024-04-13 coincided with a specific event or marketing campaign (e.g., seasonal push, new product launch, local event) that triggered the promotional activity.
3. **Stockout impact analysis** — Examine whether the most-stocked-out items were the best-sellers, and whether the stockouts began later in the day (consistent with demand depletion) or early (consistent with supply failure).
4. **Repeat check on next Saturday (2024-04-20)** — Determine if the lift persists, which would indicate a sustained change (e.g., new pricing, new traffic driver) vs. a one-off promotional spike.