Now I have extensive data. Let me compile the analysis.

---

## RCA Report: Store l185 – 2024-04-13

### 1. Trigger

**Signal: LIFT**  
Current sales of **49.4** exceed the trailing-7-day average of **32.0** by **+54.3%**, well above the +30% lift threshold. Day-over-day growth from 35.7 (Apr 12) is also strong at **+38.4%**.

---

### 2. Likely Drivers

The lift appears to be driven by **a combination of promotional activity, discounting, and calendar/weekend effects**, despite **material stockout friction** that would otherwise have held sales back.

---

### 3. Evidence

**Sales History & Baseline Context**
- Trailing 7-day average: ~32.0. The most recent prior Saturday (Apr 6) recorded 41.5, meaning the current 49.4 is +19% above that comparable Saturday.
- Sales have trended upward through the week: 27.8 (Wed) -> 29.2 (Thu) -> 35.7 (Fri) -> 49.4 (Sat), suggesting a normal weekly ramp plus an extra boost.

**Promotional & Discount Activity (strong supporting evidence)**
- **Activity rate**: 36.6% of products were on promotion, and these promoted items accounted for **48.4% of all sales** — a disproportionate share indicating the promotion was effective.
- **Discounting**: 46.3% of products carried some discount; average discount depth was 0.92 (i.e., ~8% off on average). No deep discounts (0% deep-discount rate), so this was moderate, broad-based discounting rather than a clearance fire sale.
- The high sales share from activity items (~48%) strongly suggests the lift was **promotion-led**.

**Calendar & Weather (supporting)**
- Saturday is a naturally strong shopping day. The previous Saturday (Apr 6) fell during the **Qingming period** holiday, which may have suppressed traffic relative to a normal Saturday. Apr 13 is a regular weekend Saturday, so the lift partly reflects a **holiday-effect reversal**.
- Weather: moderate rain (2.2mm precipitation), 18.4°C, high humidity. Nothing extreme enough to meaningfully drive or suppress sales.

**Stockout Context (paradoxical headwind)**
- **High stockout rates**: average stockout hours per product = 5.85 hours; 68.3% of products had some stockout; 39.0% had severe stockouts; hourly stockout peak rate = 65.9%.
- Despite this, sales hit a 7-day high. This suggests demand was strong enough to overcome availability constraints, or that the promoted, fast-moving items were particularly well-stocked relative to the rest of the range. Stockouts may have been concentrated in non-promotional or slower-moving SKUs.

**Peer & Tier Comparison**
- Store l185 is in the **L tier** (5 stores). Its sales of 49.4 are ranked **#1 in tier**, well above the tier average of 40.1. However, the overall (all tiers) same-day average is 116.8 — this store is a small-format store, so its absolute sales are lower by design. The fact it leads its tier suggests the lift is real and not an artifact.

---

### 4. Caveats

- **Stockouts cut both ways**: The high stockout rates could be a *result* of strong demand depleting inventory (i.e., a consequence, not a cause). If so, the underlying demand lift may be even larger than observed. However, we cannot rule out that some sales were lost due to stockouts; the actual lift could have been even higher.
- **No same-weekday 4-week baseline**: The tool returned null for `same_weekday_4w_avg_sales`, so we cannot compare against an average of prior Saturdays. The single prior Saturday (Apr 6, Qingming period) may not be a fair baseline.
- **Promotion causality**: While promotional activity and sales lift are strongly correlated, we cannot fully separate whether the promotion *caused* the lift or was simply timed alongside it. Given the 48% sales share from promoted items, causation is likely but not proven.
- **Weather**: Light rain may have detered some walk-in traffic, but the sales data shows this didn't materialize as a negative effect.

---

### 5. Suggested Next Checks

1. **Check whether the same promotion was run in prior weeks** — is this a temporary tactical promo or a new permanent price change? Compare discount context for prior Saturdays (Apr 6, Mar 30).
2. **Drill into stockout timing**: Did stockouts spike after peak sales hours (suggesting demand-driven depletion), or start early in the day (suggesting replenishment issues)? Hourly sales data would help.
3. **Examine which categories or SKUs drove the activity sales share**: If the promoted items are high-margin or seasonal, this may influence whether to repeat the tactic.
4. **Compare to L-tier peers on stockout rates**: If peers also have high stockouts but lower sales, L185's execution (or mix) may be superior — worth understanding.
5. **Monitor the following Saturday (Apr 20)** to see if the lift sustains or if it was purely a one-time promotional spike.