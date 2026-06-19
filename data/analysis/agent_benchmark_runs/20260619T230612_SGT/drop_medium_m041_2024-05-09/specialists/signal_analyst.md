## 1. Scope

Store: **m041** | Date: **2024-05-09** (Thursday, normal weekday)
Tools used: signal evidence, 14-day sales history, and baseline comparisons.

---

## 2. Findings

**Signal Trigger: DROP**
- The trailing-7-day % change is **-33.0%**, well past the drop threshold of -20%.
- Current sales: **56.67** (vs. trailing 7d avg: 84.64, previous day: 75.30).

**Day-over-Day Comparison**
- Sales fell **-24.7%** from 75.30 yesterday (Wed) to 56.67 today (Thu). That's a sharp single-day decline.

**vs. Trailing 7-Day Average**
- Today's sales are **33.0% below** the trailing 7d avg of 84.64 — a pronounced drop.

**vs. Same Weekday (4-Week) Baseline**
- Today (Thu) beat the average Thursday from the prior 4 weeks (56.67 vs. 67.30) by **-15.8%**. So even compared to the 4-week Thursday norm, sales are low.

**Recent Sales Shape**
Looking at the 14-day history:

| Period | Shape |
|---|---|
| Last week (Apr 25 - May 1) | Mixed, with a spike on May 1 (94.70, Labor Day period start). |
| Labor Day period (May 1-5) | Elevated sales (peaked at 116.48 on May 5). May have been holiday-driven lift. |
| Post-holiday (May 6-9) | **Steady decline**: 83.51 → 79.94 → 75.30 → **56.67**. |

The pattern shows a clear **downward staircase** after the Labor Day period ended. Sales went from holiday-elevated levels back down, and then today dropped even further.

**Baseline Comparisons Summary**

| Baseline | Value | vs. Current (56.67) |
|---|---|---|
| Previous day (May 8) | 75.30 | -24.7% |
| Trailing 7d avg | 84.64 | -33.0% |
| Same-weekday 4w avg | 67.30 | -15.8% |

Today's sales underperform **all three baselines** — the drop is not an artifact of a single comparison.

---

## 3. Caveats

- The trailing-7d and trailing-7d-avg baselines are **skewed upward** by the Labor Day period (May 1-5 had elevated sales). The % drop vs. those baselines is partly a post-holiday normalization effect.
- The same-weekday 4w avg (67.30) is a cleaner "normal Thursday" comparison — sales are 15.8% below it, which is notable but less extreme than the -33% headline.
- No evidence on stockout, discount, activity, or weather was available or used. The signal is statistically valid but causal attribution would require those inputs.
- The holiday flag for May 1-5 was "labor_day_period" — this is the only notable calendar effect in the window. May 9 itself is flagged as a normal weekday.