# JFrog Artifactory — Gold Layer Data Model

**Task 1 of 2 · Data Modeling & AI-Assisted Transformation Pipeline**

---

## 🔎 Quick Review Guide

| File | Deliverable |
|---|---|
| [README.md](README.md) | Overview, model summary, design principles |
| [erd.mmd](erd.mmd) | Model diagram — 3 fact + 3 dimension tables, all relationships |
| [models/model_definitions.md](models/model_definitions.md) | Grain, key columns, materialization, and SCD strategy for all 6 models |
| [models/gold_fact_artifact_usage_daily.sql](models/gold_fact_artifact_usage_daily.sql) | Full SQL stub — primary deliverable; all 6 CTEs, actor classification, Redshift patterns |
| [models/schema.yml](models/schema.yml) | DBT-style model descriptions, unique_key, and test definitions |
| [assumptions.md](assumptions.md) | Documented hypothetical schema and all design assumptions |
| [docs/raw_to_gold_mapping.md](docs/raw_to_gold_mapping.md) | Snowplow / Fullstory / Airbyte field-level mapping to Gold columns |
| [ai_workflow/](ai_workflow/) | Controlled AI-assisted workflow — prompts, review log, checklist |

---

## ✅ Validation / Review Notes

- **This is a design deliverable, not a runnable application or DBT project.** There is no pipeline to execute for Task 1.
- **The SQL file** ([models/gold_fact_artifact_usage_daily.sql](models/gold_fact_artifact_usage_daily.sql)) is a Redshift/DBT-style stub. It is written to be read and reviewed, not executed in this repository.
- **schema.yml** documents expected DBT tests (not_null, unique, accepted_values) and model metadata. It reflects what a production DBT project would define, not a running test suite.
- **Key review points:** grain correctness, source-to-Gold traceability, Snowplow/Fullstory event mapping, SCD strategy, and Gold-layer usability for analysts querying Redshift directly.

---

## 📌 Overview

This repository contains the Gold layer data model design for the JFrog Artifactory analytics domain. The model is built entirely from raw Redshift tables (no existing Silver layer) and serves four analytical use cases:

| Use Case | Primary Model |
|---|---|
| Artifact usage — downloads, uploaders, repositories | `gold_fact_artifact_usage_daily` |
| Repository health — storage growth, traffic | `gold_fact_repository_traffic_daily` |
| User & pipeline activity — humans vs. CI bots | `gold_fact_artifact_usage_daily` + `gold_dim_user_identity` |
| Package adoption — gaining/losing traction over time | `gold_fact_package_adoption_daily` |

---

## 🧭 Design Principles

- **Wide and flat over normalized** — analysts query Gold directly in Redshift; unnecessary joins at query time are avoided by denormalizing the most useful dimension attributes into fact tables.
- **Explicit grain on every model** — each model definition starts with a grain statement.
- **Raw → Gold in one hop** — because there is no Silver layer, staging CTEs inside each model perform lightweight normalization: type casting, event deduplication, and Snowplow/Fullstory event mapping.
- **Assumptions are documented explicitly** — see [assumptions.md](assumptions.md).

---

## 📁 Repository Structure

```
Gold Layer Data Model/
├── README.md                                        # This file
├── assumptions.md                                   # All design assumptions
├── erd.mmd                                          # Mermaid ERD diagram
├── models/
│   ├── model_definitions.md                         # Grain + key columns for every model
│   ├── gold_fact_artifact_usage_daily.sql           # Full SQL stub (primary deliverable)
│   └── schema.yml                                   # DBT-style model descriptions and tests
└── docs/
    └── raw_to_gold_mapping.md                       # Raw source → Gold model mapping
```

---

## 🏗️ Gold Layer Models

### 📊 Fact Tables

| Model | Grain | Primary Use Case |
|---|---|---|
| `gold_fact_artifact_usage_daily` | artifact × repository × actor_type × day | Artifact usage, user activity |
| `gold_fact_repository_traffic_daily` | repository × day | Repository health, storage growth |
| `gold_fact_package_adoption_daily` | package × repository × day | Package adoption trends |

### 🧩 Dimension Tables

| Model | Grain | SCD Strategy |
|---|---|---|
| `gold_dim_repository` | one row per repository | SCD1 implemented / SCD2 recommended for ownership history |
| `gold_dim_artifact` | one row per artifact (repo + path + checksum) | SCD1 (artifacts are immutable) |
| `gold_dim_user_identity` | one row per normalized actor | SCD1 implemented / SCD2 recommended for team history |

---

## ⭐ Most Important Model

**`gold_fact_artifact_usage_daily`** — full SQL stub in [models/gold_fact_artifact_usage_daily.sql](models/gold_fact_artifact_usage_daily.sql).

This model covers the primary analytical question: *which artifacts are most downloaded, by whom, and from which repositories?* It also drives user activity and pipeline identification use cases through the denormalized `actor_type` and `pipeline_name` columns.

---

## 🤖 AI Usage

This design was developed using an AI-assisted, human-reviewed workflow:

1. Translated assignment requirements into a candidate set of Gold models and grains.
2. Used Claude (claude-sonnet-4-6) as a design reviewer — checking grain clarity, join risks, missing dimensions, SCD edge cases, and Snowplow/Fullstory mapping completeness.
3. Refined model definitions and SQL stub based on review feedback.
4. Applied final human judgment to select the design and validate assumptions.

Tool used: **Claude Code** (Anthropic) — running as an AI pair programmer, not as an autonomous code generator.

---

## 📝 What I Would Do Next (given more time)

- Build full SQL stubs for `gold_fact_repository_traffic_daily` and `gold_fact_package_adoption_daily`.
- Add SCD2 scaffolding for `gold_dim_repository` and `gold_dim_user_identity`.
- Define DBT incremental materialization strategy (merge on surrogate key, partition by `event_date`).
- Expand `schema.yml` test coverage with referential integrity and row-count reconciliation tests (not-null and accepted-values are already present).
- Model Fullstory session funnel events as a separate `gold_fact_ui_session_activity_daily` table.
- Validate grain assumptions against sample Snowplow event payloads.
