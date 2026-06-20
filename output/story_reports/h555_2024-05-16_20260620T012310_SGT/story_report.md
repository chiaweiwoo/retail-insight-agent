# RCA Report: Store h555 — 2024-05-16 Sales Drop

## Executive Takeaway

**Sales dropped 24.9% below trailing-7-day average — likely a one-day operational disruption (broad stockout event) layered on moderate structural underperformance. No escalation warranted, but two critical follow-ups needed: (1) compare stockout metrics to the prior 7 days to confirm "elevation," and (2) cross-reference whether the 38.8% promotional rate overlapped with the 36.7% stockout rate (promotions on unavailable items are meaningless).**

The ~$44 one-day gap is low-to-moderate materiality at store level; h555 remains 28% above fleet average. The finance lens classifies this as likely one-off, with a structural concern only if stockout rates persist over the next 3 days.

---

## Why This Day Triggered Review

**Signal: −24.9% vs trailing-7-day average, exceeding the −20% threshold by ~5 percentage points.**

The **sales_analyst** (first to examine) confirmed this is a statistically meaningful outlier: 2.0 standard deviations below the store's normal mean of 174.37 (stddev 21.29). Current sales of 131.91 on Thursday May 16 represent the continuation of a 4-day decline from a peak of 217.71 on Sunday May 12.

The **analyst correctly rated this "inconclusive, low confidence"** — the drop is real and large, but coincides with a weekend-to-weekday transition following a holiday period. Natural mean reversion is plausible but insufficient alone.

---

## How The Analysis Unfolded

### Layer 1: Sales magnitude — confirmed

The signal was real. No further work needed on the "what." The question became the "why."

### Layer 2: Market context — store-specific problem emerges

The **market_analyst** pulled peer comparisons, calendar data, and weather.

**Evidence:**
- h555 ranked **5th out of 5** within its "h-tier" peer group (tier average: 161.29)
- The **weather was mild**: 23.2°C, 1.89mm rain, 70.4% humidity — plausible as a minor dampener, but not a primary driver
- Calendar: Normal Thursday, no holiday

**Interpretation:** The drop is store-specific, not market-wide. Weather is "ruled out" as primary driver — though the analyst overstated confidence here (see below).

### Layer 3: Operations — stockouts are the strongest candidate

The **ops_analyst** examined availability data.

**Evidence:**
- **36.7% of products** experienced some stockout
- **17.7% had severe stockouts** (>4 hours)
- **Peak hourly stockout rate**: 34.0%
- **Average duration**: 2.96 hours

**Interpretation:** "Stockout metrics are elevated across the board." The breadth (36.7% of products) is unusually high — enough that a pure demand-side explanation is less parsimonious. But the analyst correctly caveated: lower traffic could inflate stockout rates, and stockouts reduce sales. The direction could run either way.

**Key gap flagged by the critic:** "Elevated" is asserted without a baseline. No prior-day or store-average stockout rate was provided. The raw numbers look high, but the system cannot prove they're abnormal without comparison.

### Layer 4: Commercial — promotions are happening but can't be assessed

The **commercial_analyst** reviewed discount and activity data.

**Evidence:**
- **38.8% of products** were on promotion
- **Average discount**: ∼7.6%
- **Deep discount rate**: 0.0%
- **Activity sales share**: 38.2%

**Interpretation:** "Promotional activity is present but sales are weak — suggesting the promotion is failing to drive traffic."

**Critical flaw caught by the critic:** This is a correlation/causation error. Weak sales concurrent with promotion does not prove the promotion *failed*. The promotion may have prevented an even larger drop, or it may have been a response to an already-declining trend. The data cannot distinguish.

### The unresolved tension (not caught by any analyst)

The **coordinator** spotted the critical interaction: **If 36.7% of products were stocked out and 38.8% were on promotion, there may be significant overlap.** Promotions on unavailable items are meaningless. Neither the ops_analyst nor the commercial_analyst addressed this.

This is the single most important gap to close before any causal story is endorsed.

---

## Where The System Challenged Itself

### Critic audit findings

The **critic** reviewed each analyst's claims against the evidence and found multiple overstatements:

1. **Market_analyst:** Claimed weather was "ruled out" — downgraded. 1.89mm rain and 70% humidity on a mild day *could* have a mild dampening effect, but without foot-traffic data, the magnitude is inconclusive.

2. **Ops_analyst:** "Elevated" stockouts are asserted without temporal baseline — flagged as unsupported. The raw numbers (36.7%, 17.7% severe) are high in absolute terms, but "elevated" implies a comparison that wasn't provided.

3. **Commercial_analyst:** The "promotion is failing" claim — downgraded. Correlation/causation: weak sales with promotion doesn't prove promotion failed. Could have prevented worse, or been a response to decline.

4. **Deep discount definition:** 0.0% deep discount rate is reported but the threshold for "deep" is undefined.

### Calibration note

The critic recommended a downward calibration:
- **sales_analyst** correctly rated "inconclusive, low confidence" — should anchor the synthesis
- The other three should calibrate from "medium" to at most "low-medium" given missing traffic data, replenishment timing, and promotion-type granularity

### Finance lens

The **controller** classified this as:
- **One-off indicators**: Post-holiday mean reversion (recurring pattern); stockout at 36.7% is unusually broad for a single day (suggests missed delivery or system error, not chronic flaw)
- **Structural indicators**: h555 ranks 5/5 in its tier (ongoing competitive disadvantage); no baseline for normal stockout rate
- **Verdict**: Likely one-off operational disruption layered on underlying moderate structural underperformance

---

## Final Decision

**No escalation. Action items, not causal endorsement.**

1. **Resolve stockout baseline**: Compare May 16 stockout metrics to (a) prior 7-day average for h555, and (b) same-day h-tier average
2. **Cross-reference stockout × promotion**: What share of the 38.8% promoted products were among the 36.7% stocked out? If >50% overlap, availability failure is the primary driver by definition
3. **Obtain foot-traffic data**: If traffic is normal → stockouts likely causal. If traffic is also down → demand-side factors
4. **Check delivery/replenishment schedule**: Was there a missed delivery on May 15 or early May 16? This would explain the 3-day accelerating decline pattern

**Confidence: medium** — the evidence supports a stockout-driven hypothesis, but the missing baseline and unresolved promotion-overlap introduce material uncertainty. The critic's calibration note is accepted: three of four analysts overstated their causal claims, and the lowest-confidence verdict (sales_analyst's "inconclusive") should anchor the overall assessment.