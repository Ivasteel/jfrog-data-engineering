# Design Assumptions

All schema design is hypothetical. Raw source tables are not provided — the schema below is inferred from the entity descriptions in the assignment and common Artifactory/Snowplow patterns. Each assumption is called out explicitly so reviewers can evaluate reasoning rather than correctness.

---

## Raw Source Tables

### Assumption 1 — Snowplow event table structure

I assume Snowplow fires one event per artifact interaction (download or upload) via the Artifactory REST API or CLI. The raw table is:

```
raw.snowplow_events (
    event_id          VARCHAR,   -- deduplicated on this
    collector_tstamp  TIMESTAMP,
    event             VARCHAR,   -- e.g. 'unstruct'
    event_name        VARCHAR,   -- e.g. 'artifact_download', 'artifact_deploy'
    app_id            VARCHAR,   -- 'artifactory'
    user_id           VARCHAR,   -- human user or service account name
    contexts          SUPER,     -- JSON: session, device, identity context
    unstruct_event    SUPER      -- JSON payload: repo, path, checksum, size, package type
)
```

I extract artifact metadata from `unstruct_event` and actor identity from `contexts`.

### Assumption 2 — Fullstory event table structure

Fullstory tracks UI-level interactions only (browser sessions). I assume:

```
raw.fullstory_events (
    session_id        VARCHAR,
    user_id           VARCHAR,
    event_type        VARCHAR,   -- 'page_view', 'click', 'search', 'navigate'
    page_url          VARCHAR,
    element_tag       VARCHAR,
    occurred_at       TIMESTAMP
)
```

Fullstory events are UI signals, not artifact-level signals. I use them to enrich `gold_dim_user_identity` with `last_ui_seen_at` and to distinguish human users from CI bots (CI bots do not produce Fullstory events).

### Assumption 3 — Airbyte sync metadata

Airbyte syncs repository metadata and artifact manifest data from the Artifactory REST API into Redshift:

```
raw.airbyte_repositories (
    repository_key    VARCHAR PRIMARY KEY,
    repository_name   VARCHAR,
    package_type      VARCHAR,   -- 'docker', 'npm', 'maven', 'pypi', 'helm', etc.
    repository_mode   VARCHAR,   -- 'local', 'remote', 'virtual'
    owning_team       VARCHAR,
    created_at        TIMESTAMP,
    updated_at        TIMESTAMP,
    is_active         BOOLEAN
)

raw.airbyte_artifacts (
    artifact_id       VARCHAR,   -- Airbyte internal surrogate; NOT used as join key
    repository_key    VARCHAR,
    artifact_path     VARCHAR,
    artifact_name     VARCHAR,
    package_name      VARCHAR,
    package_version   VARCHAR,
    checksum_sha256   VARCHAR,
    size_bytes        BIGINT,
    created_at        TIMESTAMP,
    last_modified_at  TIMESTAMP  -- not mapped to Gold; artifacts are immutable after publish
)
```

The join key into `raw.airbyte_artifacts` is `(repository_key, artifact_path, checksum_sha256)`, not `artifact_id`. `last_modified_at` is not mapped to any Gold column — a published artifact's content does not change, so any modification would indicate a source data error.

### Assumption 4 — No Artifactory access log table exists in raw

Download and upload events come entirely from Snowplow. If Artifactory server-side access logs were available in raw, I would use those as the authoritative event source and treat Snowplow as a supplementary signal.

---

## Event Mapping Assumptions

### Assumption 5 — Download event identification

A Snowplow event with `event_name = 'artifact_download'` represents one artifact download. I deduplicate on `event_id`. If an artifact is requested via a virtual repository, the event payload contains both the virtual repository key and the resolved local repository key — I attribute the event to the resolved local repository.

### Assumption 6 — Upload / deploy event identification

A Snowplow event with `event_name IN ('artifact_deploy', 'artifact_publish')` represents one artifact upload. Promotions (moving an artifact between repositories) are treated as a new upload event in the target repository, not a download from the source.

### Assumption 7 — Actor type classification

Fullstory presence is checked first — it is the strongest human signal and overrides naming conventions. Naming pattern matching is applied only when no Fullstory record exists.

```
actor_type = CASE
    WHEN user_id IN (SELECT user_id FROM raw.fullstory_events)
                                     THEN 'human'          -- strongest signal; checked first
    WHEN user_id ILIKE '%bot%'       THEN 'ci_bot'
    WHEN user_id ILIKE '%pipeline%'  THEN 'ci_bot'
    WHEN user_id ILIKE 'svc-%'       THEN 'service_account'
    WHEN user_id ILIKE 'sa-%'        THEN 'service_account'
    ELSE                                  'unknown'
END
```

In the SQL implementation this is expressed as a LEFT JOIN to a deduplicated Fullstory actor CTE, with the Fullstory check (`h.user_id IS NOT NULL`) evaluated first in the CASE. CI bots and service accounts never appear in Fullstory.

### Assumption 8 — Pipeline name extraction

Pipeline name is extracted from `user_id` by stripping the bot/svc suffix, or from the `contexts` SUPER column if a CI context is present in the Snowplow payload. If neither is available, `pipeline_name` is NULL.

---

## Grain and SCD Assumptions

### Assumption 9 — Daily grain for all fact tables

All fact tables aggregate to daily grain (`event_date`). Sub-daily granularity is not required for the stated use cases (trend analysis, top-N rankings, storage growth). Sub-daily queries can use raw Snowplow events directly.

### Assumption 10 — SCD2 for repository ownership

Repository ownership (`owning_team`) and mode (`repository_mode`) can change. If historical attribution is required (e.g., "which team owned this repository when these downloads happened?"), `gold_dim_repository` must be SCD2. I call this out in the model definitions but implement only the SCD1 (current-state) version in this stub to stay within time constraints.

### Assumption 11 — SCD2 for user team membership

A user's `team_name` can change over time (re-orgs, contractor rotations). If historical team attribution matters, `gold_dim_user_identity` requires SCD2. I note the strategy but implement SCD1 in this submission.

### Assumption 12 — Artifact checksum as natural key

Artifacts are immutable once published. The natural key for `gold_dim_artifact` is `repository_key + artifact_path + checksum_sha256`. If the same binary is promoted to a different repository, it gets a new row with a new `repository_key`.

---

## Storage and Performance Assumptions

### Assumption 13 — Redshift sort and distribution keys

For `gold_fact_artifact_usage_daily`:
- `DISTKEY(repository_key)` — most queries filter or group by repository.
- `SORTKEY(event_date, repository_key)` — supports time-range filters efficiently.

For dimension tables:
- `DISTSTYLE ALL` — dimensions are small enough to broadcast to all slices.

### Assumption 14 — Incremental materialization

In production, fact tables would be materialized incrementally: insert new rows for `event_date = current_date - 1`, and allow a 3-day late-arrival window for reprocessing. This is noted in `schema.yml` but not implemented in the SQL stub.

### Assumption 15 — Airbyte sync frequency and end-of-day storage snapshots

Airbyte syncs `raw.airbyte_repositories` and `raw.airbyte_artifacts` once per day, scheduled after midnight UTC. The `storage_bytes_eod` and `artifact_count_eod` columns in `gold_fact_repository_traffic_daily` are derived from the most recent Airbyte snapshot available at transformation time — they represent an end-of-day approximation, not a true point-in-time value. If Airbyte sync frequency increases to sub-daily, these columns would need to be recalculated using the snapshot closest to 23:59 for each event_date.
