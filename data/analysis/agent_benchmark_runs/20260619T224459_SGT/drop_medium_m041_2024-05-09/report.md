Now I have a comprehensive picture. Let me compile the report.

---

## Root Cause Analysis Report — Store m041, 2024-05-09

### 1. Trigger

**Signal: Drop**  
The signal triggered on a **-33.0% trailing-7d change** (threshold: <= -20%).  
Current sales: **$56.67** vs trailing 7-day avg of **$84.64**.  

Day-over-day: **-24.7%** (from $75.30 on May 8).  
Versus same-weekday-4wk average: **-15.8%** (from $67.30).  

The store is a **Thursday (normal weekday, no holiday)** with light precipitation (0.47 in) and mild temperatures (21.5 C). Weather alone is unlikely to explain a >30% decline.

---

### 2. Likely Drivers

**Primary driver: Chronic & worsening stockout problems.**

- Stockouts on May 9 were widespread: **37.7% of products** experienced some stockout, **15.9% experienced severe stockouts**, and **8.7% were fully stocked out**. Average stockout duration was ~3 hours.
- However, comparing to the prior two days, stockouts were actually **slightly better** on May 9 than on May 8 or May 7:
  - May 7: 68.1% of products affected, 17.4% severe, avg 3.9 hrs
  - May 8: 59.4% of products affected, 21.7% severe, avg 4.1 hrs
  - May 9: 37.7% of products affected, 15.9% severe, avg 3.0 hrs
- So stockouts improved but were still **elevated vs a healthy baseline**, and the sales continued to fall. This suggests either:
  1. The damage from prior days' deep stockouts carried forward (lost customer trips, depleted low-inventory items further).
  2. Fresh stockout issues on May 9 (still at 37.7%) continued to suppress sales.

**Secondary driver: Post-holiday demand normalization.**

- Looking at the 10-day history, sales were elevated during the **Labor Day period** (May 1–5):
  - May 1 (Wed): $94.70
  - May 2 (Thu): $70.07
  - May 3 (Fri): $72.67
  - May 4 (Sat): $94.50
  - May 5 (Sun): $116.48
- After Labor Day period ended, sales dropped to $83.51 (May 6), $79.94 (May 7), $75.30 (May 8), and finally $56.67 (May 9).
- The **trailing-7d average ($84.64)** is inflated by the holiday period, making the drop look steeper than a pure non-holiday comparison would suggest. The same-weekday-4wk average ($67.30) is a more sober baseline, and relative to that the drop is -15.8%, which is still material but less dramatic.

**Tertiary factor: Peer underperformance / tier context.**

- Store m041 is in tier **"m"** (smaller stores). Its $56.67 is **well below** the tier average of $73.12 on May 9, and ranks **5th out of 5** stores in its tier.
- It also ranks **10th out of 15** stores overall, with the overall average at $92.26. This indicates the store is underperforming relative to peers of similar size, suggesting a store-local issue (stockouts) rather than a chain-wide demand shock.

**Discount/Activity context — not a driver.**

- Average discount: 0.93 (i.e., ~7% off on average across all products).
- 46.4% of products discounted, 40.6% on promotion. No deep discounts.
- These figures are not extreme enough to explain a demand drop (if anything, promotions should support sales). This rules out a sudden pricing-driven decline.

---

### 3. Evidence

| Evidence | Supports |
|---|---|
| Signal reads "drop", -33% trailing-7d, -24.7% DoD | Trigger is genuine |
| Stockout product rate = 37.7%, severe = 15.9% on May 9 | Stockout pressure remains high |
| Prior days had even worse stockouts (May 7: 68.1%, May 8: 59.4%) | Chronic stockout problem that worsened then partially eased |
| Sales declined from $116.48 (Labor Day Sun) to $56.67 (post-holiday Thu) | Holiday baseline inflation amplifies the drop metric |
| Same-weekday-4w average is $67.30 — sales of $56.67 is -15.8% below that | Genuine drop, but not as extreme as -33% headline |
| Store ranks 5/5 in its tier, 10/15 overall | Store-specific issue, not a chain-wide pattern |
| Discount rate is normal to modestly elevated | Pricing/promotions not the cause |
| Thursday, normal weekday, mild weather (0.47 in rain, 21.5 C) | Calendar/weather unlikely to be the primary driver |

---

### 4. Caveats

- **Stockout direction is mixed.** Stockouts improved from May 7/8 to May 9, yet sales fell further. This could mean the stockout problem already lost customers on prior days and they did not return on May 9. Alternatively, the stockout levels on May 9 (37.7% of products) were still high enough to suppress sales. Without customer traffic data, it is hard to distinguish between "lost traffic from prior stockouts" and "continued on-the-day stockout impact."
- **Holiday carryover vs. true weakness.** The Labor Day period (May 1–5) may have pulled forward demand or created a natural post-holiday lull. The -33% trailing-7d metric is partly an artifact of comparing to inflated holiday sales. The same-weekday-4w baseline ($67.30) suggests a real but smaller drop of ~16%.
- **No direct competitor or foot traffic data** is available. It is possible that nearby competition or local events also contributed.

---

### 5. Suggested Next Checks

1. **Investigate root cause of stockouts.** Check whether the chronic stockouts on May 7–9 are due to upstream supply chain issues, ordering errors, or delivery delays. Look at which categories/products were most affected.
2. **Pull foot traffic / transaction count data.** If traffic dropped sharply on May 9, it suggests customers were lost on prior days. If transactions were normal but basket size dropped, it suggests on-the-day availability issues.
3. **Compare to other tier-m stores with similar stockout profiles.** Are other stores experiencing the same pattern, or is m041 an outlier?
4. **Check inventory replenishment logs for May 5–9.** Did a delivery fail or arrive late? Was there a shortage in key high-margin / high-traffic categories?
5. **Monitor the next several days.** If stockouts resolve and sales rebound toward the $67–75 range, the primary cause was likely stockout-driven. If sales remain low, other factors (e.g., permanent customer loss, competition) may be at play.