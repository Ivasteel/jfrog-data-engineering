# AI-Assisted Workflow — Task 1

This folder documents how Claude Code (claude-sonnet-4-6, Anthropic) was used as a design assistant and reviewer for Task 1 of the JFrog Data Engineering home assignment.

---

## Workflow Summary

The process followed four controlled stages. Claude was used as an assistant and reviewer at each stage — not as an autonomous decision-maker. All final design choices, assumption wording, and deliverable selection were made by the human author.

```
Stage 1 — Initial Generation
  Human provides: assignment context, entity definitions, data stack, use cases
  Claude produces: folder structure, model definitions, ERD, SQL stub, assumptions, mapping doc

Stage 2 — Strict Lead Data Engineer Review
  Human instructs: review each file independently, then run cross-file integration check
  Claude acts as: strict reviewer identifying critical bugs, inconsistencies, and gaps
  Claude does NOT: modify any files, move to Task 2, or make design decisions

Stage 3 — Controlled Fix Pass
  Human instructs: apply only the issues identified in the review — nothing more
  Claude applies: minimal, targeted fixes to the identified critical and documentation issues
  Claude does NOT: redesign models, add new models, or introduce unrequested changes

Stage 4 — Final Critical Review
  Human instructs: review the fixed files one more time, strict mode, no cosmetic suggestions
  Claude confirms: no critical issues remain, two optional improvements noted
  Human decides: apply both optional improvements, then close Task 1

Human final judgment: The human reviewed every file before and after each stage,
accepted or rejected individual fixes, and made the final call on submission readiness.
```

---

## Why This Approach

This workflow was designed to demonstrate what a production AI-assisted data engineering process looks like — as opposed to "paste the assignment into ChatGPT and submit the output."

Key principles applied:

- **Decomposed prompts** — each stage had a single, constrained purpose. No single prompt tried to generate, review, and fix in one shot.
- **Role discipline** — Claude was explicitly instructed to act as a reviewer and not modify files during review stages. This separates analysis from action.
- **Controlled scope** — fix prompts included explicit rules: "fix only reviewed issues," "do not redesign," "do not add new models."
- **Final human review** — a strict final review prompt was run after fixes to catch any regressions or remaining gaps before submission.

---

## Tools Used

| Tool | Purpose |
|---|---|
| Claude Code (claude-sonnet-4-6) | AI assistant, reviewer, code generator |
| Mermaid | ERD diagram format |
| DBT schema YAML conventions | Model test definitions |
| Redshift SQL | SQL stub target dialect |

---

## Files in This Folder

| File | Contents |
|---|---|
| `README.md` | This file — workflow overview |
| `prompts.md` | Summary of the four main prompt stages |
| `review_checklist.md` | Grader-style checklist used to evaluate the submission |
| `review_log.md` | Issues found and fixes applied during the review stages |
