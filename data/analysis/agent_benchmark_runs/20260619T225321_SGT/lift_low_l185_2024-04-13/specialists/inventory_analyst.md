## 1. Scope

Store **l185** | Date **2024-04-13** (Saturday, weekend). Analyzed stockout intensity and sales deviation vs. recent history.

---

## 2. Findings

### Sales Performance
- **Current sales**: $49.4 — **+54%** above the trailing 7-day average ($32.0) and **+38%** vs. the prior day (Friday, $35.7).
- This is well above any recent daily total and suggests a demand spike (likely weekend-driven, possibly amplified by lingering Qingming-period foot traffic or a local promo).

### Stockout Conditions (Alarming)
| Metric | Value | Interpretation |
|---|---|---|
| Avg stockout hours | **5.85 hrs** | Products were unavailable for nearly 6 hours on average |
| Stockout product rate | **68.3%** | ~68% of tracked products hit a stockout at some point |
| Severe stockout rate | **39.0%** | ~39% of products had severe/prolonged stockouts |
| Full stockout rate | **2.4%** | Only ~2.4% were fully out all day — most eventually recovered |
| Hourly peak stockout rate | **65.9%** | At peak hour(s), nearly 2/3 of products were unavailable |

### Cause vs. Consequence Ambiguity

- **The sales spike ($49.4) and the stockout severity (68% of products hit) co-occurred.** This creates a typical chicken-and-egg ambiguity:
  - **Hypothesis A (demand-driven):** Unusually high customer traffic / demand exhausted inventory faster than planned, driving stockout rates up. The inventory team may not have forecasted the Saturday + post-Qingming tail.
  - **Hypothesis B (supply-driven):** A pre-existing replenishment gap or delivery miss caused broad shortages, which paradoxically could have *depressed* sales further — i.e., actual demand was even higher than $49.4.
- Given that sales still hit $49.4 (well above the 7-day avg), Hypothesis A seems more plausible for the *direction* of the move: strong demand overwhelmed shelf availability. However, it is likely that **sales would have been even higher** if stockout hours were lower — meaning the true demand signal is understated.

### Key Supporting Detail
- The peak hourly stockout rate (65.9%) means that during the busiest hours, two out of every three products were unavailable. This is a **critical service level failure** and indicates a systemic availability breakdown on a high-traffic day.

---

## 3. Caveats

- **No same-weekday historical baseline** (4-week Saturday average is null), so we cannot say whether $49.4 is exceptional relative to other Saturdays. It *is* exceptional vs. the rolling average, but that includes lower-weekday comparisons.
- **Stockout data is product-level aggregate** — we don't know which departments or top-selling items were affected. A few high-velocity SKUs being out could drive most of the sales impact.
- **Cannot infer causality** from co-occurrence alone. Stockout rates may be a *result* of the sales spike rather than a root cause of it.
- **Full stockout rate is low (2.4%)** — most products came back in stock during the day, suggesting the store had inventory but couldn't keep shelves filled fast enough during peak hours (replenishment/shelf-staffing issue, not a DC shortage).
- **Recommendation for deeper RCA:** Drill into hourly stockout patterns vs. hourly sales; check the top-10 selling SKUs' stockout windows; review if store received a delivery that day and when it was shelved.