# RCA Report: Store h555 — 2024-05-16

## 1. Trigger

Signal DROP triggered: trailing-7-day-average sales change of **−24.9%** breached the −20% threshold. Current day sales **$131.91** is the lowest in the 14-day history window and is **−12.7% below** the same-weekday 4-week average ($151.03).

## 2. Likely Drivers

**Primary: Inventory availability degradation**
- Over one-third of products (36.7%) experienced stockout conditions; 17.7% had prolonged stockouts. The average product was unavailable for ~3 hours (2.96 hours).
- At peak, 34.0% of the assortment was simultaneously unavailable.
- Sales shortfall (~25% vs trailing avg) is directionally consistent with the breadth of stockouts.

**Secondary but relevant: Weather headwind**
- 1.89mm precipitation, high humidity — plausible foot-traffic suppressant for a walk-in-heavy store.

**Not supported as drivers:**
- Pricing/promotion: discounts were widespread (48.3% of SKUs) but shallow (avg 7.6% off); no deep discounts. Promotional activity (38.8% of products, 38.2% of sales) was moderate and routine.
- Calendar: normal Thursday, no holiday.

## 3. Evidence

| Metric | Value | vs Current | Gap |
|---|---|---|---|
| Current sales | $131.91 | — | — |
| Prior day (Wed 5/15) | $154.43 | −14.6% | −$22.52 |
| Trailing 7-day avg | $175.63 | −24.9% | −$43.72 |
| Same-weekday 4-wk avg (Thu) | $151.03 | −12.7% | −$19.12 |
| Prior Thu (5/9) | $160.00 | −17.6% | −$28.09 |

- **Sales trajectory**: 5-day sequential decline from Sun ($217.71) → Mon ($167.00) → Tue ($167.73) → Wed ($154.43) → Thu ($131.91). Multi-day softening, not a one-day crash.
- **Peer underperformance**: h555 ranks 5th of 5 in its Tier H, **−18.2% below tier average** ($161.29). Decline started before the rainy day (since Sunday), pointing to a store-specific issue.
- **Inventory**: stockout product rate 36.7%, severe rate 17.7%, hourly peak 34.0%, full stockout 4.1%.
- **Pricing**: average discount factor 0.9239 (~7.6% off), deep discount rate 0.0%. Promo sales share (38.2%) aligns with promo product rate (38.8%).
- **Weather**: wet (1.89mm precipitation, ~23°C, ~70% humidity).

## 4. Caveats

- **Correlation vs causation**: Stockout metrics show correlation with the sales drop but cannot prove causality. Stockouts could result from unanticipated demand exceeding supply, or cause lost sales from insufficient inventory.
- **No category-level granularity**: Aggregate stockout metrics may mask a specific category or top-SKU issue driving most of the revenue impact.
- **Baseline contamination**: The trailing 7-day average includes days that may themselves have had stockouts — the true "unconstrained demand" gap could be larger than measured.
- **Weather is ambiguous**: Precipitation likely suppressed foot traffic, but peers in the same weather region outperformed h555. The multi-day slide (starting Sunday, before the rain) suggests store-level factors dominate.
- **No staffing, local event, or competitor data**: These could provide alternative explanations for the decline.
- **Residual Labor Day effects**: Prior 14-day history includes Labor Day period (May 2–5), which may slightly influence trailing averages, though the recent 5-day downtrend is clear regardless.

## 5. Suggested Next Checks

1. **Category/SKU-level drill-down**: Identify which specific products or categories drove the 36.7% stockout rate. Is it top sellers or low-velocity items? Revenue impact attribution by category.

2. **Inventory ordering vs demand pattern**: Check whether stockouts resulted from under-ordering (chronic issue) or demand spike (transient). Compare replenishment cadence with sell-through rates.

3. **Store operations check**: Given the multi-day decline and last-in-tier performance, investigate staffing levels, operating hours compliance, or local disruptions (construction, road closures, competitor activity) at h555.

4. **Foot traffic data**: If available, validate whether the sales decline is mirrored in traffic (consistent with stockout/traffic cause) or driven by conversion drop (consistent with pricing/promotion or assortment issues).

5. **Weather impact quantification**: Compare h555's performance vs tier peers on rainy days vs dry days to isolate weather contribution from store-specific factors.