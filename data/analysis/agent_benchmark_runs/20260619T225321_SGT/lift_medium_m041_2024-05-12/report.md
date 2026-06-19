# RCA Report – Store m041, 2024-05-12

---

## 1. Trigger

**Lift signal fired:** Trailing-7d % change = +77.3% (threshold +30%).  
**Observed sales:** $146.40 vs. trailing 7d avg $82.56; +43% vs. 4-week same-weekday avg ($102.37); +26% vs. prior Sunday (May 5, $116.48). Largest single-day jump in the 14-day window.

---

## 2. Likely Drivers

1. **Strong underlying demand surge (primary driver, inference)** — The sales level far exceeds any baseline or pricing/promotion explanation alone. Store outperformed its tier by +19.5% and ranked #1 of 5 in its tier, while weather and calendar were unremarkable. This suggests a local, store-specific demand event.

2. **Broader promotional coverage (supporting driver)** — Discounted product rate hit 60.9% (highest in window) vs. prior Sunday 53.6%. Average discount deepened slightly (~10% vs. ~8.4% off retail). ~40% of sales came from promoted items. However, no deep discounts were present, so this alone does not explain the full lift magnitude.

3. **Inventory constraint likely capped sales (suppressing factor)** — Extremely high stockout rates (55.1% of products hit zero at some point; avg 4.33 hrs out per product; peak hourly unavailability 50.7%) mean the $146.40 likely *understates* true demand. The directionality is ambiguous (demand surge caused stockouts vs. pre-existing replenishment failure), but in either scenario, unmet demand was probably higher than observed sales.

---

## 3. Evidence

| Evidence Type | Finding | Source |
|---|---|---|
| **Sales magnitude** | $146.40 is a new Sunday high in the 4-week lookback range ($70.5–$116.5) | inventory_analyst |
| **Baseline comparisons** | All three baselines (trailing 7d, prior day, 4wk same-weekday) show lift directionally consistent | signal_analyst |
| **Pricing depth** | Avg discount index 0.8997 (~10% off); deep discount rate 0% | pricing_activity_analyst |
| **Promo breadth** | Discounted product rate 60.87%; activity product rate 46.38%; activity sales share 39.41% | pricing_activity_analyst |
| **Stockout severity** | Avg stockout hours per product: 4.33 hrs; stockout product rate: 55.1%; severe stockout rate: 27.5% | inventory_analyst |
| **Peer outperformance** | Tier avg: $122.52; store m041: $146.40 (+19.5%); ranked #1 of 5 in tier | context_analyst |
| **Weather** | Moderate rain (0.68 in), mild temp (22.1°C) — unremarkable, cannot explain store-specific lift | context_analyst |
| **Calendar** | Normal Sunday (weekend, not holiday); prior Sunday was labor_day_period | context_analyst |
| **Sales shape** | Acceleration pattern: ramp-up during labor_day_period (May 1–5), mild dip May 6–10, sharp break upward May 11–12 | signal_analyst |

---

## 4. Caveats

- **Directionality of stockouts unresolved:** High stockout rates could be a *consequence* of demand surge (products sold out faster than replenishment) or a *pre-existing failure* (missed delivery, system error). Hourly time-series would be needed to distinguish.
- **No product-level data examined:** A few high-velocity items could be driving both the sales spike and stockout counts. Conversely, many low-velocity items being out of stock could inflate stockout rates without materially affecting revenue.
- **Pricing/promotion contribution is moderate:** While broader than usual, it does not alone explain the magnitude of the lift. Non-price factors (local event, competitor closure, store-specific marketing) are likely involved.
- **Baseline may be conservative:** The 4-week same-weekday average ($102.37) includes a labor_day_period Sunday (May 5) which may have had suppressed traffic, making the +43% lift appear larger than it would against a true "normal" Sunday.
- **Holiday context shift:** Prior Sunday was classified as "labor_day_period"; current Sunday is "weekend" — different demand patterns may apply.
- **No qualitative field data** (store manager input, local event logs, competitor intelligence) was available to identify the specific demand driver.

---

## 5. Suggested Next Checks

1. **Hourly sales vs. hourly stockout time-series** — Determine whether stockouts preceded or followed the demand surge. This resolves whether the inventory data reflects a pre-existing replenishment failure or demand-driven sellout.

2. **Product-level drill-down** — Identify top-selling SKUs on May 12. Check whether a few high-velocity items drove both the sales spike and the stockout counts. Also check if those items had unique promo or pricing support.

3. **Replenishment logs / delivery records for May 11–12** — Confirm whether a scheduled truck arrived, was missed, or was shorted. This tests the "pre-existing replenishment failure" hypothesis.

4. **Store manager inquiry** — Ask about local activity: competitor closure, community event, school function, store-specific marketing, staffing coverage change, or any special circumstance on May 12.

5. **Monitor subsequent days (May 13–14)** — Check if sales sustain near $146 or revert toward baseline. A one-day spike that reverts suggests a transient event; sustained elevation suggests a shift in demand level.