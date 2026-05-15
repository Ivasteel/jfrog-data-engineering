# Limitations and Next Steps

---

## What Is Implemented in This Submission

| Component | Status |
|---|---|
| Folder structure and README | Complete |
| Mermaid workflow diagram | Complete |
| CLAUDE.md always-on rules | Complete |
| skills.md reusable skill definitions | Complete |
| Context files (schema catalog, conventions, constraints, rules) | Complete |
| Agent prompt specifications (clarification, modeling, review, PR stub) | Complete |
| Analyst request examples (clear + ambiguous) | Complete |
| Pipeline script — all 9 stages working offline | Complete |
| Generated output SQL + YAML | Complete — 133-line SQL, 67-line YAML |
| Review report | Complete — 7 deterministic checks, all PASS |
| Review agent unit tests | Complete — 10 tests, 0 skipped |

The command `python3 task2_ai_assisted_pipeline/scripts/run_pipeline.py` runs end-to-end
in offline mode with no external API key required. All 7 review checks pass.

---

## What Is Not Implemented

### 1. Real Claude API call

The pipeline builds the full modeling prompt (15k chars) and prints a note that the API call
is skipped in offline mode. A real API call would replace the pre-authored deterministic output
with a live LLM response.

**What would be needed:** ~15 lines using the `anthropic` Python SDK. The prompt is already
constructed in `build_modeling_prompt()` — only the call and response-parsing step are missing.

### 2. Real GitHub PR creation

The PR agent prints a stub summary of what it would do (create branch, commit files, open PR).
No git commands are executed.

**What would be needed:** GitHub API calls or a GitHub MCP integration.
See `agents/pr_agent_stub.md` and `docs/mcp_integrations.md` for the full design.

### 3. Live Redshift schema querying

`context/raw_schema_catalog.yml` is manually maintained. Schema drift (new columns,
renamed tables) would cause the review agent to reject valid models over time.

**What would be needed:** A Redshift MCP integration to auto-populate the schema catalog
from live `INFORMATION_SCHEMA` queries. See `docs/mcp_integrations.md`.

### 4. Hooks and MCP integrations

Event-driven automation (run review on every SQL edit, notify analyst via Slack on PR open)
is documented as design notes in `docs/hooks.md` and `docs/mcp_integrations.md` but not
configured or implemented in this submission.

---

## Known Design Limitations

### Context catalog maintenance

`context/raw_schema_catalog.yml` is the ground truth for both the modeling agent (context injection)
and the review agent (column validation). If the real Redshift schema changes and this file
is not updated, valid models will be rejected and invalid models may pass undetected.

### Single-pass clarification

The clarification agent runs once before the modeling agent. If the analyst's clarification
is itself ambiguous, the pipeline proceeds with a warning and documents the remaining
assumption in the SQL. A multi-turn clarification loop would require stateful session design.

### Hallucination risk in modeling agent

Even with strict context injection, an LLM can hallucinate column names that sound plausible.
Check 3 (raw table references) and Check 4 (JSON field references) catch the most common
hallucination patterns. Plausible-sounding wrong column names (e.g. `artifact_size` instead
of `size_bytes`) require exact string matching against the catalog — which is implemented
for JSON field literals. Full SELECT/WHERE/JOIN column validation requires SQL AST parsing
and is listed as a future enhancement in `agents/review_agent.md`.

### PR agent is fully stubbed

No actual GitHub operations are performed. The stub prints what a real agent would do.

---

## Recommended Next Steps (in priority order)

1. **Implement the Claude API call** — wire `build_modeling_prompt()` output into the
   `anthropic` SDK. Compare live LLM output to the pre-authored example to validate
   that context injection produces correct SQL.

2. **Implement full column reference validation** — extend Check 4 from JSON field literals
   to all column references in SELECT, WHERE, and JOIN ON clauses using regex or a SQL parser.

3. **Add GitHub MCP integration** — replace the PR agent stub with real branch creation
   and PR opening via the GitHub MCP server.

4. **Add live schema querying** — replace the static `raw_schema_catalog.yml` with a
   Redshift MCP integration that queries `INFORMATION_SCHEMA` on each pipeline run.

5. **Configure hooks** — add `.claude/settings.json` with PostToolUse hooks to auto-run
   the review agent whenever a SQL file in `generated_output/` is edited.
