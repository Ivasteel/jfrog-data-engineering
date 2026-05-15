# Analyst Request — Ambiguous (Clarification Path)

This example demonstrates how the clarification agent handles an underspecified request.

---

## Request

> I want something showing package activity.

---

## Why This Request Is Ambiguous

| Signal | Present | Issue |
|---|---|---|
| Time grain | No | "activity" could be all-time, daily, weekly |
| Primary entity | Partial | "package" is present, but scope is unclear |
| Primary event | No | Download? Upload? Both? |
| Breakdown dimensions | No | By repository? By team? By package type? |
| Measures | No | Count? Bytes? Distinct users? |

The clarification agent routes this request before it reaches the modeling agent.

---

## Clarification Agent Response

```
Clarification needed before modeling can proceed.

I need the following information to design this model correctly:

1. What time period should the model cover — should it aggregate by day, by week,
   or show all-time totals?

2. By "activity" — do you mean downloads (pulls), uploads (pushes), or both?

3. Should the model break down by package name only, or also by repository
   and/or package type (docker, npm, maven...)?
```

---

## After Clarification — Resolved Request

> Daily downloads per package, broken down by package type and repository.
> Show distinct human users and CI bots separately.

This resolved request matches `examples/analyst_request.md` exactly — it now routes to the modeling agent.

---

## Failure Mode Demonstrated

If the analyst cannot provide a grain after 2 rounds of clarification, the pipeline exits with:

```
Could not determine model grain after clarification.
Please work with a data engineer to define the model requirements.
Exit code 2.
```

This prevents a malformed model from being generated and reviewed as if it were valid.
