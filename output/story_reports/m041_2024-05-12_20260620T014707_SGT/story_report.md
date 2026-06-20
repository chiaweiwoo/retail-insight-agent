# RCA Report — Store m041, 2024-05-12

## Executive Takeaway

**Store m041 sold 146.4 units on May 12 — its highest single-day total in the 90-day dataset.** This represents a +77% lift vs its trailing 7-day average. **No causal attribution is possible.** The spike is real, but why it happened is unknown. The immediate recommended action is a **data quality audit** to confirm the figure isn't a POS error, followed by a check of the following week for persistence before any process changes.

**Do not escalate. Do not change the forecast.**

---

## Why This Day Triggered Review

The system flagged store m041 on Sunday, May 12, because its trailing 7-day sales change crossed the 30% lift threshold. The numbers:

| Metric | Value |
|---|---|
| Day's sales | 146.4 units |
| Previous day | 89.0 |
| Trailing 7-day avg | 82.56 |
| Same-weekday 4-week avg | 102.37 |
| Day-over-day change | +64.5% |
| Trailing 7-day change | +77.3% |
| vs 4-week Sunday avg | +43.0% |

The ramp accelerated sharply over the final four days: 56.67 → 77.01 → 89.0 → **146.4**.

---

## How The Analysis Unfolded

### Layer 1: Sales Analyst — Confirming the Signal

The **sales_analyst** pulled the signal evidence, then fetched sales context for the 14-day lookback and 90-day bounds. Key findings:
- 146.4 is the **dataset maximum** in the 90-day window (previous max: 116.48)
- Sales rank: #1 in the dataset
- The store's normal max is 146.4 — but the critic later catches this: *"Claiming it as the store's historical maximum without longer data is speculative. Downgrade to 'observed dataset max.'"*

**Tool used:** `get_signal_evidence`, `get_sales_context` (twice)

### Layer 2: Market Analyst — Fleet Context and Calendar

The **market_analyst** examined whether this was an isolated event or part of a wider pattern. Using calendar/weather data and peer comparisons:

- Fleet average on May 12: **140.23 units** (fleet daily mean is 103.06)
- Tier 'm' stores averaged 122.52
- m041 ranked **#1 among tier 'm'** stores and **#6 overall** in the fleet
- m041 was **3.0 standard deviations** above its own mean (146.4 vs 84.41 ± 20.51)
- Weather: neutral — light precipitation, moderate temperature

The analyst hypothesized a "post-holiday-weekend Sunday boost." **The critic flagged this as unsupported** — the holiday label (labor_day_period) applied to the *prior* Sunday (May 5), not May 12. The fleet-wide lift is real but unexplained.

**Verdict:** Contributing (medium confidence)
**Tool used:** `get_calendar_weather_context`, `get_peer_store_context`, `get_sales_context`

### Layer 3: Ops Analyst — Stockout Assessment

The **ops_analyst** dug into stockout data, making 8 calls to get full context. Key findings:

- Average stockout hours: 4.33
- Stockout product rate: 55.07%
- **Severe stockout rate: 27.54%** — highest in the 6-day window (prior range 17-26%)
- Full stockout product rate: 2.9%

**The analyst's interpretation:** Stockouts are a *consequence* of high demand, not a cause. The sales spike is sharply upward despite stockouts, suggesting demand-pull depleting inventory.

**The critic pushed back:** *"Without opening inventory levels, we cannot distinguish between demand-driven depletion, promotional drawdown of already-low stock, or a pre-existing stockout condition. Verdict 'ruled_out' is too strong — 'not supported as explanatory' would be more accurate."*

**Verdict:** Ruled_out (medium confidence → critic says low)
**Tool used:** `get_sales_context`, `get_stockout_context` (8 times)

### Layer 4: Commercial Analyst — Promotion Analysis

The **commercial_analyst** examined discount and activity data:
- Average discount: ~10% off (0.8997 price ratio)
- **60.87% of products discounted** — broad coverage
- **0% deep discount** rate (none below 10%)
- Activity product rate: 46.38%
- Activity sales share: 39.41%

**The analyst's interpretation:** The broad, shallow promotional event drove the spike.

**The critic demolished this causal claim:** *"This is equally consistent with normal Sunday traffic buying promoted items incidentally, the promotion being a reaction to high traffic, or the promotion having existed for weeks and only 'working' because of unrelated demand surge. No pre/post comparison, no control group. High confidence is unwarranted."*

**Verdict:** Contributing (high confidence → critic says low)
**Tool used:** `get_sales_context`, `get_discount_context`, `get_activity_context`

---

## Where The System Challenged Itself

The critic and controller provided the most valuable corrections:

### Critic's Key Challenges

1. **Overstated "historical max"** — corrected to "observed dataset maximum"

2. **Unsupported causal chain** — the "post-holiday" explanation for the fleet-wide lift is correlation presented as causation

3. **Overconfident stockout verdict** — "ruled_out" should be "not supported as explanatory"

4. **Causal leap on promotions** — correlation ≠ causation; no temporal alignment demonstrated

5. **Missing interaction** — ops says stockouts capped demand, commercial says promotions drove it. These viewpoints are compatible (promotions drove demand that depleted stock), but no memo cross-references this

6. **Missing: product-mix data** — if stockout items were the promoted items, that's a different story than separate categories

7. **Missing: data anomaly check** — "A single-day spike to the dataset maximum with no clear cause should trigger a data quality check. Has this been ruled out?"

### Calibration Downgrades

| Analyst | Stated Confidence | Appropriate Confidence |
|---|---|---|
| sales_analyst | high | medium-high (right about the number, wrong about "historical max") |
| market_analyst | medium | low-medium (post-holiday inference unsupported) |
| ops_analyst | medium | low (overconfident "ruled_out" verdict) |
| commercial_analyst | high | low (causal leap from correlation) |

### Controller's Financial Lens

The controller added a margin perspective:
- **If Hypothesis A (promotion-driven):** The 60.9% discount rate directly compresses unit margins on 39.4% of sales dollars. Net profitability of incremental volume is uncertain.
- **If Hypothesis B (external demand surge):** Margins on full-price items are protected, making the spike highly profitable.
- **Critical missing link: product-mix.** Were stockout items high-margin or low-margin?
- **Verdict: almost certainly one-off, not structural.** The synchronized fleet-wide spike rules out a permanent shift. Recommended action: data quality audit.

---

## Final Decision

**Headline:** Store m041 hit 146.4 units (dataset max, +73.5% vs mean) — fleet also spiked to 140.23; **no causal attribution possible.**

**Pattern:** One-off spike (dataset maximum, sharp 4-day ramp, fleet-wide synchronized lift)

**Materiality:** High — +62 units vs store average on a single day

**Confidence:** Medium

**Action:**
1. ✅ Initiate data quality audit to confirm 146.4 is not a POS error
2. ✅ Check following week (May 13 onward) for persistence before any process change
3. ❌ Do not escalate — this does not warrant a process change or revised forecast

**Escalate:** No