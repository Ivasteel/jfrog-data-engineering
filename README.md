# JFrog Data Engineering — Home Assignment

This repository contains the JFrog Data Engineering contractor home assignment, structured by task for clarity.

---

## Tasks

| Task | Folder | Status |
|---|---|---|
| Task 1 — Gold Layer Data Model | [`task1_gold_layer_data_model/`](task1_gold_layer_data_model/) | Complete |
| Task 2 — AI-Assisted Transformation Pipeline | [`task2_ai_assisted_pipeline/`](task2_ai_assisted_pipeline/) | Complete |

---

## Quick Review Guide

**Task 1 — start here:**

| File | What it contains |
|---|---|
| [`task1_gold_layer_data_model/README.md`](task1_gold_layer_data_model/README.md) | Overview, model summary, design principles |
| [`task1_gold_layer_data_model/erd.mmd`](task1_gold_layer_data_model/erd.mmd) | Mermaid ERD — 3 fact tables + 3 dimension tables |
| [`task1_gold_layer_data_model/models/model_definitions.md`](task1_gold_layer_data_model/models/model_definitions.md) | Grain, key columns, SCD strategy for all 6 models |
| [`task1_gold_layer_data_model/models/gold_fact_artifact_usage_daily.sql`](task1_gold_layer_data_model/models/gold_fact_artifact_usage_daily.sql) | Full SQL stub — primary deliverable |
| [`task1_gold_layer_data_model/docs/raw_to_gold_mapping.md`](task1_gold_layer_data_model/docs/raw_to_gold_mapping.md) | Source-to-Gold mapping, Snowplow/Fullstory field mapping |

**Task 2 — start here:**

| File | What it contains |
|---|---|
| [`task2_ai_assisted_pipeline/README.md`](task2_ai_assisted_pipeline/README.md) | Overview, pipeline stages, run instructions |
| [`task2_ai_assisted_pipeline/workflow.mmd`](task2_ai_assisted_pipeline/workflow.mmd) | Mermaid pipeline diagram |
| [`task2_ai_assisted_pipeline/scripts/run_pipeline.py`](task2_ai_assisted_pipeline/scripts/run_pipeline.py) | Working pipeline script — all 9 stages |
| [`task2_ai_assisted_pipeline/generated_output/`](task2_ai_assisted_pipeline/generated_output/) | Sample SQL, YAML, and review report produced by the pipeline |
| [`task2_ai_assisted_pipeline/tests/test_review_agent.py`](task2_ai_assisted_pipeline/tests/test_review_agent.py) | 10 unit tests for the review agent validation logic |

---

## Quick Start — Task 2

No API key or external dependencies required. The pipeline runs fully offline.

```bash
# Run the pipeline end-to-end
python3 task2_ai_assisted_pipeline/scripts/run_pipeline.py

# Run the review agent unit tests
python3 -m pytest task2_ai_assisted_pipeline/tests/test_review_agent.py -v
```

Expected output: `7 PASS  0 WARNING  0 FAIL` and `10 passed`.

**Optional — Docker** (if a local Python environment is not available):

```bash
docker build -t jfrog-data-engineering-home-assignment .
docker run --rm jfrog-data-engineering-home-assignment
```

---

## Task 1 — Gold Layer Data Model

Design an analytics-ready Gold layer data model for the JFrog Artifactory domain, sourced entirely from raw Redshift tables.

**Deliverables:** ERD, model definitions, SQL stub, assumptions, raw-to-Gold mapping, SCD strategy, DBT schema tests, AI workflow documentation.

See [`task1_gold_layer_data_model/README.md`](task1_gold_layer_data_model/README.md) for full details.

---

## Task 2 — AI-Assisted Transformation Pipeline

A semi-automated pipeline that takes an analyst's natural-language request and produces a DBT Gold model draft (SQL + YAML) ready for human review.

See [`task2_ai_assisted_pipeline/README.md`](task2_ai_assisted_pipeline/README.md) for full details.

---

## Notes

- **No API key required.** Task 2 runs in deterministic offline mode; the pipeline builds the full modeling prompt but does not call the Claude API.
- **Intentional stubs:** GitHub PR creation, live Claude API call, MCP integrations (GitHub, Slack, Redshift), and hooks are documented as future/stubbed integrations. The review agent and all offline pipeline stages are fully implemented.
- **Repository is private** because the assignment is marked confidential.

---

## Repository Structure

```
jfrog-data-engineering-home-assignment/
├── README.md                              # This file
├── task1_gold_layer_data_model/
│   ├── README.md
│   ├── assumptions.md
│   ├── erd.mmd
│   ├── models/
│   │   ├── gold_fact_artifact_usage_daily.sql
│   │   ├── model_definitions.md
│   │   └── schema.yml
│   ├── docs/
│   │   └── raw_to_gold_mapping.md
│   └── ai_workflow/
│       ├── README.md
│       ├── prompts.md
│       ├── review_checklist.md
│       └── review_log.md
└── task2_ai_assisted_pipeline/
    ├── README.md
    ├── workflow.mmd
    ├── CLAUDE.md
    ├── skills.md
    ├── agents/
    │   ├── clarification_agent.md
    │   ├── modeling_agent.md
    │   ├── review_agent.md
    │   └── pr_agent_stub.md
    ├── context/
    │   ├── raw_schema_catalog.yml
    │   ├── dbt_conventions.md
    │   ├── redshift_constraints.md
    │   └── gold_modeling_rules.md
    ├── examples/
    │   ├── analyst_request.md
    │   └── ambiguous_request.md
    ├── scripts/
    │   └── run_pipeline.py
    ├── generated_output/
    │   ├── gold_package_downloads_daily.sql
    │   ├── gold_package_downloads_daily.yml
    │   └── review_report.md
    ├── tests/
    │   └── test_review_agent.py
    └── docs/
        ├── subagents.md
        ├── hooks.md
        ├── mcp_integrations.md
        └── limitations_and_next_steps.md
```
