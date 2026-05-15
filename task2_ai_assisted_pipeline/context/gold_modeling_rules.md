# Gold Modeling Rules — JFrog Artifactory Analytics

Design rules for Gold layer models in this analytics domain.
Applied by the modeling agent. Validated by the review agent.

---

## Layer Definition

Gold layer models are the final, analytics-ready tables that analysts query directly in Redshift.
There is no Silver layer — raw source tables are the only input.

---

## Grain

- Every Gold model must have an explicit, single grain.
- State it in the first SQL comment: `-- Grain: one row per (col1, col2, ...)`
- The grain must match: SQL GROUP BY, YAML unique_key, YAML description first sentence.
- Default to **daily grain** for fact tables unless the analyst explicitly requests otherwise.
- Dimensions: one row per natural key (repository_key, actor_id, artifact surrogate key).

## Wide and Flat

- Denormalize key dimension attributes directly into fact tables.
- Analysts should be able to answer most questions with a single `WHERE` + `GROUP BY` — no joins needed.
- Include at minimum: all grain keys, the 3–5 most commonly needed dimension attributes, all primary measures.
- Do not include every possible column — choose thoughtfully.

## No Silver Layer

- All transformation logic lives in staging CTEs within the Gold model.
- CTE naming convention (`stg_`, `deduped_`, `classified_`, `enriched_`, `typed_`) signals Silver-like operations inline.
- Do not reference any intermediate model that does not exist in the raw schema catalog.

## CTE Pattern for Snowplow Events

All models sourcing from `raw.snowplow_events` follow this CTE sequence:

```
stg_{model}_events       → parse SUPER columns, filter app_id and event_name, cast types
deduped_{model}_events   → QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ...) = 1
classified_{model}       → actor_type classification (Fullstory first, then naming conventions)
enriched_{model}         → LEFT JOIN raw.airbyte_artifacts and raw.airbyte_repositories
typed_{model}            → tag event direction (download vs. upload), calculate byte values
final SELECT             → aggregate to grain
```

## Actor Classification Rule

Always check Fullstory presence FIRST before naming conventions:

```sql
CASE
    WHEN h.user_id IS NOT NULL     THEN 'human'           -- Fullstory presence: strongest signal
    WHEN e.user_id ILIKE '%bot%'   THEN 'ci_bot'
    WHEN e.user_id ILIKE 'svc-%'   THEN 'service_account'
    ELSE                                'unknown'
END AS actor_type
```

The LEFT JOIN to a deduplicated Fullstory CTE must come before naming convention CASE checks.

## Virtual Repository Resolution

When a download is via a virtual repository, prefer the resolved local repository:

```sql
COALESCE(
    JSON_EXTRACT_PATH_TEXT(unstruct_event, 'resolved_repository_key'),
    JSON_EXTRACT_PATH_TEXT(unstruct_event, 'repository_key')
) AS repository_key
```

## Assumption Documentation

If any modeling decision is ambiguous or not derivable from the request, document it:

```sql
-- Assumption: treating download events as the primary grain signal.
-- Upload events are counted but do not create separate grain rows.
```

## SCD Strategy

- Gold dimensions default to SCD1 (current state) unless historical attribution is explicitly required.
- If SCD2 is needed, document it in the model definition — do not implement it without instruction.
- Artifacts are immutable (content-addressed by checksum) — no SCD needed for `gold_dim_artifact`.
