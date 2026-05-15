# MCP Integrations — Design Notes

This document describes how MCP (Model Context Protocol) servers would extend
this pipeline with access to external systems in a production deployment.

---

## What MCP Provides

MCP gives Claude Code structured access to external tools and APIs —
GitHub, Jira, Slack, databases, internal services — without hardcoding
API calls into the pipeline script.

Skills tell Claude HOW to do a task.
MCP gives Claude ACCESS to external systems to do it.

---

## Planned MCP Integrations

### GitHub MCP

**Purpose:** Replace the PR agent stub with a real implementation.

**Operations:**
- `create_branch(name)` — create `analytics/auto/{model_name}`
- `commit_files(branch, files)` — commit SQL + YAML + review report
- `create_pull_request(title, body, branch, assignees)` — open PR
- `add_label(pr, label)` — tag PR as "auto-generated"

**Required:** `GITHUB_TOKEN` with repo write scope.

### Jira MCP (optional)

**Purpose:** Link model generation to analyst ticket workflows.

**Operations:**
- `get_ticket(id)` — read analyst request from a Jira ticket description
- `add_comment(id, text)` — post pipeline status back to the ticket
- `transition_ticket(id, status)` — move ticket to "In Review" after PR is opened

### Slack MCP (optional)

**Purpose:** Notify the requesting analyst when the model draft is ready.

**Operations:**
- `post_message(channel, text)` — post PR link + review summary to team channel

### Redshift / Database MCP (advanced)

**Purpose:** Query actual raw schema from Redshift to auto-populate `raw_schema_catalog.yml`.

**Operations:**
- `describe_table(schema, table)` — fetch column names and types
- `list_tables(schema)` — enumerate available raw tables

This would replace the manually maintained `context/raw_schema_catalog.yml` with
a live schema query — eliminating the risk of catalog drift.

---

## Integration Architecture

```
run_pipeline.py
  ├── Context Loader → reads context/ files (static)
  │                 → OR queries Redshift MCP (live, advanced)
  ├── Modeling Agent → calls Claude API
  ├── Review Agent   → deterministic (no MCP needed)
  └── PR Agent       → calls GitHub MCP (replaces stub)
                     → calls Jira MCP (optional)
                     → calls Slack MCP (optional)
```

---

## Implementation Status

Not implemented in this submission. The PR agent stub documents
the GitHub MCP operations it would invoke. Live schema querying
via Redshift MCP is documented as a future enhancement.
