## 1. Scope

**Store:** m041  
**Date of interest:** 2024-05-12 (Sunday, "weekend" holiday context)  
**Signal metric:** Trailing 7-day percent change  
**Signal classification:** **LIFT** (current +77.3% vs trailing-7d avg, exceeding +30% threshold)

---

## 2. Findings

**Signal triggers as "LIFT" – confirmed valid.**

| Comparison | Value | Interpretation |
|---|---|---|
| **Current Sales** | **146.4** | Highest in the 14-day lookback window |
| **Prior Day (Sat)** | 89.0 | +64.5% DoD – sharp single-day acceleration |
| **Trailing 7d Avg** | 82.6 | +77.3% vs trailing avg – well above the 30% lift threshold |
| **Same Weekday Avg (4w)** | 102.4 | +43.0% vs typical Sundays – strong above-baseline |

**Sales shape observations:**

- The store had a visible **Labor Day period bump** (May 1–5) where daily sales ranged 70–116, peaking at 116.5 on Sunday May 5.
- After Labor Day, sales **settled down** (May 6–10 range: 57–84) with a notable dip to 56.7 on May 9 (Thursday).
- Starting May 11 (Sat = 89.0), a **clear upward leg begins**, culminating in the 146.4 print on May 12.
- The current Sunday (146.4) **exceeds the prior holiday Sunday** (May 5 = 116.5) by **+25.7%** – the recent trajectory is steeper than the Labor Day peak.

**Baseline comparisons:**

- **Trailing 7d avg (82.6):** Very soft baseline – the 7-day window includes the post-holiday lull (May 6–10 low sales), making the percentage lift appear larger.
- **Same-weekday 4w avg (102.4):** A more robust baseline. The +43% lift above typical Sunday performance is still a strong signal but less dramatic than the trailing-7d view.

**Summary:** The lift signal is real. The recent shape shows sales recovering from a post-Labor-Day trough and accelerating sharply into May 12. The day-over-day jump from 89 to 146 is the most abrupt move in the 14-day window.

---

## 3. Caveats

- The **trailing-7d baseline (82.6)** is depressed because it includes several low-volume post-holiday weekdays (May 6–10). This inflates the percentage lift. The same-weekday baseline (102.4) is a more conservative reference and still shows a strong +43% signal.
- The signal is based on **trailing_7d_pct_change** as the primary metric. No alternative signal metrics (e.g., DoD, same-weekday) were flagged as crossing thresholds independently, but all three comparisons (DoD, trailing-7d, same-weekday) point in the same direction: **sales are notably up.**
- No tool evidence on **stockout, discount, activity, weather, or peer performance** was available – any attribution to those factors is outside scope.