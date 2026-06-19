## MEMORANDUM — Signal Analysis: Store h235 on 2024-05-05

---

### 1. Scope

Store **h235**, date **2024-05-05** (Sunday). Examined signal validity, baseline comparisons, and recent sales shape using trailing-7d averages and same-weekday-4w averages. This day falls within a **labor_day_period** holiday context.

---

### 2. Findings

**Signal Classification: LIFT (valid trigger)**
- The trailing-7d pct change is **+46.8%**, well above the 30% lift threshold.
- Same-weekday-4w pct change is **+29.3%**, also above the lift threshold.
- Current sales: **$270.80** — the highest single-day value in the trailing 14-day window.

**Baseline Comparisons**
| Baseline | Value | vs. Current Sales |
|---|---|---|
| Current sales | **$270.80** | — |
| Prior day (Sat 05-04) | $219.40 | +23.4% DoD |
| Trailing 7d avg | $184.48 | +46.8% above avg |
| Same-weekday 4w avg (Sundays) | $209.41 | +29.3% above avg |

All three baselines are meaningfully exceeded. The lift signal is consistent across both short-term (7d trend) and medium-term (4-week same-day) comparisons.

**Recent Sales Shape**

The sales history over the past 14 days shows a notable **step-up starting May 1** (the start of the labor_day_period). Prior to May, store h235's daily sales ranged roughly $150–$250 (with typical Sunday peaks near $185–$251). Beginning May 1, values lifted:

- May 1 (Wed): $221.30
- May 4 (Sat): $219.40
- **May 5 (Sun): $270.80** ← session high

Sales have been elevated across multiple weekdays during this period, and the May 5 Sunday exceeds the prior Sunday (Apr 28: $184.63) by **+46.7%** — a substantial week-over-week gain that also outpaces the prior Sunday peak (Apr 21: $250.82).

**Signal Validity Summary**
- ✅ Trailing-7d change exceeds lift threshold (30%)
- ✅ Same-weekday-4w change exceeds lift threshold
- ✅ Day-over-day gain is positive and material
- ✅ The current sales value is the highest in the observed window
- ✅ The lift is visible across multiple baseline comparisons (not noise)
- Signal is **valid and supported** by the data.

---

### 3. Caveats

- The lift coincides with the **labor_day_period** (May 1 onward). This contextual holiday may partially explain elevated sales, but per scope I do not attribute causality.
- The trailing-7d average includes the low-sales days of late April, which amplifies the % change metric. The same-weekday baseline ($209.41) is a more conservative comparator, and it too shows a **+29% lift** — just below the 30% hard threshold but still materially elevated.
- The 14-day history shows only two other Sundays for comparison (Apr 21: $250.82; Apr 28: $184.63), so the same-weekday comparison is based on a small sample; seasonality within the month may be present but unmeasured.
- No evidence on stockout, discount, activity, weather, or peer behavior was examined.