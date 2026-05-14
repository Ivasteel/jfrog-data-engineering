/*
  gold_fact_artifact_usage_daily
  ─────────────────────────────────────────────────────────────────────────────
  Grain: one row per (event_date, repository_key, artifact_path,
                      checksum_sha256, actor_type)

  Purpose: daily artifact-level consumption and production activity,
  broken down by actor type (human / service_account / ci_bot / unknown).

  Source tables (raw layer — no Silver exists):
    raw.snowplow_events          — download and upload events from Artifactory
                                   REST API, CLI, and UI (via Snowplow tracker)
    raw.airbyte_repositories     — repository metadata synced via Airbyte
    raw.airbyte_artifacts        — artifact manifest synced via Airbyte
    raw.fullstory_events         — UI session events; used only for actor
                                   classification (human vs. bot detection)

  Assumptions (see assumptions.md for full detail):
    A1 — Snowplow fires one event per artifact interaction.
         event_name = 'artifact_download' | 'artifact_deploy' | 'artifact_publish'
    A2 — artifact metadata (repo, path, checksum, size, package) lives in
         unstruct_event SUPER column as JSON.
    A3 — actor identity is in user_id. Bot/SA detection via naming convention.
    A4 — a user_id present in fullstory_events is classified as 'human'.
    A5 — virtual-repository downloads are attributed to the resolved local repo
         via a resolved_repository_key field in unstruct_event (if present).
    A6 — size_bytes comes from airbyte_artifacts; if not matched, defaults to 0.

  Materialization (production):
    - Incremental, insert-only, partitioned by event_date.
    - Reprocess window: last 3 days to handle late-arriving Snowplow events.
    - DISTKEY(repository_key) / SORTKEY(event_date, repository_key)

  DBT config (if using DBT):
    {{ config(
        materialized  = 'incremental',
        unique_key    = ['event_date','repository_key','artifact_path',
                         'checksum_sha256','actor_type'],
        dist          = 'repository_key',
        sort          = ['event_date','repository_key'],
        incremental_strategy = 'delete+insert'
    ) }}
*/

-- ─── CTE 1: parse raw Snowplow events ────────────────────────────────────────
-- Extract artifact fields from the SUPER (JSON) unstruct_event column.
-- In Redshift SUPER, use JSON_EXTRACT_PATH_TEXT for scalar fields.
WITH stg_snowplow_events AS (
    SELECT
        event_id,
        collector_tstamp::DATE                                      AS event_date,
        collector_tstamp,
        event_name,
        user_id,

        -- Resolve to local repository: prefer resolved_repository_key if present
        COALESCE(
            JSON_EXTRACT_PATH_TEXT(unstruct_event, 'resolved_repository_key'),
            JSON_EXTRACT_PATH_TEXT(unstruct_event, 'repository_key')
        )                                                           AS repository_key,

        JSON_EXTRACT_PATH_TEXT(unstruct_event, 'artifact_path')    AS artifact_path,
        -- Production note: checksum_sha256 is a grain key; if absent from the payload,
        -- NULL rows aggregate together and conflate distinct artifacts.
        -- Add COALESCE(…, 'unknown') or filter NULL rows before this reaches Gold.
        JSON_EXTRACT_PATH_TEXT(unstruct_event, 'checksum_sha256')  AS checksum_sha256,
        JSON_EXTRACT_PATH_TEXT(unstruct_event, 'package_name')     AS package_name,
        JSON_EXTRACT_PATH_TEXT(unstruct_event, 'package_version')  AS package_version,

        -- Pipeline name: try CI context first, then parse from user_id suffix
        COALESCE(
            JSON_EXTRACT_PATH_TEXT(contexts, 'ci_pipeline_name'),
            CASE
                WHEN user_id ILIKE '%bot%'      THEN SPLIT_PART(user_id, '-bot', 1)
                WHEN user_id ILIKE '%pipeline%' THEN SPLIT_PART(user_id, '-pipeline', 1)
                ELSE NULL
            END
        )                                                           AS pipeline_name

    FROM raw.snowplow_events
    WHERE
        app_id = 'artifactory'
        AND event_name IN ('artifact_download', 'artifact_deploy', 'artifact_publish')
        AND event_id IS NOT NULL
        -- Incremental filter: reprocess last 3 days to catch late arrivals.
        -- In production DBT: wrap in {% if is_incremental() %} ... {% endif %}
        -- so that a full refresh loads all history, not just the trailing 3 days.
        AND collector_tstamp::DATE >= CURRENT_DATE - 3
),

-- ─── CTE 2: deduplicate Snowplow (idempotent on event_id) ────────────────────
-- Snowplow collector retries can produce duplicate event_ids under network retry
-- or tracker flush conditions; take the earliest occurrence as authoritative.
stg_deduped AS (
    SELECT *
    FROM stg_snowplow_events
    QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY collector_tstamp) = 1
),

-- ─── CTE 3: classify actors ──────────────────────────────────────────────────
-- Fullstory presence → human. Naming conventions → bot/service_account.
-- This CTE is a one-time scan; production would persist this as gold_dim_user_identity.
stg_human_actors AS (
    SELECT DISTINCT user_id
    FROM raw.fullstory_events
),

stg_classified AS (
    SELECT
        e.*,
        CASE
            WHEN h.user_id IS NOT NULL                   THEN 'human'
            WHEN e.user_id ILIKE '%bot%'                 THEN 'ci_bot'
            WHEN e.user_id ILIKE '%pipeline%'            THEN 'ci_bot'
            WHEN e.user_id ILIKE 'svc-%'                 THEN 'service_account'
            WHEN e.user_id ILIKE 'sa-%'                  THEN 'service_account'
            ELSE                                               'unknown'
        END                                              AS actor_type
    FROM stg_deduped e
    LEFT JOIN stg_human_actors h ON e.user_id = h.user_id
),

-- ─── CTE 4: join artifact metadata from Airbyte ──────────────────────────────
-- Airbyte provides artifact size and artifact_name (file name component).
-- Left join — if artifact not yet in manifest, size defaults to 0.
stg_with_artifact_meta AS (
    SELECT
        e.*,
        COALESCE(a.size_bytes, 0)                        AS artifact_size_bytes,
        COALESCE(
            a.artifact_name,
            -- SPLIT_PART does not support negative index in Redshift; reverse to extract last segment
            REVERSE(SPLIT_PART(REVERSE(e.artifact_path), '/', 1))
        )                                                AS artifact_name
    FROM stg_classified e
    LEFT JOIN raw.airbyte_artifacts a
        ON  e.repository_key  = a.repository_key
        AND e.artifact_path   = a.artifact_path
        AND e.checksum_sha256 = a.checksum_sha256
),

-- ─── CTE 5: join repository metadata from Airbyte ────────────────────────────
stg_with_repo_meta AS (
    SELECT
        e.*,
        COALESCE(r.repository_name, e.repository_key)   AS repository_name,
        r.package_type,
        r.repository_mode,
        r.owning_team
    FROM stg_with_artifact_meta e
    LEFT JOIN raw.airbyte_repositories r
        ON e.repository_key = r.repository_key
),

-- ─── CTE 6: split downloads and uploads, tag byte direction ──────────────────
stg_typed AS (
    SELECT
        *,
        CASE WHEN event_name = 'artifact_download'               THEN 1 ELSE 0 END AS is_download,
        CASE WHEN event_name IN ('artifact_deploy','artifact_publish') THEN 1 ELSE 0 END AS is_upload,
        CASE WHEN event_name = 'artifact_download'               THEN artifact_size_bytes ELSE 0 END AS downloaded_bytes,
        CASE WHEN event_name IN ('artifact_deploy','artifact_publish') THEN artifact_size_bytes ELSE 0 END AS uploaded_bytes
    FROM stg_with_repo_meta
)

-- ─── FINAL: aggregate to grain ───────────────────────────────────────────────
SELECT
    event_date,
    repository_key,
    artifact_path,
    checksum_sha256,
    actor_type,

    -- Measures
    SUM(is_download)                                                AS download_count,
    SUM(is_upload)                                                  AS upload_count,
    COUNT(DISTINCT CASE WHEN actor_type = 'human'           AND is_download = 1 THEN user_id END) AS unique_human_users,
    COUNT(DISTINCT CASE WHEN actor_type = 'service_account' AND is_download = 1 THEN user_id END) AS unique_service_accounts,
    COUNT(DISTINCT CASE WHEN actor_type = 'ci_bot'          AND is_download = 1 THEN user_id END) AS unique_ci_bots,
    SUM(downloaded_bytes)                                           AS total_bytes_downloaded,
    SUM(uploaded_bytes)                                             AS total_bytes_uploaded,
    MAX(CASE WHEN is_download = 1 THEN collector_tstamp END)        AS last_downloaded_at,
    MAX(CASE WHEN is_upload   = 1 THEN collector_tstamp END)        AS last_uploaded_at,

    -- Denormalized dimension attributes (wide/flat for analyst convenience)
    MAX(repository_name)                                            AS repository_name,
    MAX(repository_mode)                                            AS repository_mode,
    MAX(package_type)                                               AS package_type,
    MAX(package_name)                                               AS package_name,
    MAX(package_version)                                            AS package_version,
    MAX(artifact_name)                                              AS artifact_name,
    MAX(owning_team)                                                AS owning_team,
    MAX(pipeline_name)                                              AS pipeline_name

FROM stg_typed

GROUP BY
    event_date,
    repository_key,
    artifact_path,
    checksum_sha256,
    actor_type

/*
  ─── Example analyst queries ────────────────────────────────────────────────

  -- Top 10 most-downloaded artifacts last 30 days
  SELECT artifact_path, repository_key, package_type,
         SUM(download_count) AS total_downloads
  FROM gold_fact_artifact_usage_daily
  WHERE event_date >= CURRENT_DATE - 30
  GROUP BY 1,2,3
  ORDER BY total_downloads DESC
  LIMIT 10;

  -- Human vs CI bot download ratio by repository
  SELECT repository_name, actor_type,
         SUM(download_count)        AS downloads,
         SUM(total_bytes_downloaded) AS bytes_served
  FROM gold_fact_artifact_usage_daily
  WHERE event_date >= CURRENT_DATE - 7
  GROUP BY 1,2
  ORDER BY 1,2;

  -- Upload activity by team this week
  SELECT owning_team, package_type,
         SUM(upload_count) AS uploads
  FROM gold_fact_artifact_usage_daily
  WHERE event_date >= DATE_TRUNC('week', CURRENT_DATE)
    AND actor_type IN ('service_account','ci_bot')
  GROUP BY 1,2
  ORDER BY uploads DESC;
*/
