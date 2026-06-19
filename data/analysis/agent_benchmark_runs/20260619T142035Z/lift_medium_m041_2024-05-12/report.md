Excellent! I now have a comprehensive picture. Let me compile the analysis.

---

## Root Cause Analysis — Store m041 | 2024-05-12

---

### 1. Trigger

**Signal: LIFT** — Sales of **$146.40** significantly exceeded expectations:
- **Day-over-day**: +64.5% vs prior day ($89.00)
- **Trailing 7-day avg**: +77.3% ($82.56 → $146.40)
- **Same-weekday 4-week avg**: +43.0% ($102.37 → $146.40)

This is a strong positive outlier — the store's best day in the trailing 7-day window by a wide margin.

---

### 2. Likely Drivers

1. **🥇 Promotional Activity (Primary Driver)** — A heavy promotional calendar is in effect with 46% of products on promotion and 39% of sales coming from promoted items. This is the strongest and most direct lever.
2. **🥈 Discounting** — 61% of products are discounted with an average discount depth of ~10% off (avg_discount = 0.8997). No deep discounts (0%), but broad, shallow discounting is supporting the lift.
3. **🥉 Weekend / Calendar** — Sunday is a naturally higher-volume day. The prior Sunday (May 5) also saw a lift ($116.48), but the current Sunday is **$29.92 higher** — so weekend alone doesn't explain it.
4. **Weather** — Mild temperature (22°C / ~72°F) and moderate rain (0.68 mm precip) — nothing extreme that would drive unusual traffic. Unlikely to be a material driver.

---

### 3. Evidence

| Metric | May 12 (Sun) | May 5 (Prior Sun) | Δ |
|---|---|---|---|
| **Total Sales** | **$146.40** | $116.48 | **+$29.92 (+25.7%)** |
| **Activity Product Rate** | **46.4%** | 42.0% | +4.4pp |
| **Activity Sales Share** | **39.4%** | 35.9% | +3.5pp |
| **Avg Discount** | 0.8997 (~10% off) | 0.9156 (~8.4% off) | Slightly steeper |
| **Discounted Product Rate** | **60.9%** | 53.6% | +7.3pp |
| **Stockout Product Rate** | 55.1% | 59.4% | -4.3pp (improved) |
| **Avg Stockout Hours** | 4.33 hrs | 4.16 hrs | Slightly higher |

**Key observations:**

- **Promotional coverage increased** from 42.0% to 46.4% of products on activity, and the share of sales from these activities rose from 35.9% to 39.4%. This is the clearest signal of an intentional commercial push.
- **Discount breadth expanded** — 60.9% of products were discounted on May 12 vs 53.6% on May 5 (the prior Sunday). The average discount also deepened slightly.
- **Stockouts improved slightly** — 55.1% of products experienced a stockout vs 59.4% on May 5. This suggests better availability may have enabled the higher sales, though stockout levels are still high.
- **Sales rank context** — Store m041 ranked **#1 among its tier** (tier "m", 5 stores) and **#6 overall** (15 stores) on this day, well above its tier average ($122.52).

---

### 4. Caveats

- **Stockout ambiguity**: The stockout rate (55%) is still very high despite being lower than prior Sunday. Some sales may have been *capped* by stockouts — the lift could have been even larger with fuller availability.
- **Activity vs discount overlap**: The 60.9% discounted-product rate is broader than the 46.4% activity-product rate. This means some items were discounted outside of formal promotional activity, muddying attribution between "discount-driven" vs "activity-driven" sales.
- **No deep discounts**: Deep discount rate is 0%, suggesting this is not a clearance event but rather a broad, mild promotional push.
- **Previous Sunday also elevated**: May 5 was already a strong Sunday ($116.48, +28% vs its trailing 7-day avg of $77.06), so the "Sunday effect" is partly baked in. The incremental lift on May 12 is the real story.

---

### 5. Suggested Next Checks

1. **Check which categories drove the activity lift** — Drill into category-level sales to see if a specific department (e.g., dairy, snacks, beverages) carried the promotion.
2. **Check competitor calendar** — See if a local competitor had a gap or closure, potentially redirecting traffic to store m041.
3. **Investigate the high stockout rate** — Even though it improved vs May 5, 55% stockout is high. Determine if critical top-selling items were unavailable and whether replenishment is an issue.
4. **Check foot traffic / transaction count** — Determine if the lift came from more customers or higher basket size. This distinguishes traffic-driven vs. price-driven lift.
5. **Review 4-week same-weekday trend** — Compare May 12 to the other recent Sundays (April 21, April 28, May 5) to see if this is part of a growing trend or a one-off spike.