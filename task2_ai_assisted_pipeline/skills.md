# Skills — Task 2 AI-Assisted Transformation Pipeline

Reusable skill definitions for Claude Code when working on this pipeline.

---

## Skill: dbt-gold-model-generation

**Trigger:** User asks to generate a DBT Gold model from a natural-language request.

**Methodology:**
1. Load the analyst request from `examples/analyst_request.md` or inline.
2. Load all context files from `context/`.
3. Apply the modeling agent prompt from `agents/modeling_agent.md`.
4. Produce a SQL file and a YAML file matching DBT conventions in `context/dbt_conventions.md`.
5. Write output to `generated_output/`.

**Constraints:**
- Only use tables and columns from `context/raw_schema_catalog.yml`.
- State grain explicitly in the first SQL comment.
- Apply Redshift rules from `context/redshift_constraints.md`.

---

## Skill: dbt-model-review

**Trigger:** User asks to review a generated DBT model or validate a SQL/YAML pair.

**Methodology:**
1. Load the SQL and YAML files to review.
2. Load `context/raw_schema_catalog.yml` as the column existence ground truth.
3. Load `context/dbt_conventions.md` as the naming and test convention ground truth.
4. Run the 7-check validation defined in `agents/review_agent.md`.
5. Produce `generated_output/review_report.md`.

**Exit behavior:** Report PASS/FAIL/WARNING per check. Blocking failures must be fixed before PR.

---

## Skill: pipeline-run

**Trigger:** User asks to run the pipeline end-to-end.

**Methodology:**
1. Run `scripts/run_pipeline.py`.
2. Inspect `generated_output/` for SQL, YAML, and review report.
3. Report pipeline exit code and summary.

---

## Skill: clarification-handling

**Trigger:** Analyst request is ambiguous — missing grain, missing time dimension, or referencing unknown tables.

**Methodology:**
1. Apply the clarification agent prompt from `agents/clarification_agent.md`.
2. Generate a set of targeted clarifying questions.
3. Do not proceed to modeling until grain and primary source table are confirmed.
