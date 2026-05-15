# Review Agent

**Role:** Deterministic quality gate. Validates the modeling agent's SQL + YAML output against the schema catalog and conventions before any PR is opened.

**Design principle:** The review agent is NOT an LLM prompt. It is a rule-based checker implemented in `scripts/run_pipeline.py`. This document is the human-readable spec — the Python code is the implementation.

**Why deterministic?** Chaining two LLMs for generation + review risks cascading hallucinations where the review LLM validates plausible-sounding but incorrect output. A rule-based checker catches the failure modes that matter most.

---

## Validation Checklist — 7 Checks

### Check 1 — Grain Declaration (FAIL if violated)
- The first non-whitespace line of the SQL must match: `-- Grain: one row per (...)`
- **FAIL** if the grain comment is absent or malformed.

### Check 2 — No Negative SPLIT_PART Index (FAIL if violated)
- Scan for `SPLIT_PART(..., -N)` patterns.
- Redshift does not support negative indexes in SPLIT_PART.
- **FAIL** if any negative SPLIT_PART index is found.

### Check 3 — Raw Table References in Catalog (FAIL if violated)
- Extract all `raw.*` table references from the SQL.
- Cross-reference each against `context/raw_schema_catalog.yml`.
- **FAIL** if any `raw.*` table is not in the catalog.

### Check 4 — JSON Field References in Catalog (FAIL if violated)
- Extract all field-name string literals from `JSON_EXTRACT_PATH_TEXT(col, 'field')` calls.
- Cross-reference each against the known fields in `context/raw_schema_catalog.yml`.
- **FAIL** if any field name is not present in the catalog.
- *Scope note:* This check validates JSON field literals only. General column alias validation
  (SELECT/WHERE/JOIN ON) is a future enhancement requiring SQL AST parsing.

### Check 5 — YAML not_null Tests on Grain Keys (WARNING if missing)
- All columns listed in the grain must have a `not_null` test in the schema YAML.
- **WARNING** (non-blocking) if any grain key is missing `not_null`.

### Check 6 — Model Name Convention (FAIL if violated)
- Model name (from YAML `name:` field) must start with `gold_`.
- **FAIL** if the model name does not follow this convention.

### Check 7 — Request Clarity (WARNING if ambiguous)
- Re-run the clarification agent's heuristic checks against the original analyst request.
- Signals checked: time dimension, grain indicator, primary event.
- **WARNING** if the request would have been flagged as ambiguous at intake.

---

## Future Enhancements (not implemented)

- **JOIN safety check:** Verify that all nullable LEFT JOIN columns used in SELECT are wrapped in COALESCE.
- **Assumption documentation check:** Verify that SQL NULL assignments have an accompanying comment.
- **Dot-notation SUPER access check:** Detect `column.field` access on SUPER columns (should use JSON_EXTRACT_PATH_TEXT).
- **Full column reference validation:** Cross-reference all SELECT/WHERE/JOIN column references against the catalog (requires SQL AST parsing).

---

## Output Format — review_report.md

```markdown
# Review Report

**Model:** gold_package_downloads_daily
**Generated:** {timestamp}
**Overall verdict:** PASS

## Check Results

| # | Check | Result | Details |
|---|---|---|---|
| 1 | Grain declaration | PASS | Grain found: one row per (event_date, repository_key, package_type, package_name, actor_type) |
| 2 | Redshift: no negative SPLIT_PART index | PASS | No negative SPLIT_PART indexes found. |
| 3 | Raw table references in catalog | PASS | All 4 raw table(s) found in catalog |
| 4 | Column references in catalog (JSON fields) | PASS | All 6 JSON field reference(s) found in catalog. |
| 5 | YAML not_null tests on grain keys | PASS | not_null tests present for all 5 grain key(s). |
| 6 | Model name convention (gold_ prefix) | PASS | Model name 'gold_package_downloads_daily' follows gold_ prefix convention. |
| 7 | Request clarity | PASS | Request is clear — no clarification needed. |
```

See `generated_output/review_report.md` for the live output from the last pipeline run.

---

## Exit Codes

| Condition | Exit code |
|---|---|
| All checks PASS or WARNING only | 0 |
| Any check FAIL | 1 |
