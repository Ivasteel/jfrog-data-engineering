# Prompt Stages — Task 1

Each stage used a distinct, constrained prompt. Prompts were written to limit scope and prevent Claude from taking unrequested actions (e.g., modifying files during a review stage, or starting Task 2 without instruction).

---

## Prompt 1 — Initial Task 1 Generation

**Purpose:** Translate the assignment requirements into a complete set of Task 1 deliverables.

**Key instructions given to Claude:**
- Create the folder structure with `models/` and `docs/` subdirectories.
- Generate all required files: README, assumptions, ERD (Mermaid), model definitions, SQL stub, schema.yml, raw-to-gold mapping.
- Use only the entities and data stack defined in the assignment (Snowplow, Fullstory, Airbyte, Redshift).
- Design the Gold layer to be wide, denormalized, and analyst-friendly.
- Document every assumption explicitly.
- The SQL stub should target `gold_fact_artifact_usage_daily` as the primary deliverable.

**Output:** 7 files across the project folder — all Task 1 deliverables in draft form.

---

## Prompt 2 — Strict Lead Data Engineer Review

**Purpose:** Identify critical bugs, logical inconsistencies, missing requirements, and documentation gaps. No file modifications allowed at this stage.

**Key instructions given to Claude:**
- Act as a strict Lead Data Engineer reviewer.
- Review each file independently, then run a cross-file integration check.
- Do not modify any files.
- Do not move to Task 2.
- For every issue: specify the file, section, severity, and recommended fix.
- Separate critical blockers from optional improvements.
- Return a confidence score and overall verdict.

**Scope provided:** Assignment context, list of files to review, explicit review criteria (grain clarity, SQL correctness, Redshift compatibility, SCD consistency, Snowplow/Fullstory mapping, no-Silver constraint, dbt test coverage, cross-file contradictions).

**Output:** Structured review report — overall verdict, file-by-file findings, cross-file integration issues, missing requirements check, prioritized fix list, confidence score (7.5/10 before fixes).

---

## Prompt 3 — Controlled Fix Pass

**Purpose:** Apply only the issues identified in Prompt 2. Nothing more.

**Key instructions given to Claude:**
- Act as a Lead Data Engineer applying review feedback.
- Fix only the issues from the review. Do not redesign.
- Do not change the folder structure.
- Do not add new models or SQL stubs.
- Do not start Task 2.
- Keep language professional and concise.
- After changes: list files modified, summarize what changed and why, note anything intentionally not applied and why.

**Explicit fix rules provided in the prompt:** Minimal changes only. Preserve model design. Maintain consistency across all seven files.

**Output:** Targeted edits across 7 files — critical bugs fixed (Redshift SPLIT_PART, SCD contradiction, actor classification order, ERD labels), documentation gaps filled (Assumption 15, artifact_id clarification, schema.yml source alignment).

---

## Prompt 4 — Final Critical Review

**Purpose:** Independent final check after fixes. Confirm submission readiness or surface any remaining issues.

**Key instructions given to Claude:**
- Act as a strict independent reviewer — no prior review context carried over.
- Read all seven files and check only for critical or meaningful issues.
- Do not suggest cosmetic changes.
- Do not request a second SQL stub (assignment requires only one).
- Return: verdict, critical issues, meaningful inconsistencies, optional improvements, confidence score, next step.

**Output:** Verdict — READY. No critical issues. No meaningful inconsistencies. Two optional improvements noted (schema.yml description wording, checksum_sha256 NULL production note). Confidence score: 9.0/10.

---

## Prompt 5 — Optional Improvements

**Purpose:** Apply the two optional improvements from the final review. Strictly scoped.

**Key instructions given to Claude:**
- Apply only these two changes, nothing else.
- Do not modify unrelated files.
- Do not change the model design.
- Confirm exactly which files changed.

**Output:** Two minimal edits — `schema.yml` description clarification, SQL stub production comment on NULL checksum handling.

---

## Prompt Design Principles

| Principle | How it was applied |
|---|---|
| Role prompting | Each prompt assigned an explicit role (generator, reviewer, engineer applying fixes) |
| Negative constraints | Every prompt included explicit "do not" rules to prevent scope creep |
| Structured output | Review prompts requested structured output (severity, file, fix) — not free-form commentary |
| Separation of analysis and action | Review stage and fix stage were separate prompts — never combined |
| Human checkpoints | The human reviewed Claude's output between each stage before issuing the next prompt |
