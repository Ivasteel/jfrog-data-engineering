# Subagents — Design Notes

This document describes how subagents could be used in a production version of this pipeline
to parallelize work and isolate concerns.

---

## Current Pipeline — Sequential (implemented in this submission)

```
analyst_request → clarification_agent → modeling_agent → review_agent → output_writer → pr_agent_stub
```

All stages run sequentially in `scripts/run_pipeline.py`. The main Claude instance
handles all stages. This is correct for a single-request pipeline at this scale.

---

## Subagent Pattern — When It Would Apply

Subagents become valuable when:
- Multiple analyst requests are queued simultaneously (parallel modeling)
- A large model needs multiple independent review perspectives (parallel review)
- Context loading is slow and can be pre-fetched by a dedicated agent

### Example: Parallel Review with Subagents

```
Main agent: dispatch review tasks
  ├── Subagent 1: schema integrity check  (checks 1–2)
  ├── Subagent 2: convention + syntax check (checks 3–4)
  └── Subagent 3: test coverage + safety check (checks 5–7)
Main agent: combine results → review_report.md
```

In Claude Code's Agent SDK, this would be expressed as parallel Agent tool calls
in a single message, each with an isolated context window.

### Example: Parallel Modeling for Multiple Requests

```
Main agent: read request queue
  ├── Subagent A: model gold_package_downloads_daily
  ├── Subagent B: model gold_repository_traffic_daily
  └── Subagent C: model gold_user_activity_daily
Main agent: collect outputs → run review on each
```

---

## Why Not Used in This Submission

- A single analyst request does not benefit from parallelism.
- The review agent is deterministic (not an LLM) — no isolation benefit from a subagent.
- Sequential flow is easier to debug and trace for an assignment submission.

---

## Claude Code SDK Reference

Subagents in Claude Code are invoked via the Agent tool:

```python
# Conceptual — not implemented in run_pipeline.py
Agent(
    description="Schema integrity review",
    prompt=f"Review this SQL for unknown columns: {sql}",
    subagent_type="claude"
)
```

For production, subagents would be launched in a single message (parallel execution)
and their results combined by the main agent.
