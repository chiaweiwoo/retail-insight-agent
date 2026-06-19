Now I have a comprehensive picture. Let me compile the analysis.

## RCA Report: Store l165 – 2024-05-16

### 1. Trigger

**Drop** – The trailing 7-day average sales declined by **-31.7%** (from $37.17 to $25.38), far exceeding the -20% drop threshold. The day-over-day change from 2024-05-15 was also a sharp **-24.2%** ($33.50 to $25.38). The same-weekday (Thursday) 4-week comparison shows a milder decline of **-9.5%** (from $28.05 to $25.38), indicating the current day is low even relative to its typical Thursday baseline.

### 2. Likely Drivers

1. **Stockouts** – Most probable primary driver. Stockout metrics are elevated (27.3% of products had stockout events; 11.4% severe; peak hourly rate of 36.4%). This directly suppresses sales and aligns with the sudden day-over-day drop.

2. **Calendar / Weather** – Minor contributor, not a primary cause. 2024-05-16 is a normal Thursday with no holiday. However, 1.89 mm of precipitation and moderate temperature (23.2°C) may have a small dampening effect on foot traffic, but nothing severe.

3. **Discount & Activity** – Not likely a driver of the *drop*. Discount penetration is moderate (47.8% of products discounted, average discount ~8% off), and promotional activity covers 40.9% of products with 39.4% of sales share. These factors would ordinarily *support* sales, so their presence does not explain the decline.

4. **Peer/Store-tier Context** – Store l165 is in tier "L" (lowest sales tier). Its $25.38 is below the tier average of $29.84, ranking 5th out of 5 in its tier. This confirms the underperformance is not merely a tier-wide trend – peers in the same tier averaged higher sales. The store also ranks last (15th out of 15) among all stores.

### 3. Evidence

| Evidence | Detail |
|---|---|
| **Sales signal** | Current = $25.38; Trailing 7d avg = $37.17 (-31.7%); Prior day = $33.50 (-24.2%); Same-weekday 4wk avg = $28.05 (-9.5%) |
| **Stockouts** | 27.3% product rate; 11.4% severe; avg 1.86 hours of stockout per product; peak hourly rate 36.4% |
| **Weather** | 1.89 mm precipitation; 23.2°C; typical for season, no extreme conditions |
| **Calendar** | Normal Thursday; no holiday |
| **Discounts** | 47.8% of products discounted; avg discount 0.92 factor (~8% off); no deep discounts |
| **Promo activity** | 40.9% product rate; 39.4% sales share – moderate promo presence |
| **Peer comparison** | Tier avg = $29.84; l165 at $25.38 is 5th of 5 in tier; 15th of 15 overall |

The stockout evidence is the most salient anomaly. The store had over a quarter of its products experience stockout on this day, with more than 1 in 10 products in severe stockout. This is consistent with a demand-fulfillment failure that would suppress sales below normal levels.

### 4. Caveats

- **Correlation vs. causation**: Stockouts could be both a cause and a consequence. If there was a demand surge earlier in the day that depleted inventory, the stockouts could partially reflect strong demand rather than poor replenishment. However, the overall sales being low suggests stockouts reduced total transaction volume rather than being caused by excessive demand.
- **Stockout timing**: The data shows average stockout hours and peak rates but not the sequence – whether stockouts occurred early (choking sales all day) or late (after most sales were done).
- **No deep discounts**: The absence of deep discounts (0.0%) means the store did not use aggressive markdowns to clear inventory, but this is a neutral observation, not a cause of the drop.
- **Precipitation (1.89 mm)**: Light rain may reduce foot traffic slightly, but it is mild enough that it is unlikely to explain a ~25% day-over-day drop on its own.
- **Historical volatility**: The same weekday 4-week baseline ($28.05) is itself lower than the trailing 7d avg ($37.17), suggesting Thursdays have been a softer day historically. The drop relative to that baseline is only -9.5%, which is notable but less dramatic than the trailing-7d view.

### 5. Suggested Next Checks

1. **Investigate specific stockout SKUs/categories** – Identify which products or categories were heavily stocked out (especially severe stockouts at 11.4%). See if high-velocity or high-margin items were affected.
2. **Check stockout timing pattern** – Determine whether stockouts occurred early in the day (suggesting replenishment failure) or late (suggesting demand exceeded forecast). Hourly sales-by-hour data would clarify this.
3. **Review inventory replenishment logs** – Look for delivery delays, order errors, or supply chain issues specific to store l165 for the days leading up to 2024-05-16.
4. **Examine the previous day (2024-05-15)** – Sales on the prior day were $33.50, which is near the trailing 7d avg. Checking stockouts or anomalies on the 15th could reveal if inventory issues started earlier.
5. **Analyze foot traffic / POS transaction counts** – If available, transaction count vs. average basket size would help distinguish between fewer customers (traffic issue) vs. lower basket value (stockout-driven substitution or reduced choice).