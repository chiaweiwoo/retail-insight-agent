# RCA Report — Store l165 | 2024-05-16

## 1. Trigger

Trailing 7-day percent change signal fired a **DROP** alert at **−31.7%** (threshold: ≤ −20%). Current sales of **$25.38** represent the lowest value in an 8-day window.

## 2. Likely Drivers

The sales decline is **multi-causal**. The most probable drivers, ranked:

1. **Rain-related foot traffic suppression** — 1.89 mm precipitation (highest in the window) on a Thursday that is already a chronically soft day.
2. **Structural stockout failure** — 27.3% of products affected; 11.4% severe (>4 hr). Likely suppressed conversion/basket size materially.
3. **Modest promotional pullback** — discount breadth contracted (52% → 48%) and depth shallowed slightly (~8.2% → ~7.8% off).
4. **Day-of-week pattern** — the same-weekday 4-week baseline ($28.05) confirms Thursdays are historically weak for this store.

None of these drivers alone explains the full −32% gap vs. trailing 7-day avg, but together they are sufficient.

## 3. Evidence

| Evidence Category | Observed Fact | Source |
|---|---|---|
| **Signal** | Trailing 7d % change = −31.7%; DoD = −24% | Signal desk |
| **Sales shape** | Weekend spike (Sun 57.2) → steady decline Mon–Thu (36.4 → 32.2 → 33.5 → 25.4) | Signal desk |
| **Stockout severity** | 27.3% of products had any stockout; 11.4% had severe (>4 hr); peak hourly = 36.4% unavailable | Inventory desk |
| **Thursday baseline** | Same-weekday 4w avg = 28.05; current day = 25.38 (−9.5%) | Signal & context desks |
| **Discount breadth** | 47.7% products discounted vs. 52.3% on prior day; discount factor 0.9218 vs. 0.9182 | Pricing desk |
| **Deep discounting** | 0.0% on 5/16, unchanged from 5/14–15; was 2.3% on 5/9 | Pricing desk |
| **Weather** | 1.89 mm precipitation — highest in recent window; mild temp (23°C) | Context desk |
| **Peer rank** | 5th of 5 in Tier L; 15th of 15 overall — chronically lowest performer | Context desk |

**Key inference** (not directly observed): The stockout rate is high enough (27%) that at least some portion of the ~$12 gap to the trailing 7-day avg is likely attributable to availability failure. The pricing pullback is directionally consistent but too small to be the primary driver.

## 4. Caveats

- **No timestamp correlation** between stockout hours and sales dips — causality direction (stockout → low sales vs. low traffic → less shelf-scanning) is ambiguous, though the 11.4% severe stockout rate argues for a genuine availability problem.
- **No SKU-level data** — we cannot determine whether high-velocity items were among the stockouts.
- **No replenishment logs** — the root of the stockout (under-ordering, DC miss, or shelf management) is unknown.
- **No peer-store weather comparison** — we cannot confirm whether other L-tier stores in the same rain zone had similar dips, which would strengthen the weather argument.
- **The trailing 7-day avg ($37.17) is inflated** by the Sunday spike ($57.20), making the −32% gap somewhat misleading vs. a day-of-week-adjusted baseline.
- **The Thursday same-weekday 4w avg includes May 2** (a "labor day period" anomaly), which may distort the baseline.

## 5. Suggested Next Checks

1. **Category-level stockout impact:** Determine which categories had the highest stockout rates. If high-margin or high-velocity categories (e.g., produce, dairy) were affected, the sales impact is amplified.
2. **Replenishment log review:** Check whether orders for 5/15–5/16 were placed correctly and whether the DC shipped as requested. Distinguish ordered-but-not-delivered vs. received-but-not-shelved.
3. **Peer-store weather comparison:** Obtain sales and weather data for other Tier L stores in the same geographic region on 5/16. If they also had rain and saw comparable dips (especially on Thursday), the weather hypothesis is supported. If they did not, the issue is store-specific (likely stockouts).
4. **Hourly sales vs. hourly stockout correlation:** Overlay hourly sales trends with hourly stockout rates for 5/16. If sales troughs coincide with peak stockout hours (36.4% at worst), the causal role of availability is strengthened.
5. **Prior Thursday deep dive:** Review why the same-weekday 4w baseline ($28.05) is already low. Is this a chronic pattern or a recent decay? Compare inventory and promotion data for the prior three Thursdays to see if the current stockout situation is new or persistent.