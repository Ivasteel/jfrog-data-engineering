# Hooks — Event-Driven Automation Design

This document describes how Claude Code hooks could automate quality checks
in the development workflow for this pipeline.

---

## What Hooks Are

Hooks are shell commands configured in `.claude/settings.json` that execute
automatically in response to Claude Code events — before/after tool calls,
on session end, etc. They enforce automated behaviors without requiring
manual prompts.

---

## Proposed Hooks for This Pipeline

### PostToolUse — Run review after any SQL file is edited

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "if echo '$TOOL_INPUT' | grep -q '\\.sql'; then python scripts/run_pipeline.py --review-only; fi"
          }
        ]
      }
    ]
  }
}
```

**Effect:** Every time Claude edits a `.sql` file in `generated_output/`, the review agent
runs automatically and reports blocking errors before Claude continues.

### PreToolUse — Block reading secrets

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "if echo '$TOOL_INPUT' | grep -qE '\\.env|secrets|credentials'; then echo 'Blocked: secret file access'; exit 1; fi"
          }
        ]
      }
    ]
  }
}
```

**Effect:** Prevents Claude from reading `.env` or credential files accidentally.

### SessionEnd — Write a pipeline run summary

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "type": "command",
        "command": "echo 'Session ended at $(date)' >> pipeline_run_log.txt"
      }
    ]
  }
}
```

---

## Why Hooks Matter for This Pipeline

| Without hooks | With hooks |
|---|---|
| Developer must remember to run review manually | Review runs automatically after every SQL edit |
| Secrets can be accidentally read by Claude | PreToolUse hook blocks access at the harness level |
| No audit trail of pipeline runs | SessionEnd hook logs each run automatically |

Hooks are event-driven; skills are request-driven. The combination creates
a self-enforcing development workflow.

---

## Implementation Status

Not implemented in this submission. Hooks would be configured in
`.claude/settings.json` at the repository root for production use.
