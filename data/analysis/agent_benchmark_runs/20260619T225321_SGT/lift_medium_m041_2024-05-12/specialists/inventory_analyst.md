Now I have a comprehensive picture. Here's the memo.

---

## 1. Scope

Store: **m041** | Date: **2024-05-12** (Sunday, classified as weekend)

Analysis covers stockout severity, availability pressure, and whether inventory constraints contributed to the sales observed that day.

---

## 2. Findings

### Sales performance
- **Current sales: $146.4** — a **sharp upward move** vs. recent norms.
- Compared to trailing 7d avg ($82.6): **+77%**.
- Compared to prior Sunday (2024-05-05, also a holiday-period Sunday): $116.5 → **+26%**.
- Compared to the 4-week same-weekday average ($102.4): **+43%**.
- The prior day (Saturday 2024-05-11) was $89.0, so this is a **large day-over-day jump**.
- Historical Sunday range across the last 4 weeks: $70.5 – $116.5. $146.4 is a **new high** for Sundays in the lookback.

### Stockout & availability picture (this is striking)
| Metric | Value |
|---|---|
| **Avg stockout hours per product** | **4.33 hrs** (very high for a single day) |
| **Stockout product rate** | **55.1%** (more than half of SKUs out of stock at some point) |
| **Severe stockout product rate** | **27.5%** (over a quarter of products out for extended period) |
| **Full stockout product rate** | **2.9%** |
| **Peak hourly stockout rate** | **50.7%** (at worst hour, half the store was unavailable) |

### Interpretation: Cause vs. Consequence Ambiguity

**The high sales and the extreme stockout rates are very likely connected**, but the directionality is ambiguous:

1. **Demand-driven stockouts (consequence hypothesis):** The store saw a major demand surge on this Sunday (+77% vs. trailing average). This may have overwhelmed available inventory, causing products to sell through faster than replenishment could keep up. In this reading, *stockouts are the consequence of high demand,* not a primary cause of the sales move.

2. **Availability-constrained sales (cause hypothesis):** Despite the $146.4 being a high number, it could have been **even higher** if stockouts weren't so severe. With 55% of products hitting zero at some point and peak hourly unavailability at 51%, it's quite possible that demand was *capped* by poor availability. The true unmet demand could be significantly above the observed $146.4.

3. **Pre-existing replenishment failure (independent factor):** The stockout data (4.3 avg hours, 55% rate) is so extreme it might reflect a systematic replenishment or ordering failure that predates the demand surge — e.g., missed delivery, system error, or upstream supply break. If so, the high sales happened *despite* terrible availability, which would make the underlying demand even stronger.

**Bottom line: Inventory issues are a material factor in this store-day.** The stockout metrics are among the worst you'd expect to see on an otherwise normal day. They likely *depressed* sales below what demand would have supported, meaning the sales figure of $146.4 probably understates true customer demand.

---

## 3. Caveats

- **Directionality cannot be resolved from daily aggregates alone.** Hourly sales vs. hourly stockout time-series would be needed to see if sales spiked first (demand-driven sellout) or stockouts were present early (replenishment failure).
- **No product-level detail** is available — it's possible a few high-velocity items drove both the sales spike and the stockout count, or that many low-velocity items were already out of stock, inflating the stockout product rate without materially affecting revenue.
- **The 2024-05-05 prior Sunday** fell in a "labor_day_period" holiday context. The current Sunday (2024-05-12) is labeled "weekend" — different holiday classification could mean different demand patterns.
- **No replenishment log or delivery data** was available to confirm whether a truck was missed or order was shorted.
- **The "severe stockout" definition** (≥X consecutive hours) could overlap with end-of-day closeout; need to rule out normal end-of-day zeroing for perishables or deli categories.