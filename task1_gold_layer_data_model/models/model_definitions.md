# Gold Layer Model Definitions

Each model definition includes: grain, description, key columns, materialization strategy, and notes on SCD handling where relevant.

---

## Fact Tables

---

### `gold_fact_artifact_usage_daily`

**Grain:** One row per `(event_date, repository_key, artifact_path, checksum_sha256, actor_type)`

**Design note on actor_type in the grain:** Including `actor_type` as a grain component allows analysts to filter or pivot by actor type (human / ci_bot / service_account) with a simple `WHERE actor_type = 'human'` — no aggregation or sub-query needed. The trade-off is that the `unique_human_users`, `unique_service_accounts`, and `unique_ci_bots` columns will always be zero for non-matching `actor_type` rows. This is intentional: rolling up across `actor_type` still produces correct totals, and the per-type measures are available without joins.

**Description:**
Daily artifact-level consumption and production activity, broken down by actor type (human, service_account, ci_bot). This is the primary analytical fact table. It answers: *which artifacts are most downloaded, by whom, and from which repositories?*

Key dimension attributes are denormalized directly into the fact table to minimize joins at query time.

**Primary Use Cases:**
- Top-N most-downloaded artifacts
- Download volume by repository or package type
- Human vs. CI bot download ratio
- Upload activity by team or pipeline
- Actor-level activity trends

**Key Columns:**

| Column | Type | Description |
|---|---|---|
| `event_date` | DATE | Partition column. Calendar date of activity. |
| `repository_key` | VARCHAR | Artifactory repository identifier (PK component). |
| `artifact_path` | VARCHAR | Full path within the repository (PK component). |
| `checksum_sha256` | VARCHAR | SHA-256 of artifact content (PK component). |
| `actor_type` | VARCHAR | `'human'`, `'service_account'`, `'ci_bot'`, `'unknown'` (PK component). |
| `download_count` | BIGINT | Count of download events for this artifact on this date. |
| `upload_count` | BIGINT | Count of upload/deploy events for this artifact on this date. |
| `unique_human_users` | BIGINT | Distinct human user IDs who downloaded. |
| `unique_service_accounts` | BIGINT | Distinct service account IDs who downloaded. |
| `unique_ci_bots` | BIGINT | Distinct CI bot IDs who downloaded. |
| `total_bytes_downloaded` | BIGINT | Sum of artifact size × download count. |
| `total_bytes_uploaded` | BIGINT | Sum of artifact size × upload count. |
| `last_downloaded_at` | TIMESTAMP | Latest download timestamp on this date. |
| `last_uploaded_at` | TIMESTAMP | Latest upload timestamp on this date. |
| `repository_name` | VARCHAR | Denormalized from `gold_dim_repository`. |
| `repository_mode` | VARCHAR | `'local'`, `'remote'`, `'virtual'`. |
| `package_type` | VARCHAR | `'docker'`, `'npm'`, `'maven'`, `'pypi'`, `'helm'`, etc. |
| `package_name` | VARCHAR | Logical package name (e.g. `my-service`). |
| `package_version` | VARCHAR | Artifact version (e.g. `1.0.3`). |
| `artifact_name` | VARCHAR | File name component of the artifact path. |
| `owning_team` | VARCHAR | Team that owns the repository. |
| `pipeline_name` | VARCHAR | CI pipeline name if actor is a bot/service account; NULL for humans. |

**Materialization:** Incremental, insert-only, partitioned by `event_date`. Late-arrival window: 3 days.

**Distribution:** `DISTKEY(repository_key)` / `SORTKEY(event_date, repository_key)`

**Source events:** Snowplow `artifact_download` and `artifact_deploy` events.

**SQL stub:** See [gold_fact_artifact_usage_daily.sql](gold_fact_artifact_usage_daily.sql)

---

### `gold_fact_repository_traffic_daily`

**Grain:** One row per `(event_date, repository_key)`

**Description:**
Daily repository-level traffic and storage snapshot. Answers: *how is each repository growing, and how heavily is it used?*

**Primary Use Cases:**
- Storage growth over time per repository
- Repository traffic trends (upload vs. download velocity)
- Identifying abandoned or over-used repositories
- Capacity planning

**Key Columns:**

| Column | Type | Description |
|---|---|---|
| `event_date` | DATE | Calendar date. |
| `repository_key` | VARCHAR | Artifactory repository identifier. |
| `download_count` | BIGINT | Total downloads across all artifacts in this repository on this date. |
| `upload_count` | BIGINT | Total uploads across all artifacts on this date. |
| `unique_artifacts_downloaded` | BIGINT | Distinct artifacts downloaded. |
| `unique_artifacts_uploaded` | BIGINT | Distinct artifacts uploaded. |
| `unique_actors` | BIGINT | Distinct actor IDs (all types combined). |
| `total_downloaded_bytes` | BIGINT | Total bytes served on this date. |
| `total_uploaded_bytes` | BIGINT | Total bytes ingested on this date. |
| `storage_bytes_eod` | BIGINT | Estimated repository storage at end of day (from Airbyte artifact manifest). |
| `artifact_count_eod` | BIGINT | Total artifact count at end of day. |
| `repository_name` | VARCHAR | Denormalized. |
| `package_type` | VARCHAR | Denormalized. |
| `repository_mode` | VARCHAR | Denormalized. |
| `owning_team` | VARCHAR | Denormalized. |

**Materialization:** Incremental, partitioned by `event_date`.

**Distribution:** `DISTKEY(repository_key)` / `SORTKEY(event_date)`

**Source events:** Aggregated from `gold_fact_artifact_usage_daily` + Airbyte artifact manifest snapshots.

---

### `gold_fact_package_adoption_daily`

**Grain:** One row per `(event_date, package_name, repository_key)`

**Description:**
Daily package-level adoption signal. Answers: *which packages are gaining or losing traction over time?*

**Primary Use Cases:**
- Package popularity trends (rising, stable, declining)
- Version diversity (how many versions of a package are actively used?)
- First-adoption date for new packages
- Cross-repository package comparison

**Key Columns:**

| Column | Type | Description |
|---|---|---|
| `event_date` | DATE | Calendar date. |
| `package_name` | VARCHAR | Logical package name. |
| `repository_key` | VARCHAR | Repository where the package lives. |
| `download_count` | BIGINT | Total downloads of any version of this package on this date. |
| `unique_downloaders` | BIGINT | Distinct actor IDs who downloaded any version. |
| `upload_count` | BIGINT | New versions published on this date. |
| `active_version_count` | INTEGER | Number of distinct versions downloaded at least once on this date. |
| `latest_version_seen` | VARCHAR | Most recently uploaded version as of this date. |
| `first_seen_date` | DATE | Date when the first version was uploaded (slowly changing; max over history). |
| `last_download_at` | TIMESTAMP | Most recent download timestamp. |
| `package_type` | VARCHAR | Denormalized. |
| `repository_name` | VARCHAR | Denormalized. |

**Materialization:** Incremental, partitioned by `event_date`.

---

## Dimension Tables

---

### `gold_dim_repository`

**Grain:** One row per repository (SCD1 — current state only in this submission; SCD2 noted below).

**Description:**
Repository master data. Source: Airbyte sync of Artifactory repository configuration API.

**SCD Strategy:** SCD2 is recommended — `owning_team` and `repository_mode` can change, and historical attribution ("which team owned this repository when these downloads happened?") requires tracking prior states. SCD2 would add `scd_valid_from`, `scd_valid_to`, and `scd_is_current` columns; fact tables would join on `repository_key` within the matching date range. **This submission implements SCD1 (current state only)** due to time constraints.

**Key Columns:**

| Column | Type | Description |
|---|---|---|
| `repository_key` | VARCHAR PK | Natural key from Artifactory. |
| `repository_name` | VARCHAR | Human-readable name. |
| `package_type` | VARCHAR | `docker`, `npm`, `maven`, `pypi`, `helm`, etc. |
| `repository_mode` | VARCHAR | `local`, `remote`, `virtual`. |
| `owning_team` | VARCHAR | Team that owns this repository. |
| `created_at` | TIMESTAMP | When the repository was created. |
| `is_active` | BOOLEAN | Whether the repository is currently active. |

---

### `gold_dim_artifact`

**Grain:** One row per `(repository_key, artifact_path, checksum_sha256)`

**Description:**
Artifact master data. Artifacts are immutable once published (content-addressed by checksum). SCD2 is not needed — a new version is a new row.

**Key Columns:**

| Column | Type | Description |
|---|---|---|
| `artifact_surrogate_key` | VARCHAR PK | MD5 of `repository_key + artifact_path + checksum_sha256`. |
| `repository_key` | VARCHAR | FK to `gold_dim_repository`. |
| `artifact_path` | VARCHAR | Full path within the repository. |
| `artifact_name` | VARCHAR | File name component. |
| `package_name` | VARCHAR | Logical package name. |
| `package_version` | VARCHAR | Version string. |
| `checksum_sha256` | VARCHAR | Content hash — immutable natural key component. |
| `size_bytes` | BIGINT | Artifact size. |
| `first_uploaded_at` | TIMESTAMP | When first published. |
| `last_downloaded_at` | TIMESTAMP | Most recent download (updated on each load). |

---

### `gold_dim_user_identity`

**Grain:** One row per normalized actor identity (SCD1 — current state).

**Description:**
Unified identity dimension covering human users, service accounts, and CI bots. Human users are identified by presence in Fullstory events; bots and service accounts are identified by naming conventions in Snowplow `user_id`.

**SCD Strategy:** SCD2 is recommended — `team_name` changes on re-orgs and contractor rotations. Historical team attribution requires tracking prior states via `scd_valid_from`, `scd_valid_to`, and `scd_is_current`. **This submission implements SCD1 (current state only)** due to time constraints.

**Key Columns:**

| Column | Type | Description |
|---|---|---|
| `actor_id` | VARCHAR PK | Normalized actor identifier. |
| `actor_name` | VARCHAR | Display name. |
| `actor_type` | VARCHAR | `human`, `service_account`, `ci_bot`, `unknown`. |
| `email` | VARCHAR | Email if available (humans only). |
| `team_name` | VARCHAR | Owning team. |
| `is_service_account` | BOOLEAN | True for non-human service accounts. |
| `is_ci_bot` | BOOLEAN | True for CI pipeline bots. |
| `first_seen_at` | TIMESTAMP | Earliest Snowplow event for this actor. |
| `last_seen_at` | TIMESTAMP | Most recent Snowplow event. |
| `last_ui_seen_at` | TIMESTAMP | Most recent Fullstory event (NULL for bots). |
