I already have everything. Let me compile the report.

---

## Root Cause Analysis Report – Store h555 | 2024-05-16

### 1. Trigger

**Signal: DROP**

Sales on 2024-05-16 were **$131.91**, which is:
- **-24.9%** below the trailing 7-day avg of $175.63 (exceeds the **-20% drop** threshold)
- **-14.6%** day-over-day vs $154.43 (Wed)
- **-12.7%** below the same-weekday 4-week avg of $151.03

The store ranks **5th (last)** among 5 tier-H peers and is well below the tier average ($161.29), confirming a meaningful underperformance.

---

### 2. Likely Drivers

**Primary driver: Widespread stockouts**

- **36.7% of products** experienced stockout, with an average stockout duration of **~3 hours**.
- **Severe stockouts** (extended outage) affected **17.7% of products**.
- A peak hourly stockout rate of **34.0%** suggests a mid-day inventory crisis that suppressed sales through the remainder of the day.
- This is a strong explanatory factor: missing ~1/3 of product availability would materially reduce total transaction volume.

**Secondary/Contributing factors:**
- **No deep discount activity** (0% deep discount rate) — the store lacked aggressive price levers to compensate for inventory gaps or stimulate demand.
- The store sits in the **top tier (H)** where the daily average is $161.29 — its $131.91 is a **$29.38 gap**, consistent with lost sales due to unavailable products.
- **Moderate promotional activity** (38.8% of products, 38.2% sales share) — not unusually high or low.

---

### 3. Evidence

| Evidence Source | Finding |
|---|---|
| **Signal Evidence** | Trailing 7d change = -24.9% (threshold: -20%); same-weekday 4w change = -12.7%. Label: **drop**. |
| **Sales Context** | Current: $131.91; Prev day: $154.43; 7d avg: $175.63; 4w avg: $151.03. Declining trend visible over the last 3 days (May 14: $167.73 → May 15: $154.43 → May 16: $131.91). |
| **Stockouts** | **36.7% stockout rate**; avg **2.96 hours** out-of-stock; **17.7% severe**; peak hourly rate **34.0%**. This is the strongest causal signal. |
| **Discounts** | Avg discount factor 0.92 (small); 48.3% of products discounted but **0% deep discounts**. No liquidation or aggressive markdown push. |
| **Activity** | 38.8% of products under promotion; 38.2% of sales from promoted items — moderate, not a driver. |
| **Calendar/Weather** | Normal Thursday; no holiday; mild rain (1.9mm), temp ~23°C — not disruptive. |
| **Peer Context** | Tier-H avg: $161.29 (store at $131.91). Ranked 5/5 in tier. No other tier-H store was this low. |

---

### 4. Caveats

- **Stockout-sales causality direction**: While stockouts likely caused lost sales, it is also possible that lower foot traffic / demand led to less restocking urgency. The data here is correlational.
- **No deep discounts** could be either a cause (lost opportunity to stimulate sales) or a symptom (a passive pricing strategy). Without deeper discounting, the store couldn't offset the stockout-driven losses.
- **No foot traffic / customer count data** is available — we cannot rule out a demand-side drop (e.g., local event, competitor opening).
- The decline has been **multi-day** (May 14→16), suggesting a possible inventory replenishment issue that compounded over several days, not a one-day anomaly.

---

### 5. Suggested Next Checks

1. **Investigate specific stockout categories** — Which departments/SKUs had the longest stockout durations? Was it a few high-volume items or many smaller ones?
2. **Check yesterday (May 15) stockouts** — If stockouts were already elevated on May 15, the problem may be cumulative across days.
3. **Replenishment & supply chain** — Check whether a delivery was missed or delayed. Compare actual vs. scheduled inbound shipments.
4. **Foot traffic / POS transaction count** — If transactions dropped proportionally to sales, demand-side causes are more likely; if basket size dropped, stockouts driving substitution/abandonment is more likely.
5. **Compare to peer stockout rates** — If other tier-H stores also had elevated stockouts on the same day, the issue may be warehouse/distribution-wide rather than store-specific.