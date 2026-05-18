# Task 2 — AI-Assisted Transformation Pipeline

**Status: Complete**

---

## 🔎 Quick Review Guide

| File | What to look for |
|---|---|
| [scripts/run_pipeline.py](scripts/run_pipeline.py) | Working offline pipeline — all 9 stages implemented |
| [context/raw_schema_catalog.yml](context/raw_schema_catalog.yml) | Ground truth schema — injected into the modeling prompt and used by the review agent for validation |
| [agents/modeling_agent.md](agents/modeling_agent.md) | Modeling agent system prompt and user prompt template showing full context injection |
| [agents/review_agent.md](agents/review_agent.md) | Deterministic review/grader specification — 7 checks, failure modes, exit codes |
| [generated_output/gold_package_downloads_daily.sql](generated_output/gold_package_downloads_daily.sql) | Generated SQL — produced by running the pipeline |
| [generated_output/gold_package_downloads_daily.yml](generated_output/gold_package_downloads_daily.yml) | Generated YAML — schema tests and model metadata |
| [generated_output/review_report.md](generated_output/review_report.md) | Review report — written by the pipeline on each run |
| [tests/test_review_agent.py](tests/test_review_agent.py) | 10 unit tests covering valid model, 4 failure modes, naming convention, ambiguity detection |
| [workflow.mmd](workflow.mmd) | Mermaid pipeline diagram |

---

## ✅ Validation Summary

```bash
python3 task2_ai_assisted_pipeline/scripts/run_pipeline.py
# Expected: 7 PASS  0 WARNING  0 FAIL — exits 0

python3 -m pytest task2_ai_assisted_pipeline/tests/test_review_agent.py -v
# Expected: 10 passed
```

No API key required. The pipeline runs fully offline — the modeling prompt is built but no Claude API call is made.

**Optional — Docker** (if a local Python environment is not available):

```bash
# From the repository root:
docker build -t jfrog-data-engineering-home-assignment .
docker run --rm jfrog-data-engineering-home-assignment
```

---

## 🎯 Objective

Build a semi-automated pipeline that takes an analyst's natural-language modeling request and produces a DBT Gold model draft (SQL + YAML) ready for review and merge.

The goal is to give analysts a tool they can use without a data engineer in the loop for every model request.

---

## 🧭 Workflow Diagram

See [workflow.mmd](workflow.mmd) for the Mermaid source.

---

## ⚙️ Pipeline Stages

| Stage | Agent / Component | Status |
|---|---|---|
| 1 — Request intake | `examples/analyst_request.md` | Working |
| 2 — Clarification | `agents/clarification_agent.md` | Working (heuristic check) |
| 3 — Context injection | `context/` files | Working |
| 4 — DBT model generation | `agents/modeling_agent.md` | Working (deterministic offline) |
| 5 — Review & validation | `agents/review_agent.md` | Working (7 checks) |
| 6 — Output writing | `generated_output/` | Working |
| 7 — PR creation | `agents/pr_agent_stub.md` | Stub only |

---

## 📁 Repository Structure

```
task2_ai_assisted_pipeline/
├── README.md                        # This file
├── workflow.mmd                     # Mermaid pipeline diagram
├── CLAUDE.md                        # Claude Code always-on rules for Task 2
├── skills.md                        # Reusable skill definitions
├── agents/
│   ├── clarification_agent.md       # Handles ambiguous analyst requests
│   ├── modeling_agent.md            # Generates DBT SQL + YAML draft
│   ├── review_agent.md              # Validates draft against schema + conventions
│   └── pr_agent_stub.md             # PR creation stub design
├── context/
│   ├── raw_schema_catalog.yml       # Available raw tables and columns
│   ├── dbt_conventions.md           # Naming, materialization, test patterns
│   ├── redshift_constraints.md      # DISTKEY, SORTKEY, SUPER column rules
│   └── gold_modeling_rules.md       # Grain, denormalization, CTE patterns
├── examples/
│   ├── analyst_request.md           # Clear analyst request (happy path)
│   └── ambiguous_request.md         # Ambiguous request (clarification path)
├── scripts/
│   └── run_pipeline.py              # Working pipeline script
├── generated_output/
│   ├── gold_package_downloads_daily.sql
│   ├── gold_package_downloads_daily.yml
│   └── review_report.md
├── tests/
│   └── test_review_agent.py         # Unit tests for review validation logic
└── docs/
    ├── subagents.md                 # Subagent design and delegation patterns
    ├── hooks.md                     # Event-driven automation hooks design
    ├── mcp_integrations.md          # MCP server integration design
    └── limitations_and_next_steps.md
```

---

## 🧠 Key Design Decisions

- **Context injection is the hardest part** — the modeling agent is only as good as the schema catalog and conventions it receives. See `context/` files.
- **Review agent is deterministic** — the review/grader runs rule-based checks, not another LLM call. This prevents cascading hallucinations.
- **Human stays in the loop** — the pipeline exits with a review report before any PR is opened. A human approves the generated output before merge.
- **PR agent is stubbed** — GitHub integration is out of scope; the stub documents what a real implementation would do.
- **Failure modes are explicit** — ambiguous requests route to the clarification agent; hallucinated column names cause a blocking review failure.

---

## 🚀 Running the Pipeline

**No external API key or dependencies required.** The pipeline runs fully offline.

```bash
# From the repository root:
python3 task2_ai_assisted_pipeline/scripts/run_pipeline.py

# With a custom request file:
python3 task2_ai_assisted_pipeline/scripts/run_pipeline.py --request path/to/request.md
```

**What happens when you run it:**

1. Loads `examples/analyst_request.md` and checks it for ambiguity.
2. Loads all 4 context files from `context/` (schema catalog, conventions, constraints, rules).
3. Builds the modeling prompt (15 k chars) — the prompt that would be sent to Claude API.
4. Generates the deterministic pre-authored model output (no API call needed).
5. Runs 7 deterministic review checks against the SQL and YAML.
6. Writes `generated_output/gold_package_downloads_daily.sql`, `.yml`, and `review_report.md`.
7. Prints a PR stub summary and exits 0 (pass) or 1 (blocking review failures).

**Run the unit tests:**

```bash
python3 -m pytest task2_ai_assisted_pipeline/tests/test_review_agent.py -v
```

10 tests, no skips. Tests cover: valid model passes review, negative SPLIT_PART fails, unknown raw table fails, grain declaration, JSON field validation, model naming, and ambiguity detection.

**Exit codes:**

| Code | Meaning |
|---|---|
| 0 | Pipeline passed (all checks PASS or WARNING) |
| 1 | Pipeline failed (one or more FAIL checks) |
| 2 | Request too ambiguous (documented; not yet triggered in offline mode) |

---

## 📝 Limitations & Next Steps

See [docs/limitations_and_next_steps.md](docs/limitations_and_next_steps.md).

---

## 🤖 AI Usage

This pipeline was designed with Claude Code (claude-sonnet-4-6) as an AI pair programmer.
See [../task1_gold_layer_data_model/ai_workflow/](../task1_gold_layer_data_model/ai_workflow/) for the documented AI workflow methodology applied across both tasks.
