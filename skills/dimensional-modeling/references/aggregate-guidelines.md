# Aggregate Fact Table Guidelines

Load this reference when designing aggregate fact tables to support user-requested KPIs.

## Design Principles

1. **Declared grain**: Aggregate fact tables must have a grain that is **strictly coarser** than the base fact table. Reference the applicable chapter/concepts from "Star Schema: The Complete Reference".

2. **Shrunken dimensions**: Aggregate fact tables reference shrunken versions of the original dimensions (fewer rows, same surrogate key domain). Identify which dimensions must be shrunken and propose their DDL.

## When to Propose Aggregates

Propose an aggregate fact table when:
- A user-requested indicator is defined at a **grain coarser than the base fact** (e.g., monthly revenue when base fact is at transaction grain)
- The indicator involves **running totals, period-over-period deltas**, or cumulative measures expensive to compute at query time
- Data volume statistics suggest that **query-time aggregation over the base fact would be prohibitively slow**

## When NOT to Propose Aggregates

Do **not** propose an aggregate table when:
- The base fact table is **small enough** that query-time aggregation is efficient
- The indicator can be served by a **simple GROUP BY** on the base fact
- Adding the aggregate would create **redundancy without meaningful performance gain**

## Naming Convention

Name aggregate fact tables as: `fact_<business_process>_<aggregate_grain>`

Examples:
- `fact_pagamentos_mensal`
- `fact_contemplacoes_trimestral`
- `fact_vendas_semanal`

## Population Rule

The SELECT that populates an aggregate fact table must **source from the base fact table** (not from the silver layer directly), ensuring consistency between base and aggregate facts.
