# CLAUDE.md — Task 2 AI-Assisted Transformation Pipeline

Always-on rules for Claude Code when working in this directory.

---

## Project Rules

- Do not modify files in `../task1_gold_layer_data_model/`.
- Do not call external APIs without explicit instruction.
- Do not add Docker or containerization unless asked.
- Do not implement the PR agent beyond its stub — it is intentionally incomplete.
- Do not invent raw table or column names not present in `context/raw_schema_catalog.yml`.
- Preserve the `generated_output/` files as the canonical example — do not overwrite them unless explicitly asked.

## Code Rules

- Python only in `scripts/` and `tests/`.
- No third-party dependencies beyond `anthropic`, `pyyaml`, and Python stdlib.
- All file paths in scripts use `Path(__file__).parent` — relative to the script's own location.
- Exit codes: 0 = pipeline passed, 1 = review found blocking errors.
- Exit code 2 = request too ambiguous to model (documented in run_pipeline.py; not yet implemented in the ambiguity routing path — clarification currently warns but does not exit 2).

## Documentation Rules

- Agent prompt files in `agents/` are Markdown. Keep them concise and structured.
- Context files in `context/` are the ground truth. If a context file conflicts with a script, fix the script.
- All assumptions must be stated explicitly — do not silently default.

## Scope

- Task 2 is in `task2_ai_assisted_pipeline/`.
- Task 1 is complete and must not be touched.
- Root `README.md` is managed separately.
