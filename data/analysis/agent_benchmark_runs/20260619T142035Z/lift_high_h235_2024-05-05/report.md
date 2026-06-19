Now I have all the data. Let me compile a comprehensive RCA report.

---

# Root Cause Analysis — Store h235 | 2024-05-05

## 1. Trigger

**Signal: LIFT** — trailing 7-day % change = **+46.8%** (threshold: ≥30%)

| Metric | Value |
|---|---|
| Current Sales | **$270.80** |
| Previous Day (Sat 5/4) | $219.40 (+23.4% DoD) |
| Trailing 7d Avg | $184.48 |
| Same Weekday 4w Avg (Sundays) | $209.41 (+29.3%) |
| Day of Week | Sunday |
| Holiday Context | **Labor Day period** (inferred) |

Sales are well above all baseline comparisons — a clear and strong lift.

---

## 2. Likely Drivers

1. **Holiday/Calendar Effect (Labor Day period)** — The strongest explanatory factor.
2. **Tier-leading performance** — Store h235 was the #1 store in its tier ($270.8 vs tier avg $241.09) and #1 overall out of 15 stores.
3. **Moderate promotional activity** — 36% of products on promotion, accounting for 36% of sales.
4. **Weather — moderate rain** (precipitation 2.65 mm) which may have driven more customers to shop indoors at this store.

---

## 3. Evidence

### a) Sales Context
Sales on 2024-05-05 ($270.80) are the **highest in the last 8 days** by a margin. The trailing 7-day average is just $184.48, meaning this Sunday was ~47% above the recent norm. Compared to the same-weekday-over-4-weeks average ($209.41), it's +29%. The lift is not marginal — it's substantial.

### b) Calendar / Holiday
- **Labor Day period** is flagged. Historically, this holiday period likely drives increased foot traffic or basket size. The previous 4 days (May 1–4) also fell within this period and showed elevated sales ($221.30, $164.19, $167.44, $219.40) vs earlier normal weekdays ($153.53–$180.90).
- Sunday is a **weekend** day — naturally higher traffic.

### c) Peer & Tier Comparison
- Store h235's $270.80 is **$30 above** the tier average ($241.09) and **double** the overall store average ($134.00).
- Ranked **#1 in its tier** (out of 5) and **#1 overall** (out of 15) — this store uniquely captured more sales than peers on this day.

### d) Promotional Activity
- **47.5%** of products had some discount (avg discount depth 0.9277, meaning ~7% off on average — light/moderate).
- No deep discounts (0% deep discount rate).
- **36.4%** of products were in promotional activities, accounting for **35.9%** of sales. This suggests promotions played a supporting role but were not extremely aggressive — they likely helped draw incremental traffic.

### e) Stockouts
- Stockouts are **elevated**: 4.4 avg stockout hours, 56.8% of products had some stockout, 30.3% had severe stockouts. Despite this, sales were strong — meaning demand outstripped supply and the store still moved high volumes. This could indicate that the lift was driven by a **high-demand holiday surge** that temporarily overwhelmed inventory.

### f) Weather
- Light rain (2.65 mm precipitation) with mild temps (~20.6°C). Minor rain may have localized shopping to this store versus outdoor alternatives, but this is a weak effect.

---

## 4. Caveats

- **Stockout rates are high** (56.8% products with any stockout, 30.3% severe). Despite a sales lift, there may have been **even more unrealized demand** that was lost due to stockouts. The observed sales might actually be **lower than they could have been**.
- The "Labor Day period" label is **inferred**, not confirmed from an official calendar. It's possible there is another explanation for the holiday period impact.
- Promotional intensity is moderate — discounts are shallow. The lift is likely more about **holiday-driven traffic** than price promotion effectiveness.
- No deep discounts (0%), so the lift is **not** from aggressive price-cutting.

---

## 5. Suggested Next Checks

1. **Check neighboring stores' Labor Day period trends** — Is the lift uniform across the area (suggesting a broad holiday effect) or was h235 uniquely outperforming?
2. **Drill into the stockout data** — Which specific products/SKUs stocked out? Were they high-margin or high-demand holiday items? Quantify potential lost sales.
3. **Compare to same Sunday last year** (if data available) — To isolate the Labor Day period effect from year-over-year growth.
4. **Check foot traffic / customer count** — Was the lift driven by more customers, higher basket size, or both?
5. **Investigate the specific promotional activities** — What was promoted (categories, product types)? Did any specific promotion campaign (e.g., "Labor Day Sale") drive the activity?