Now I have a comprehensive picture. Let me compile the report.

---

## Root Cause Analysis Report — Store l165, 2024-05-16

### 1. Trigger

**Signal: DROP**  
- Current sales: **$25.38**  
- Trailing 7-day avg: **$37.17** (signal fires at ≤ -20%; actual: **-31.7%**)  
- Day-over-day: **-24.2%** (from $33.50 on May 15)  
- Vs. same weekday 4-week avg: **-9.5%** ($28.05 baseline)

Sales on this Thursday are the lowest in the trailing 8-day window.

---

### 2. Likely Drivers

**Primary driver: Significant stockout issues.** The store experienced a high rate of stockouts on the day, which is the most plausible direct cause of suppressed sales.

**Secondary factor: No deep discounts or strong promotional pull.** With no deep discounting and only moderate activity rates, there was no compensating mechanism to offset lost availability.

**Tertiary/structural: This store is chronically low-performing.** It is the **lowest-ranked store** overall (rank 15/15) and the **lowest in its tier** (rank 5/5), with sales well below both tier average ($29.84) and overall average ($87.35).

---

### 3. Evidence

**Stockouts (strongest evidence):**
- **27.3%** of products experienced a stockout on May 16.
- **11.4%** experienced *severe* stockouts.
- Average stockout duration: **1.86 hours**.
- Hourly stockout rate peaked at **36.4%** — meaning over a third of SKUs were unavailable at some point.
- These figures are significant and directly suppress the ability to transact.

**Discounts & Promotions (weak compensatory force):**
- Average discount depth: **0.92** (i.e., ~8% off — minimal).
- **0%** deep discounts (heavy discounting could have driven traffic/volume but was absent).
- Activity (promotional) product rate: **40.9%**, with activity sales share of **39.4%** — moderate but unremarkable.

**Calendar & Weather (neutral — no material impact):**
- Normal weekday (Thursday), no holiday.
- Precipitation: 1.89mm (light rain), temperature ~23°C, moderate humidity. Nothing extreme enough to explain a 32% drop.

**Peer & Tier Context:**
- Store l165 is in the **L tier** (5 stores). Its sales of $25.38 are **15% below** the tier average of $29.84 for the same day.
- Even relative to its peers, it underperformed — but the whole tier is weak.
- The store is consistently the **lowest-ranked** overall store in the data set.

**Historical Context:**
- Sales dropped from $33.50 (May 15) to $25.38 (May 16). Prior Thursdays: May 9 was $26.50. So the current $25.38 is not radically lower than the prior Thursday itself (-4.2% vs May 9), but the trailing 7d avg was elevated by a strong weekend ($57.20 on Sunday, May 12), making the drop look sharper.

---

### 4. Caveats

- **Stockout ↔ Sales causality direction is confounded.** High stockout rates could cause lower sales, but lower traffic could also reduce the need to restock. The analysis doesn't distinguish which came first.
- **The trailing 7-day average ($37.17) was inflated** by an unusually high Sunday ($57.20). The "true" recent baseline for a weekday is closer to $30–33. The -31.7% metric exaggerates the drop.
- **Peer data is weak** — the entire L tier is low-volume, so being last among them may be structural, not event-driven.
- No data on competitor activity, local events, staffing shortages, or supply-chain disruptions beyond stockouts.

---

### 5. Suggested Next Checks

1. **Stockout depth analysis:** Which specific SKUs or categories hit stockout? Were they high-velocity items (e.g., core staples) that would have the most impact on total sales?
2. **Traffic data** (if available): Did foot traffic drop, suggesting a demand-side issue, or was traffic normal with conversion suffering due to stockouts?
3. **Lead/lag stockout timing:** Were stockouts present early in the day (suppressing full-day sales) or did they occur later (less impactful)?
4. **Compare to prior Thursdays' stockout rates:** Is the 27.3% stockout rate normal for this store, or is it a spike?
5. **Supply chain check:** Was there a missed delivery (e.g., May 15 or early May 16)? Could explain both low stock and lack of deep discounts (no inventory to discount).
6. **Staffing:** Could understaffing have led to both poor shelf replenishment and reduced sales/service?