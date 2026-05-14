# JFrog Data Engineering — Home Assignment

This repository contains the JFrog Data Engineering contractor home assignment, structured by task for clarity.

---

## Tasks

| Task | Folder | Status |
|---|---|---|
| Task 1 — Gold Layer Data Model | [`task1_gold_layer_data_model/`](task1_gold_layer_data_model/) | Complete |
| Task 2 — AI-Assisted Transformation Pipeline | [`task2_ai_assisted_pipeline/`](task2_ai_assisted_pipeline/) | Not started |

---

## Task 1 — Gold Layer Data Model

Design an analytics-ready Gold layer data model for the JFrog Artifactory domain, sourced entirely from raw Redshift tables.

**Deliverables:** ERD, model definitions, SQL stub, assumptions, raw-to-Gold mapping, SCD strategy, DBT schema tests, AI workflow documentation.

See [`task1_gold_layer_data_model/README.md`](task1_gold_layer_data_model/README.md) for full details.

---

## Task 2 — AI-Assisted Transformation Pipeline

Design and partially build an automated pipeline that takes an analyst's natural-language request and produces a DBT model pull request.

See [`task2_ai_assisted_pipeline/README.md`](task2_ai_assisted_pipeline/README.md) for details.

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
    └── README.md
```
