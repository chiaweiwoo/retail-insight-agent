## MEMORANDUM — Signal & Baseline Review

**Store:** l185  
**Date:** 2024-04-13 (Saturday)  
**Analyst Focus:** Signal validity, baseline comparisons, recent sales shape

---

### 1. Scope

Review the trailing-7d percent change signal for store l185 on 2024-04-13 to assess whether the flagged **lift** is valid relative to available baselines and recent sales trajectory. No activity, stockout, discount, or peer data was consulted.

---

### 2. Findings

| Metric | Value |
|---|---|
| **Current Sales** | 49.4 |
| **Previous Day Sales** | 35.7 (+38.4% DoD) |
| **Trailing 7d Avg Sales** | 32.03 |
| **Trailing 7d % Change** | **+54.3%** (signal: **lift**, threshold: >=30%) |
| **Same Weekday 4w Avg** | Not available (null) |

**Signal Validity:** The `trailing_7d_pct_change` of +54.3% exceeds the lift threshold of 30%. The signal is **valid**. Additionally, day-over-day growth of +38.4% confirms upward momentum into the signal date.

**Baseline Context:**
- Current sales (49.4) are **54% above** the trailing-7d average (32.03).
- Current sales are **38% above** the previous day (35.7).
- No 4-week same-weekday baseline is available for cross-check.

**Recent Sales Shape (last 14 days):**
The last 2 weeks show a **clear upward trend** driven by the recent Qingming period (Apr 4–6) and elevated weekend sales:
- **Mar 30–Apr 6:** Stepped up from 33.9 (Sat) → 41.7 (Sun) → mid-20s weekdays → **Qingming bump** (38.5, 34.5, 41.5 on Apr 4–6).
- **Apr 7–12:** Post-holiday weekdays settled around 27.8–30.7, then a noticeable ramp: 29.18 (Thu) → 35.7 (Fri) → **49.4 (Sat, signal date).**
- The two most recent days (Apr 12→13) show the steepest sequential increase in the window.

**Signal Interpretation:** The lift signal reflects genuine recent elevation. Sales on 2024-04-13 are the **highest in the 14-day window**, and Friday's 35.7 already exceeded the trailing average. However, note that the trailing-7d average (32.03) includes the lower weekday post-Qingming numbers, which amplifies the % change. The signal is **credible but partly mechanical** — it reflects both a real Saturday lift and a depressed weekday baseline.

---

### 3. Caveats

- **No 4-week same-weekday baseline** was available; cannot assess if 49.4 is normal for a Saturday versus a broader historical pattern.
- The trailing-7d average (32.03) includes lower post-holiday weekdays. Using a longer baseline or same-day-of-week baseline would provide more robust context.
- This analysis is purely signal- and sales-shape based. Any stockout, promotion, or competitive factors are outside scope.