# Retail Insight Agent - PRD

## 1. Project Overview

Retail Insight Agent is a learning project for building an evidence-backed retail root cause analysis system.
It utilizes LangGraph, Supabase, Next.js, and FastMCP to provide an end-to-end framework.

## 2. Delivery Milestones

**Shipped:**
- Read the raw FreshRetailNet-50K parquet file and filter scope.
- Aggregate into daily store-level tables (local DuckDB ETL).
- Push analytical foundations to Supabase (`rca_` schemas).
- Implement a LangGraph multi-agent orchestration (Planner -> Specialists -> Critic -> Coordinator -> Controller -> SLT).
- Record traceable episodic memory and distil semantic store profiles.
- Stand up an LLM-as-judge Evaluator (9 dimensions).
- Stand up a FastMCP server exposing RCA tools.
- Build and deploy the Next.js App Router Dashboard to Vercel.
- Configure Langfuse observability for token cost and trace tracking.
- Create Claude Markdown Skills for workflow automations.

## 3. Data Semantics Guardrail

`sale_amount` is a **daily sales amount after global normalization**.
- It is **not** a literal unit count or real currency revenue.
- Use phrasing like `sales amount` or `normalized sales amount`.

## 4. Scope

**Date Range**: `2024-03-28` to `2024-06-25` (90 days).
**City Scope**: 5 cities (0, 12, 3, 13, 16)
**Store Scope**: 15 sampled stores (h235, h263, m679, etc).
**Analysis Grain**: One analytical row represents one store on one date.

## 5. Architecture

- **Supabase (Postgres)**: System of record. `rca_store_series`, `rca_store_normals`, `rca_outcome`, `rca_store_profile`.
- **DuckDB**: Local ETL compute engine only.
- **LangGraph**: Python-based DAG orchestration defining the analyst pipeline.
- **Next.js Dashboard**: Vercel-hosted readonly viewer securely consuming the Supabase data via RLS. Features a premium glassmorphism UI built with Tailwind CSS v4, Recharts, and a dynamic 14-day signal heatmap.
