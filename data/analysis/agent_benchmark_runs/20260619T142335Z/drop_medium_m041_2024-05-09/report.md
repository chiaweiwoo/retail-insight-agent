Excellent, I have a comprehensive picture. Let me compile the RCA report.

---

## RCA Report: Store m041 – 2024-05-09

### 1. Trigger

**Signal: Drop**

- Current sales: **$56.67**
- Trailing 7-day average: **$84.64** (drop of **-33.0%**, well below the -20% threshold)
- Day over day: **-24.7%** (from $75.30 on May 8)
- Same-weekday 4-week average: **$67.30** (drop of **-15.8%**)

The signal is a clear and material drop against all comparison baselines.

---

### 2. Likely Drivers

**Primary driver: Widespread stockouts.** Stockout metrics are elevated to a level consistent with disrupting sales materially.

**Secondary driver: Post-holiday demand normalization.** The preceding week (May 1–5) included a "labor_day_period" (inferred holiday period) where sales were elevated (e.g., $116.48 on May 5, $94.70 on May 1). Sales were already drifting downward May 6–8 before the sharp drop on May 9, suggesting some pull-forward or holiday-related demand fading.

**Not likely drivers:**
- **Calendar/weather:** May 9 is a normal weekday (Thursday) with no holiday. Mild rain (0.47 precip) and ~21.5°C — possible minor weather effect but not a strong enough factor alone to explain a 33% drop.
- **Discounts:** The average discount is ~0.93 (i.e., ~7% off) and no deep discounts. Discount activity is present but not extreme, and it's normal or even slightly lower than what would offset a sales drop.
- **External promotions/activities:** ~40.6% of products on some activity, accounting for 39.3% of sales — this is moderate but not unusually high or low relative to peers.

---

### 3. Evidence

**Stockout evidence (strong):**

| Metric | Value | Interpretation |
|---|---|---|
| Avg stockout hours | **~3.0 hours** | Products unavailable for ~3 hours on average |
| Stockout product rate | **37.7%** | Over a third of products experienced stockout |
| Severe stockout rate | **15.9%** | Nearly 16% of products had prolonged stockouts |
| Full stockout rate | **8.7%** | ~9% of products were fully out of stock all day |
| Hourly stockout peak | **60.9%** | At its worst hour, 61% of products were unavailable |

These rates are very high. A store where 38% of products hit stockout and 61% are unavailable at peak is very likely to see suppressed sales, especially if stockouts affect high-traffic or high-margin items.

**Peer comparison evidence (moderate):**

- Store m041's sales ($56.67) are **22.5% below tier average** ($73.12) for the same day.
- It ranks **10th out of 15 stores overall**, and **5th (last) out of 5 in its own tier (m-tier)**.
- This underperformance relative to peers suggests a store-specific issue rather than a chain-wide demand shock — which is consistent with a localized problem like stockouts.

**Prior-day trend evidence (mixed):**

- Sales had been declining May 6 ($83.51), May 7 ($79.94), May 8 ($75.30) — a gradual decline from the holiday peak.
- May 9's drop ($56.67) is much sharper than those earlier steps, which could reflect the stockout problem worsening on that specific day, or a cumulative effect.

**Discount/activity evidence (weak):**

- ~46% of products discounted, average discount ~7.4%. No deep discounts (0%). This is ordinary and does not explain a drop. If anything, discounts could have partially mitigated losses but were apparently insufficient.

**Weather evidence (weak):**

- Light rain (0.47 inches), mild temp (~21.5°C). Rain may deter some foot traffic, but the magnitude of the drop far exceeds what mild rain alone would cause.

---

### 4. Caveats

- **Correlation vs. causation:** The stockout metrics are measured on the same day as the sales drop. It is possible that stockouts are partly a *consequence* of unexpected demand earlier in the week (the labor_day_period) depleting inventory, which then caused lower sales on May 9. The direction of causality cannot be fully separated from this single day's data.
- **No transactional-level data:** We don't know exactly *which* products were stocked out. If the stockouts were concentrated on low-volume items, their impact would be smaller. Conversely, if they hit top sellers, the impact would be large. More detailed SKU-level data would help.
- **Holiday period effect:** Sales on May 1–5 were elevated (likely labor-day related). Some of the drop on May 9 could be a natural reversion post-holiday, but the magnitude is larger than the simple reversion story.
- **No foot traffic data:** Without customer count data, we cannot distinguish between "customers came but couldn't buy due to stockouts" vs. "customers didn't come at all (perhaps due to weather or post-holiday fatigue)."
- **Peer data is a single snapshot:** The tier average includes other m-tier stores; at $56.67 vs. $73.12, this store clearly underperforms, but we don't know if peers also experienced stockouts.

---

### 5. Suggested Next Checks

1. **Investigate which specific products were stocked out on May 9.** Were they high-velocity or promotional items? Cross-reference the stockout list with top-selling SKUs from the prior week.
2. **Check inventory replenishment records** — did a delivery get missed or delayed? The high stockout rate across so many products (~38%) could indicate a supply chain disruption (missed truck, order error).
3. **Review foot traffic / transaction count** for May 9 vs. recent Thursdays to separate demand-side from supply-side causes.
4. **Look at the preceding week's sales spike** — did the labor_day_period deplete inventory so severely that May 9 was a "shelf-empty" day? This would make stockouts the consequence, not the root cause.
5. **Compare to other stores in the same tier** — if they also had stockout spikes, this points to a chain-wide distribution issue rather than a store-level problem.