# Redshift Constraints — JFrog Artifactory Analytics

Redshift-specific rules that the modeling agent must follow.
The review agent validates SQL output against this document.

---

## Distribution Keys (DISTKEY)

- Choose the column most commonly used in GROUP BY and JOIN ON clauses.
- For fact tables: use `repository_key` — most analytics queries filter or group by repository.
- For dimension tables: use `DISTSTYLE ALL` if the table is estimated < 1M rows.
- Never use a high-cardinality column (e.g. `event_id`, `artifact_path`) as DISTKEY.

```sql
-- Fact table example
DISTKEY(repository_key)

-- Small dimension
DISTSTYLE ALL
```

## Sort Keys (SORTKEY)

- Lead with `event_date` for all daily fact tables (supports time-range scan pruning).
- Follow with the DISTKEY column.
- Use compound SORTKEY (not interleaved) for Gold layer models.

```sql
SORTKEY(event_date, repository_key)
```

## SUPER Column Access

- Always use `JSON_EXTRACT_PATH_TEXT(col, 'field_name')` for scalar field extraction.
- Never use dot-notation (`unstruct_event.field`) — not supported in Redshift SUPER.
- For nested paths: chain multiple calls or use `JSON_EXTRACT_PATH_TEXT(col, 'parent', 'child')`.

```sql
-- Correct
JSON_EXTRACT_PATH_TEXT(unstruct_event, 'artifact_path')

-- Wrong — will error
unstruct_event.artifact_path
```

## SPLIT_PART

- Redshift `SPLIT_PART` only accepts positive integers (1-indexed).
- **Never use negative indexes** — will cause a runtime error.
- To extract the last segment of a path, use the REVERSE pattern:

```sql
-- Correct: extract last segment of artifact_path
REVERSE(SPLIT_PART(REVERSE(artifact_path), '/', 1))

-- Wrong — invalid in Redshift
SPLIT_PART(artifact_path, '/', -1)
```

## QUALIFY Clause

- Supported in Redshift for window function filtering.
- Use for deduplication on event_id:

```sql
QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY collector_tstamp) = 1
```

## Window Functions

- `ROW_NUMBER()`, `RANK()`, `SUM() OVER`, `LAG()`, `LEAD()` — all supported.
- `QUALIFY` — supported (Redshift-specific extension).
- `ARRAY_AGG` — not supported in Redshift; use `LISTAGG` instead.

## Date Arithmetic

- `CURRENT_DATE - 3` — valid (integer subtraction from DATE).
- `DATE_TRUNC('week', CURRENT_DATE)` — valid.
- `DATEADD(day, -3, CURRENT_DATE)` — valid alternative.
- `INTERVAL '3 days'` syntax — use `DATEADD` instead for reliability.

## NULL Handling

- Always `COALESCE` nullable columns from LEFT JOINs before using them in measures or grain keys.
- `COALESCE(size_bytes, 0)` for numeric measures.
- `COALESCE(repository_name, repository_key)` for display columns.
- `NULLIF(col, '')` to treat empty strings as NULL.
