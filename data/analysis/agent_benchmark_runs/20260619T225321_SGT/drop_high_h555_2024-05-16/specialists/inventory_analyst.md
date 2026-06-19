Now I have a thorough picture. Here is the memo.

---

## 1. Scope

**Store:** h555  
**Date:** 2024-05-16 (Thursday, normal weekday)  
**Assessment focus:** Inventory availability — stockout rates, severity, and whether inventory problems can explain the observed sales shortfall.

---

## 2. Findings

### Sales Performance
- **Actual sales:** $131.91
- **Trailing 7d avg:** $175.63 — a **-24.9%** gap
- **Previous day (Wed 05/15):** $154.43 — a **-14.6%** day-over-day drop
- **Same-weekday 4-week avg:** $151.03 — a **-12.7%** gap vs that baseline
- **Prior Thursday (05/09, normal weekday):** $160.00 — a **-17.6%** drop
- **Prior Thursday (05/02, Labor Day period):** $126.23 — the only Thursday that was lower, but that date fell in a holiday-adjacent period which may depress sales patterns.

**Bottom line:** Sales are well below the recent trailing average and below the comparable Thursday baseline. The shortfall relative to the 7d trailing avg is the most striking (~$44 / ~25% below normal mid-week levels).

### Stockout & Availability Metrics

| Metric | Value | Interpretation |
|---|---|---|
| **Avg stockout hours** | 2.96 hrs | Nearly 3 hours of the selling day had at least some products unavailable. |
| **Stockout product rate** | 36.7% | Over **1 in 3 products** experienced some stockout during the day. |
| **Severe stockout rate** | 17.7% | Nearly **1 in 5 products** stockout for a material fraction of the day. |
| **Full stockout rate** | 4.1% | ~4% of products were entirely absent for the full day. |
| **Hourly stockout peak** | 34.0% | At the worst hour, more than a third of SKUs were unavailable simultaneously. |

These are **elevated stockout metrics**. A severe stockout rate of ~18% and a peak-hour unavailability of 34% indicate meaningful availability pressure on the sales floor.

### Cause vs. Consequence Ambiguity

There are two plausible directions of causality, and the available data cannot fully disentangle them:

1. **Inventory → Sales (the "stockout drag" hypothesis):** With ~37% of products hitting stockout at some point, and nearly 18% in severe stockout, customers are facing empty shelves or limited selection. This likely depresses conversion and basket size — some customers walk away, substitute down, or buy fewer items. The magnitude of the sales drop (~25% vs trailing avg) is directionally consistent with the breadth of stockouts.

2. **Sales → Inventory (the "low-demand" hypothesis):** If Thursday is genuinely a lower-traffic day (the same-weekday 4w avg of $151 is already below the trailing 7d avg of $176), some of the stockout metrics could reflect slower replenishment cycles rather than a root-cause inventory failure. However, the day-over-day drop from Wednesday ($154 → $132, -14.6%) and the drop versus the prior Thursday ($160 → $132, -17.6%) argue that this is not just a normal Thursday pattern — something changed.

### Key Signals

| Signal | Detail |
|---|---|
| **Deteriorating trend** | Sales have declined each of the last 3 days ($168 → $167 → $154 → $132). Stockouts may be worsening as the week progresses. |
| **Week-over-week Thursday decline** | Prior Thursday (05/09) = $160; current = $132. That's $28 / 17.5% lower. |
| **Holiday note** | 05/02 (the other Thursday in the window) was Labor Day period ($126) — that's a suppressed baseline, so not directly comparable. |
| **Inventory as explanatory factor** | Stockout metrics are high enough to be **material** — a ~37% SKU hit rate and nearly 3 hours of unavailability would plausibly cause a meaningful sales hit. |

---

## 3. Caveats

- **Correlation vs. causation is not resolved.** High stockout metrics and low sales co-occur, but without item-level substitution or shopper intercept data, we cannot prove stockouts *caused* the sales decline vs. stockouts being a symptom of an underlying operational or demand issue.
- **No product-category breakdowns** are available in the current data. It is possible the stockouts are concentrated in high-velocity or high-margin categories, which would amplify the sales impact, or in slow movers, which would diminish it.
- **The same-weekday 4-week avg ($151)** is the most appropriate baseline (controls for day-of-week patterns) but still includes the Labor Day period (05/02 Thursday at $126) which may pull the average lower, making the current $132 look closer to normal than it actually is.
- **No competitor or foot-traffic data** — could be external demand factors (e.g., a nearby event, roadwork, competitor promotion) depressing traffic regardless of inventory health.
- **No replenishment timing data** — it's unclear whether stockouts are a morning replenishment gap (recoverable later in day) or a chronic mid-week inventory position problem.

**Bottom-line opinion:** Inventory availability is **likely a contributing factor** to the sales weakness on 05/16. The stockout rates are high enough to be operationally concerning, and the sales pattern (declining through the week, with a Thursday that underperforms both the prior Thursday and the trailing average) is consistent with a store that is losing sales to empty shelves. However, demand-side factors cannot be ruled out without additional foot-traffic or external data. I would recommend a **detailed SKU-level review** of the severely stocked-out products to assess whether this is a replenishment failure or a broader inventory positioning issue.