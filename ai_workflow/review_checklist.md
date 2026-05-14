# Task 1 Review Checklist

This checklist was used to evaluate the Task 1 submission during the Lead Data Engineer review stage (Prompt 2) and the final critical review (Prompt 4). Each criterion maps to one or more specific files.

**Section 1** shows the completion status of each required deliverable — verified against the actual files submitted.
**Sections 2–11** are the verification criteria applied during the review stages to assess correctness, consistency, and quality.

---

## 1. Deliverable Completeness

| Required Deliverable | File | Status |
|---|---|---|
| ERD / model diagram | `erd.mmd` | ✅ |
| Model definitions with grain, description, key columns | `models/model_definitions.md` | ✅ |
| One SQL model stub | `models/gold_fact_artifact_usage_daily.sql` | ✅ |
| Assumptions documented | `assumptions.md` | ✅ |
| Raw source to Gold mapping | `docs/raw_to_gold_mapping.md` | ✅ |
| Snowplow / Fullstory mapping to fact models | `docs/raw_to_gold_mapping.md` | ✅ |
| SCD strategy documented where relevant | `assumptions.md`, `models/model_definitions.md` | ✅ |

---

## 2. Model Grain Clarity

- [ ] Every model has an explicit grain statement at the top of its definition.
- [ ] Grain components match the GROUP BY clause in the SQL stub.
- [ ] Grain components match the `unique_key` in schema.yml.
- [ ] Grain components match the PK columns in the ERD.
- [ ] Any design trade-offs in grain selection are documented (e.g., actor_type as a grain component).

---

## 3. ERD / Model / SQL Consistency

- [ ] All models in README are present in the ERD.
- [ ] All models in the ERD are defined in model_definitions.md.
- [ ] ERD relationship labels accurately reflect join keys used in the SQL.
- [ ] ERD does not imply relationships that do not exist in the SQL (e.g., a dimension joined at runtime that is actually denormalized).
- [ ] SCD columns in the ERD match the implementation state (not future-recommended state).

---

## 4. Redshift SQL Compatibility

- [ ] No invalid Redshift syntax (e.g., negative SPLIT_PART index, unsupported window functions).
- [ ] JSON extraction from SUPER columns uses `JSON_EXTRACT_PATH_TEXT`, not dot-notation.
- [ ] QUALIFY clause is used correctly for deduplication.
- [ ] DISTKEY and SORTKEY choices are justified.
- [ ] Incremental filter is noted as requiring `{% if is_incremental() %}` in production DBT.
- [ ] COALESCE used for all left-join nullable columns.

---

## 5. Raw-to-Gold Traceability

- [ ] Every Gold model column is traceable to a raw source table or a documented assumption.
- [ ] Mapping matrix in raw_to_gold_mapping.md covers all models and all raw source tables.
- [ ] No column exists in the SQL that is not explained in assumptions.md or the mapping doc.
- [ ] Airbyte internal columns not used as keys are explicitly marked and explained.

---

## 6. Snowplow / Fullstory / Airbyte Mapping

- [ ] Snowplow download events are mapped to specific Gold fact columns (download_count, total_bytes_downloaded, last_downloaded_at, unique actors).
- [ ] Snowplow upload events are mapped to upload-specific Gold columns.
- [ ] Snowplow `unstruct_event` SUPER field extraction is documented (field name → Gold column).
- [ ] Fullstory is correctly scoped to UI-only signals — not used for artifact counts.
- [ ] Fullstory's role in actor classification (human detection) is explicitly documented.
- [ ] Airbyte repository and artifact tables are mapped to their Gold consumers.
- [ ] Airbyte sync frequency and its effect on end-of-day snapshot columns is documented.

---

## 7. No-Silver-Layer Handling

- [ ] The submission does not reference a Silver layer as if it exists.
- [ ] The CTE staging pattern is explicitly framed as performing Silver-like operations inline.
- [ ] The Silver Layer Note explains what would change if Silver were introduced.
- [ ] All raw source tables are the direct inputs to Gold models (or to staging CTEs within them).

---

## 8. SCD Strategy Consistency

- [ ] SCD strategy for each dimension is documented in model_definitions.md.
- [ ] SCD wording is consistent across README, ERD, model_definitions.md, and assumptions.md.
- [ ] The ERD does not show SCD columns that are not implemented in this submission.
- [ ] The gap between "SCD2 recommended" and "SCD1 implemented" is clearly stated everywhere it appears.

---

## 9. Assumptions Quality

- [ ] All hypothetical schema decisions are documented as numbered assumptions.
- [ ] Every assumption explains the reasoning, not just the decision.
- [ ] Join keys are explicitly documented (e.g., why artifact_id is not used).
- [ ] Event name values used in WHERE clauses are justified by assumptions.
- [ ] Actor classification logic is documented and consistent with the SQL implementation.
- [ ] Edge cases (NULL checksum, Airbyte miss on size, virtual repo resolution) are noted.

---

## 10. DBT-Style Test Coverage

- [ ] Primary grain keys have `not_null` tests in schema.yml.
- [ ] Enumeration columns (actor_type, repository_mode, package_type) have `accepted_values` tests.
- [ ] Dimension natural keys have `unique` tests.
- [ ] `unique_key` in schema.yml config matches the grain definition in model_definitions.md.
- [ ] Column descriptions in schema.yml match the definitions in model_definitions.md.

---

## 11. Gold-Layer Analyst Usability

- [ ] Fact tables are wide — key dimension attributes are denormalized, not hidden in separate joins.
- [ ] Analyst example queries are provided and reference only the Gold table (no raw source joins needed).
- [ ] Column names are self-explanatory without requiring documentation lookup.
- [ ] The primary use cases from the assignment are directly answerable from the Gold models as designed.

---

## Scoring Guide (used during review)

| Score | Meaning |
|---|---|
| 9–10 | Submission-ready. Minor optional improvements only. |
| 7–8 | Ready with small fixes. No redesign needed. |
| 5–6 | Needs targeted fixes. Core design is sound. |
| < 5 | Structural issues. Core design or coverage is incomplete. |
