Here's the full analysis.

---

## Root Cause Analysis — Store h555, 2024-05-16

### 1. Trigger

**Signal: Drop.** The store's trailing-7-day sales average was $175.63 vs. $131.91 on the trigger day, yielding a **-24.89% change**, well below the -20% drop threshold. Day-over-day sales also fell -14.6% ($154.43 -> $131.91), and the same-weekday-4-week comparison shows -12.7%.

### 2. Likely Drivers

1. **Elevated stockouts — the most probable primary cause.** The store experienced a severe stockout day with 36.7% of products out of stock at some point, 17.7% in severe stockout, and an average stockout duration of ~3 hours per affected product. This is a marked deterioration from the prior day (May 15: 38.1% stockout rate but only 9.5% severe and ~2.1 avg hours). The severe stockout rate nearly doubled (9.5% -> 17.7%) and the average stockout hours increased by ~40%.

2. **No discount or promotional lift to compensate.** Discount depth was modest (avg discount ~7.6% off, no deep discounts at 0%), and the promotional activity rate (~39% of products) was not strong enough to offset the lost availability—promo activity sales share (38.2%) roughly mirrors the activity rate, suggesting no outsized pull.

3. **Weather was unfavorable.** Precipitation of ~1.89 mm and moderate temperatures (23.2°C) may have slightly dampened foot traffic, but this is weak as a standalone explanation given the peer comparison below.

### 3. Evidence

| Dimension | Value | Indication |
|---|---|---|
| **Sales trigger** | Trailing 7d: -24.9%, DoD: -14.6%, 4W-same-wkday: -12.7% | Clear drop across all baselines |
| **Stockout (May 16)** | 36.7% products affected; avg 3.0 hrs out; 17.7% severe | **High and worsening** vs. May 15 (9.5% severe, 2.1 hrs avg) |
| **Discounts** | Avg discount factor 0.924 (~7.6% off); 0% deep discount | No pricing lever used to offset |
| **Promotions** | 38.8% activity product rate; 38.2% activity sales share | Promo activity matches share — no disproportionate pull |
| **Weather** | 1.89mm precip; 23.2°C; normal Thursday | Light rain, not extreme, but possibly mildly negative |
| **Holiday** | Normal weekday (Thursday) | No calendar effect |
| **Peer comparison** | Store $131.91 vs. tier average $161.29 (tier rank 5/5) | **Worst in its tier**; overall rank 5/15 — peers did better |
| **Prior-day stockout (May 15)** | 38.1% affected, 9.5% severe, 2.1 hrs avg | Stockouts existed before but **severity escalated** on May 16 |

**Key peer insight:** The store was the worst performer in its own tier (5th out of 5) and below the overall average ($87.35) — but that overall average includes lower-tier stores. The tier average of $161.29 confirms most similar stores sold ~22% more. This reduces the likelihood that the drop was purely weather-driven (peers would share same weather) and points to a **local operational issue** — most likely stockouts.

### 4. Caveats

- **Stockout may be both cause and consequence.** Lower customer traffic could reduce the observed stockout pressure, but the increase in severe stockout rate (9.5% -> 17.7%) and longer average hours suggest a genuine product availability issue rather than a demand-driven artifact.
- The cause of the stockouts is unknown — could be a delivery gap, a replenishment error, or supplier failure. The tools do not distinguish.
- The prior day (May 15) already had elevated stockout rates (38.1%) but sales were $154.43, suggesting that the jump in **severity** on May 16 (not just breadth) was the critical factor.
- Weather (light rain) could have contributed modestly, but peers in the same region who faced the same weather averaged $161.29, so weather alone is insufficient to explain the gap.

### 5. Suggested Next Checks

1. **Investigate replenishment/delivery records** for May 15-16. Determine if a scheduled delivery was missed or late, explaining the worsening stockout severity.
2. **Drill into top stockout categories** — identify whether the stockouts were concentrated in high-traffic/high-margin items (e.g., perishables, key staples) which would have the largest sales impact.
3. **Check staffing levels** on May 16. Understaffing could delay restocking from back-of-house, converting moderate stockouts into severe ones.
4. **Review the May 15 evening close inventory** — if shelf gaps were already present overnight, the May 16 morning starting position would have been poor.
5. **Compare stockout severity by hour** — if peak stockout hours coincide with typical high-traffic periods (e.g., late afternoon), that would amplify the sales loss.