# Raw Source → Gold Model Mapping

This document shows how each raw source table contributes to each Gold model. Because there is no Silver layer, all transformation logic lives in staging CTEs within the Gold models themselves.

---

## Source Table Summary

| Raw Table | Owner | What It Contains |
|---|---|---|
| `raw.snowplow_events` | Snowplow | One row per artifact interaction (download/upload) from REST API, CLI, and UI |
| `raw.fullstory_events` | Fullstory | One row per UI browser event (page views, clicks, navigation) |
| `raw.airbyte_repositories` | Airbyte | Repository configuration snapshot from Artifactory REST API |
| `raw.airbyte_artifacts` | Airbyte | Artifact manifest snapshot (path, checksum, size, package info) |

---

## Mapping Matrix

| Gold Model | raw.snowplow_events | raw.fullstory_events | raw.airbyte_repositories | raw.airbyte_artifacts |
|---|---|---|---|---|
| `gold_fact_artifact_usage_daily` | Primary source — all download/upload events | Actor classification only (human detection) | Repository metadata enrichment | Artifact size and name enrichment |
| `gold_fact_repository_traffic_daily` | Via `gold_fact_artifact_usage_daily` | Not used | Repository metadata | Storage/artifact count snapshots |
| `gold_fact_package_adoption_daily` | Via `gold_fact_artifact_usage_daily` | Not used | Repository metadata | Package/version metadata |
| `gold_dim_repository` | Not used | Not used | Primary source | Not used |
| `gold_dim_artifact` | Conceptual supplementary — would enrich first-seen date if Airbyte lacks it (no SQL stub provided) | Not used | Not used | Primary source |
| `gold_dim_user_identity` | Primary source — actor enumeration | Human/bot classification | Not used | Not used |

---

## Snowplow Event Mapping

### Download Events

```
raw.snowplow_events WHERE event_name = 'artifact_download'
  → gold_fact_artifact_usage_daily.download_count      (+1 per event)
  → gold_fact_artifact_usage_daily.total_bytes_downloaded (+artifact_size_bytes)
  → gold_fact_artifact_usage_daily.last_downloaded_at  (MAX collector_tstamp)
  → gold_fact_artifact_usage_daily.unique_human_users  (COUNT DISTINCT where actor_type='human')
  → gold_fact_artifact_usage_daily.unique_service_accounts
  → gold_fact_artifact_usage_daily.unique_ci_bots
```

**Payload fields used from `unstruct_event` SUPER column:**

| Snowplow field | Gold column | Notes |
|---|---|---|
| `unstruct_event.repository_key` | `repository_key` | Prefer `resolved_repository_key` if present (virtual repo resolution) |
| `unstruct_event.resolved_repository_key` | `repository_key` | Overrides `repository_key` if set |
| `unstruct_event.artifact_path` | `artifact_path` | Full path within repository |
| `unstruct_event.checksum_sha256` | `checksum_sha256` | Content hash |
| `unstruct_event.package_name` | `package_name` | Logical package name |
| `unstruct_event.package_version` | `package_version` | Version string |
| `user_id` | actor classification | Used to determine `actor_type` |
| `contexts.ci_pipeline_name` | `pipeline_name` | CI pipeline name from event context |
| `collector_tstamp` | `event_date`, `last_downloaded_at` | Timestamp of event |

### Upload / Deploy Events

```
raw.snowplow_events WHERE event_name IN ('artifact_deploy', 'artifact_publish')
  → gold_fact_artifact_usage_daily.upload_count         (+1 per event)
  → gold_fact_artifact_usage_daily.total_bytes_uploaded (+artifact_size_bytes)
  → gold_fact_artifact_usage_daily.last_uploaded_at     (MAX collector_tstamp)
```

Same payload field mapping as download events applies.

---

## Fullstory Event Mapping

Fullstory events are **UI-only signals**. They are NOT artifact-level events and do not contribute to fact table counts directly.

**Primary use: actor type classification**

```
raw.fullstory_events
  → stg_human_actors (DISTINCT user_id)
  → actor_type = 'human'  when user_id matches a Fullstory user_id
```

**Secondary use: gold_dim_user_identity enrichment**

```
raw.fullstory_events
  → gold_dim_user_identity.last_ui_seen_at   (MAX occurred_at per user_id)
```

**Not used for:** artifact counts, download/upload events, or fact table metrics. Fullstory session data would be the source for a separate `gold_fact_ui_session_activity_daily` model (not in scope for this submission).

---

## Airbyte Repository Mapping

```
raw.airbyte_repositories
  → gold_dim_repository (primary source, all columns)
  → gold_fact_artifact_usage_daily.repository_name     (denormalized)
  → gold_fact_artifact_usage_daily.repository_mode     (denormalized)
  → gold_fact_artifact_usage_daily.package_type        (denormalized)
  → gold_fact_artifact_usage_daily.owning_team         (denormalized)
```

---

## Airbyte Artifact Manifest Mapping

```
raw.airbyte_artifacts
  → gold_dim_artifact (primary source, all columns except artifact_id and last_modified_at)
  → gold_fact_artifact_usage_daily.artifact_size_bytes  (for byte calculations)
  → gold_fact_artifact_usage_daily.artifact_name        (denormalized)
  → gold_fact_repository_traffic_daily.storage_bytes_eod  (SUM per repository)
  → gold_fact_repository_traffic_daily.artifact_count_eod (COUNT per repository)

  artifact_id      — Airbyte internal surrogate; not used as join key in Gold models
  last_modified_at — not mapped to any Gold column; artifacts are immutable after publish
```

---

## Silver Layer Note

There is no Silver layer in this stack. The staging CTEs inside each Gold model perform the Silver-like transformations:

| Silver-like operation | Where it happens |
|---|---|
| Type casting (`TIMESTAMP`, `DATE`, `BIGINT`) | `stg_snowplow_events` CTE |
| Event deduplication (idempotent on `event_id`) | `stg_deduped` CTE |
| JSON payload extraction (`unstruct_event` SUPER) | `stg_snowplow_events` CTE |
| Actor type classification | `stg_classified` CTE |
| Artifact metadata enrichment | `stg_with_artifact_meta` CTE |
| Repository metadata enrichment | `stg_with_repo_meta` CTE |
| Event type flagging (download vs. upload) | `stg_typed` CTE |

If a Silver layer were introduced in the future, these CTEs would become standalone Silver models, and the Gold models would reference Silver rather than raw.
