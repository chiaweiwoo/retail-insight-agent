# RCA Report — Store l165, 2024-05-16

## 1. Trigger

Signal drop detected: trailing-7d % change = **-31.7%** (threshold: -20%). Current sales: **$25.38**, the lowest in the 8-day window.

## 2. Likely Drivers

**Primary driver: Widespread stockout conditions, likely compounded by weather-related foot traffic drop.**

- Stockout rates were materially elevated (27.3% of products affected, 36.4% peak hourly rate) — sufficient to suppress sales materially.
- Heavy rainfall (~1.89 inches) plausibly reduced foot traffic, further depressing sales.
- Pricing/promotion posture was restrained but not anomalous — unlikely a primary driver.

**Secondary: Normal post-weekend decay coinciding with a rainy Thursday.** The gap vs. the cleaner same-weekday-4w baseline ($28.05) is only ~$2.67 (-9.5%), meaning the signal severity is partly an artifact of an inflated trailing-7d average (includes weekend peaks of $57.20).

## 3. Evidence

| Evidence | Source | Type |
|---|---|---|
| Sales: $25.38, down -31.7% vs trailing-7d avg ($37.17) | signal_analyst | Observed |
| Same-weekday-4w avg: $28.05 → -9.5% gap (moderate) | signal_analyst | Observed |
| Stockout: 27.3% of products affected, 11.4% severe | inventory_analyst | Observed |
| Peak hourly stockout: 36.4% of product lines unavailable | inventory_analyst | Observed |
| Avg stockout duration: 1.86 hrs per product | inventory_analyst | Observed |
| No deep discounting (0% deep discount rate) | pricing_activity_analyst | Observed |
| Average discount: ~7.8%, 47.7% of products discounted | pricing_activity_analyst | Observed |
| Rainfall: ~1.89 inches, mild temp 23.2°C | context_analyst | Observed |
| Store l165 ranked 5th of 5 in tier L ($29.84 avg) | context_analyst | Observed |
| Store l165 ranked 15th of 15 chain-wide | context_analyst | Observed |
| Prior Thursday (5/9): $26.50 — nearly flat vs $25.38 today | context_analyst | Observed |

**Inference:** The stockout conditions were widespread enough to explain a meaningful portion of the ~$2.67 gap vs. the Thursday baseline (e.g., if high-velocity SKUs were among the 11.4% severely stocked-out products). The rain likely suppressed traffic, compounding the effect. The chain-lowest rank suggests store-specific operational issues, not just weather.

**Caveat:** Cause vs. consequence ambiguity remains — stockouts could be partly *caused by* low demand (over-ordering leading to shelf allocation issues), though the direction more plausibly runs stockouts → lost sales given the severity.

## 4. Caveats

- **Thursday baseline is noisy:** The 4-week average ($28.05) includes a Labor Day period Thursday (5/2: $27.10), which may suppress the comparison. The most recent normal Thursday (5/9: $26.50) is nearly identical to today's $25.38.
- **No SKU-level detail:** We don't know if stockouts hit top-20 revenue items. If they did, revenue impact could be amplified beyond the aggregate numbers.
- **Peak stockout timing unknown:** The 36.4% peak could have occurred during low-traffic hours, minimizing actual sales impact — or during peak hours, maximizing it.
- **Weather/peer overlap unconfirmed:** We don't know if other L-tier stores experienced similar rain, which would weaken the "underperformance vs. peers" conclusion.
- **Tier L has only 5 stores:** Small peer group; one outlier can skew averages.
- **No delivery/logistics data:** Cannot determine if stockouts were from missed deliveries, receiving lags, or unexpected demand spikes.

## 5. Suggested Next Checks

1. **Cross-reference stockout SKUs with top-20 revenue items** — if severe-stockout products overlap with high-velocity lines, the stockout → sales loss link strengthens significantly.
2. **Check delivery/logistics records for 5/15–5/16** — was a truck delayed or missed? This would explain the peak hourly stockout rate of 36.4%.
3. **Compare l165 weather vs. peer L-tier stores** — if peers had similar rain but higher sales, the store-specific operational hypothesis gains weight.
4. **Examine hourly sales pattern** — did sales drop sharply during the peak stockout hour (suggesting causal link) or remain flat throughout (suggesting traffic-driven decline)?
5. **Review staffing or store-level disruption logs** — the chain-lowest rank suggests a possible local issue (e.g., reduced hours, staffing shortages, unexpected closure period).