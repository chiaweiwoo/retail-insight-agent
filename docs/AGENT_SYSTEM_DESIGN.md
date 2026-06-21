# Agent System Design Guide

This document is the deeper technical guide for learning how to design a strong agentic system.

It is intentionally more advanced than the overview. The goal is not just to explain this project, but to teach the design habits behind a great agentic system: where structure should live, where the model should think, how to keep the system honest, and how to evolve it without losing control.

## Table of Contents

1. What a great agentic system actually is
2. Workflow vs agent vs hybrid
3. The design goals for this project
4. The core building blocks
5. Control loop design
6. Planning design
7. Tooling design
8. Evidence and claim design
9. Memory design
10. Critic and evaluator design
11. Decision design
12. Data and schema design
13. Observability and debugging
14. Testing strategy
15. Common failure modes
16. What makes a system truly improve over time
17. Design heuristics to keep

## What a great agentic system actually is

A great agentic system is not just "an LLM with tools."

It is a system that can:

- understand a task boundary
- decide what information it needs
- gather evidence in a disciplined way
- revise its plan when the first idea is weak
- separate observation from inference
- stop when enough evidence exists
- say "unknown" when enough evidence does not exist
- produce a useful output for a real audience
- remember reusable lessons
- improve future runs from memory and evaluation

The difference between a flashy demo and a durable agentic system is usually not the model. It is the harness around the model.

## Workflow vs agent vs hybrid

People often use "agent" to describe many different things. It helps to separate them.

### Deterministic workflow

The system follows fixed code paths.

Pros:

- easy to test
- easy to debug
- cheap
- predictable

Cons:

- rigid
- weak at novel situations
- hard to scale to more open-ended investigation

### Free agent

The model decides almost everything at runtime.

Pros:

- flexible
- adaptive
- feels intelligent

Cons:

- unstable
- harder to test
- easier to overrun cost
- easier to hallucinate process as well as answers

### Hybrid system

The outer structure is fixed, but the model has meaningful freedom inside bounded parts of the flow.

Pros:

- good balance of flexibility and control
- better auditability
- better learning value
- easier to evolve gradually

Cons:

- more design work
- requires explicit interfaces

This project should stay hybrid.

That means:

- workflow owns ingestion, persistence, policy, budgets, and evaluation
- the model owns planning, hypothesis formation, evidence interpretation, and synthesis

## The design goals for this project

This project is a learning system, not a production retail engine.

That changes what "good" means.

We should optimize for:

- clarity
- inspectability
- useful runtime reasoning
- modularity
- learning value
- evolution over time

We should not optimize first for:

- perfect forecasting accuracy
- perfect causal inference
- full BI functionality
- deep product/store drilldown
- autonomous business execution

The right ambition is a Level 5 learning-mode autonomous analyst:

- it investigates
- it recommends
- it monitors quality
- it learns

It does not directly change the business.

## The core building blocks

A strong agentic system usually needs these components.

### 1. Entry point

This is how the system knows where to spend attention.

In this project, that is `rca signal`.

Its job is not to solve the RCA. Its job is to rank where reasoning effort is worthwhile.

### 2. Planner

The planner decides the first investigation shape.

A good planner:

- knows the available specialists
- knows hard rules and policy constraints
- sees recent memory
- works from a compact, structured context

The planner should not be the entire brain. It should decide where to start.

### 3. Specialists

Specialists are narrow workers with bounded tools and bounded responsibility.

Narrow specialists are useful because they:

- reduce prompt ambiguity
- improve tool discipline
- create more legible intermediate outputs
- make failures easier to localize

### 4. Critic

The critic is not a second coordinator.

Its job is to ask:

- which claims are weak
- what evidence is missing
- what remains unverified
- whether the investigation should continue

The critic exists to reduce false confidence.

### 5. Coordinator or decision writer

This component turns the investigation into something useful for a human audience.

A great agentic system must care about audience.

An analyst-style memo is different from a management decision brief.

### 6. Memory

Memory is reusable state with policy.

Good memory is not just "save everything."

Good memory answers:

- what is worth reusing
- when it applies
- how much to trust it
- how it should change future planning

### 7. Evaluator

The evaluator judges the run after the fact.

This is different from the critic:

- critic improves the current answer
- evaluator improves the system over time

## Control loop design

The control loop is where a workflow starts becoming agentic.

Bad design:

```text
plan once -> run once -> summarize once
```

Better design:

```text
plan -> investigate -> critic -> replan if needed -> investigate again -> stop when sufficient
```

The control loop should be bounded.

For this project:

- max 5 rounds
- stop early if evidence is sufficient
- stop if no useful new action exists
- stop if the only remaining gaps require unavailable data

This gives us adaptive behavior without letting the system wander.

### Why bounded loops matter

Without a budget:

- cost becomes fuzzy
- traces become harder to understand
- agents repeat themselves
- the system looks busy instead of being useful

A loop should create progress, not motion.

### What progress means

Each new round should add at least one of these:

- a new evidence item
- a rejected hypothesis
- a stronger hypothesis
- a better calibrated unknown
- a materially better recommended action

If a round cannot do one of those, it should probably not exist.

## Planning design

Planning is often misunderstood.

A planner should not just say "run everything."

A better planner makes a compact and testable decision.

Planning output should include:

- objective
- selected agents
- rationale
- target gaps or hypotheses
- expected evidence

That forces planning to become explicit.

### Mandatory vs optional specialists

Some agents are nearly always useful.

For this project:

- `statistician` is mandatory
- `sales_agent` is mandatory

Others are conditional:

- `inventory_agent`
- `pricing_agent`
- `promotions_agent`
- `calendar_weather_agent`
- `news_agent`

This is a good pattern: a stable core plus conditional specialists.

### Replanning design

Replanning should be driven by critic gaps, not by vague curiosity.

That means the next round is based on:

- what is still unresolved
- what tool or agent could resolve it
- whether that action is allowed

This keeps the loop purposeful.

## Tooling design

Tools are one of the most important parts of an agentic system.

A tool is not "something convenient." It is an interface between model reasoning and grounded evidence.

Good tools are:

- narrow
- typed
- deterministic
- cheap enough to use repeatedly
- structured in output

Bad tools are:

- giant blobs of raw text
- vague convenience wrappers
- hidden side effects
- unsafe escape hatches

### Types of tools in this project

The current tool set already covers several good patterns:

- fact retrieval
- historical context retrieval
- baseline comparison
- intraday shape comparison
- memory retrieval
- external search

That is a strong learning set because it exposes both evidence collection and lightweight runtime analysis.

### When to add a new tool

Add a tool when one of these is true:

- the model repeatedly needs the same derived fact
- structured computation is more reliable than prose reasoning
- the task needs a policy boundary

Do not add a tool just because it feels "agentic."

### Gated advanced tools

Advanced tools such as statistical or ML helpers should be gated.

The agent should have to explain:

- why this analysis is needed
- what decision it supports

This rule is excellent for learning because it prevents decorative complexity.

## Evidence and claim design

A mature agentic system should separate:

- evidence
- claims
- recommendations
- unknowns

This is where many systems become sloppy. They mix all of them into one markdown paragraph.

### Evidence item

An evidence item should record:

- source
- agent or tool
- short summary
- raw payload
- what it supports
- what it weakens

### Claim

A claim should record:

- exact text
- type: observation, inference, recommendation, unknown
- confidence
- linked evidence
- caveat

### Why this matters

This separation lets us ask better questions:

- which claim has weak support
- which recommendation depends on only one soft signal
- which gap remains unresolved
- which evidence is purely external

This is the backbone of trustworthy agent behavior.

## Memory design

Many teams romanticize memory. In practice, the important thing is not "having memory." It is deciding what is worth carrying forward.

For this project, memory should be small and intentional.

### Good memory categories

- city lessons
- recurring caution patterns
- prior successful investigation patterns
- prior false-positive patterns

### Memory should change behavior

If memory does not change planning or interpretation, it is just storage.

A useful memory system should be able to say:

- this prior lesson caused the planner to check same-weekday distortion first
- this city often shows holiday noise, so confidence should stay capped

That is operational memory.

### Memory risks

Memory can also harm the system:

- it can overfit one prior run
- it can create bias toward a favorite explanation
- it can suppress fresh evidence

That is why memory should include applicability and risk, not just lesson text.

## Critic and evaluator design

One of the most important design decisions is keeping critic and evaluator separate.

### Critic

Runs inside the workflow.

Its job:

- downgrade weak claims
- identify missing evidence
- recommend whether to continue

### Evaluator

Runs after the workflow.

Its job:

- check whether output met quality standards
- create comparable scores across runs
- catch regression

### Why this separation is excellent

If one component tries to do both, it usually becomes muddled:

- either it becomes too soft to enforce quality
- or it becomes too rigid to help the current run improve

Separation keeps both roles cleaner.

## Decision design

A great agentic system does not stop at "here is my RCA."

It should also produce a decision surface for a human audience.

For management-facing output, a decision brief is better than raw analyst prose.

Key sections:

- situation
- business impact
- most likely explanation
- evidence summary
- recommended action
- alternatives
- owner function
- urgency
- expected benefit
- monitoring plan
- unknowns
- caveats

### The calibration rule

The system must be allowed to say:

- unknown
- insufficient evidence
- requires follow-up data

That is not weakness. That is maturity.

### The semantics rule

The project uses normalized sales, not currency.

So a management-quality system must avoid fake realism such as:

- dollar claims
- margin math without data
- store/product diagnosis when only city/date evidence exists

This is one of the most important guardrails in the system.

## Data and schema design

A strong agentic system benefits from separating stable relational data from evolving reasoning artifacts.

### Stable relational columns

Use columns for things we filter and sort often:

- city_id
- dt
- signal_label
- confidence
- run_id
- status
- generated_at

### JSONB reasoning artifacts

Use JSONB for things we are still learning how to design:

- hypotheses
- evidence ledger
- investigation rounds
- critic reviews
- decision brief payload
- monitoring plan
- evaluation result
- memory influence

This is the right early-stage tradeoff:

- flexible enough to evolve
- structured enough to inspect

### Why this is better than over-normalizing too early

If we force every evolving idea into rigid tables too soon:

- migrations become noisy
- experiments slow down
- the design ossifies before we understand it

JSONB lets the system breathe while the design matures.

## Observability and debugging

A system you cannot inspect is a system you cannot improve.

Good observability for an agentic system includes:

- workflow events
- node-level completions
- tool-call traces
- structured outcomes
- memory writes
- evaluator results

The key principle is simple:

final answer alone is not enough.

### What to inspect when something looks wrong

1. Did the signal make sense?
2. Did the planner choose a sensible first path?
3. Did the specialists gather grounded evidence?
4. Did the critic catch weak claims?
5. Did the decision brief stay calibrated?
6. Did memory change behavior for a good reason?
7. Did the evaluator detect the issue?

That sequence is a practical debugging checklist for almost any agentic system.

## Testing strategy

A great agentic system needs more than unit tests, but it still needs unit tests.

### Test layers

1. Deterministic tests

- signal generation
- baseline calculations
- schema validation
- audit checks
- serialization

2. Harness tests with stubbed LLM behavior

- planner output handling
- bounded loop behavior
- stop conditions
- policy gates

3. Optional LLM-judge evaluation

- groundedness
- actionability
- management usefulness

### Golden cases

Golden cases are valuable in agent systems.

A small set of known city/date examples can answer:

- did the signal get detected
- did the loop stop reasonably
- did the final brief remain calibrated
- did the agent violate scope rules

### Why deterministic audits matter

LLM judges are helpful, but they should not be the first line of quality control.

Deterministic audits should catch the obvious failures:

- currency language
- missing sections
- no evidence links
- unsupported scope leap

That keeps the system more trustworthy.

## Common failure modes

Most weak agent systems fail in recognizable ways.

### 1. Tool chaos

Too many tools, weak role boundaries, repeated calls, little progress.

### 2. Summary theater

The output sounds smart, but the evidence structure is weak.

### 3. Hidden workflow

The system looks agentic, but all meaningful logic is hidden in precomputation.

### 4. Memory theater

Memory is stored, but it does not influence behavior.

### 5. Evaluation theater

There is a judge score, but no deterministic quality bar and no regression check.

### 6. Audience mismatch

The answer is fine for an engineer, but useless for management.

### 7. Scope drift

The system starts making product-, store-, margin-, or causal claims the data cannot support.

## What makes a system truly improve over time

A system improves over time when four loops are present:

### 1. Investigation loop

Find better evidence during the current run.

### 2. Memory loop

Reuse prior lessons in future runs.

### 3. Evaluation loop

Score and compare system quality over time.

### 4. Design loop

Humans refine tools, prompts, schema, and policy based on what the traces reveal.

The fourth loop is easy to forget, but it is where most real improvement happens.

Great agentic systems are rarely "born smart." They become better because the system is designed to teach its builders.

## Design heuristics to keep

Keep these heuristics close:

- separate stable layers from experimental layers
- keep the outer workflow simple and explainable
- let the model do meaningful work, but not all the work
- use bounded specialists instead of one vague super-agent
- make evidence first-class
- make unknown an acceptable output
- keep critic and evaluator separate
- store evolving reasoning artifacts in structured JSON
- measure whether memory changes behavior
- prefer a smaller honest system over a bigger theatrical one

If this project keeps those habits, it will stay a strong place to learn real agent engineering.
