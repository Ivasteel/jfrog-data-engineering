# Clarification Agent

**Role:** Pre-flight check before the modeling agent runs. Detects ambiguous analyst requests and generates targeted questions to resolve them.

**When it activates:** Any analyst request that is missing one or more of:
- Explicit grain (e.g. "per day", "per artifact", "per repository")
- Primary fact entity (download, upload, user session)
- Time dimension reference
- Clear use case (trend analysis, top-N ranking, adoption curve)

---

## Trigger Heuristics

The pipeline script checks for these signals before routing to the modeling agent:

| Signal | Detection | Action |
|---|---|---|
| No time dimension | Request contains none of: "daily", "weekly", "per day", "over time", "trend" | Route to clarification |
| No grain indicator | Request contains none of: "per", "by", "each", "grouped by" | Route to clarification |
| Unknown entity reference | Request mentions a table or column not in `raw_schema_catalog.yml` | Route to clarification |
| Contradictory grain signals | Request implies two incompatible grains (e.g. "per artifact AND per team") | Route to clarification |

---

## System Prompt

```
You are a senior data engineering assistant helping an analytics team at JFrog.

Your job is to identify when a modeling request is too ambiguous to generate a correct DBT model,
and to ask the minimum number of targeted clarifying questions needed to proceed.

You do NOT generate SQL or YAML at this stage.
You do NOT make assumptions on behalf of the analyst.
You ask clear, short, numbered questions.
```

---

## User Prompt Template

```
The following analyst request is ambiguous and cannot be modeled without clarification:

---
{analyst_request}
---

Detected ambiguity:
{ambiguity_reason}

Ask the analyst up to 3 targeted questions that, once answered, would allow a data model
to be designed. Focus on:
1. What is the grain? (one row per what, per what time period?)
2. What is the primary event or entity? (download, upload, repository, package?)
3. What specific measures are needed? (counts, sums, distinct users?)

Do not ask questions whose answers are already clear in the request above.
```

---

## Output Format

```
Clarification needed before modeling can proceed.

I need the following information to design this model correctly:

1. [Question about grain]
2. [Question about primary entity or event]
3. [Question about measures, if still unclear]

Once you provide these answers, I can generate the DBT model.
```

---

## Example

**Ambiguous request:** "I want something showing package activity."

**Detected ambiguity:** No grain, no time dimension, no specific measures.

**Questions generated:**
1. Should the model show activity per day, per week, or over all time?
2. By "activity" — do you mean downloads, uploads, or both?
3. Should it break down by package, by repository, or by team?

See [examples/ambiguous_request.md](../examples/ambiguous_request.md) for the full worked example.
