-- Grain: one row per (event_date, repository_key, package_type, package_name, actor_type)
{{
    config(
        materialized='incremental',
        unique_key=['event_date', 'repository_key', 'package_type', 'package_name', 'actor_type'],
        dist='repository_key',
        sort=['event_date', 'repository_key']
    )
}}

WITH stg_download_events AS (
    -- Parse SUPER columns, filter to artifact_download events from Artifactory app.
    SELECT
        DATE(collector_tstamp)                                                    AS event_date,
        event_id,
        collector_tstamp,
        user_id,
        COALESCE(
            JSON_EXTRACT_PATH_TEXT(unstruct_event, 'resolved_repository_key'),
            JSON_EXTRACT_PATH_TEXT(unstruct_event, 'repository_key')
        )                                                                         AS repository_key,
        JSON_EXTRACT_PATH_TEXT(unstruct_event, 'artifact_path')                  AS artifact_path,
        JSON_EXTRACT_PATH_TEXT(unstruct_event, 'checksum_sha256')                AS checksum_sha256,
        JSON_EXTRACT_PATH_TEXT(unstruct_event, 'package_name')                   AS package_name,
        JSON_EXTRACT_PATH_TEXT(unstruct_event, 'package_version')                AS package_version
    FROM raw.snowplow_events
    WHERE app_id     = 'artifactory'
      AND event_name = 'artifact_download'
      AND unstruct_event IS NOT NULL
    {%- if is_incremental() %}
      AND DATE(collector_tstamp) >= (SELECT MAX(event_date) - 3 FROM {{ this }})
    {%- endif %}
),

deduped_download_events AS (
    -- Deduplicate by event_id. Snowplow collector retries can produce duplicates.
    SELECT *
    FROM stg_download_events
    QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY collector_tstamp) = 1
),

stg_human_actors AS (
    -- Fullstory only records human browser sessions. CI bots do not appear here.
    SELECT DISTINCT user_id
    FROM raw.fullstory_events
    WHERE user_id IS NOT NULL
),

classified_events AS (
    -- Actor classification: Fullstory presence is checked first (strongest signal).
    SELECT
        d.event_date,
        d.event_id,
        d.collector_tstamp,
        d.user_id,
        d.repository_key,
        d.artifact_path,
        d.checksum_sha256,
        d.package_name,
        d.package_version,
        CASE
            WHEN h.user_id IS NOT NULL        THEN 'human'
            WHEN d.user_id ILIKE '%bot%'       THEN 'ci_bot'
            WHEN d.user_id ILIKE '%pipeline%'  THEN 'ci_bot'
            WHEN d.user_id ILIKE 'svc-%'       THEN 'service_account'
            ELSE                                    'unknown'
        END                                                                       AS actor_type
    FROM deduped_download_events d
    LEFT JOIN stg_human_actors h ON d.user_id = h.user_id
),

enriched_events AS (
    -- Enrich with repository metadata and artifact size.
    -- Assumption: size_bytes defaults to 0 when Airbyte has not yet indexed the artifact.
    SELECT
        c.event_date,
        c.event_id,
        c.collector_tstamp,
        c.user_id,
        c.repository_key,
        c.artifact_path,
        c.checksum_sha256,
        c.package_name,
        c.package_version,
        c.actor_type,
        COALESCE(r.package_type, 'unknown')                                       AS package_type,
        r.repository_mode,
        COALESCE(r.repository_name, c.repository_key)                             AS repository_name,
        r.owning_team,
        COALESCE(a.size_bytes, 0)                                                 AS artifact_size_bytes
    FROM classified_events c
    LEFT JOIN raw.airbyte_repositories r ON c.repository_key = r.repository_key
    LEFT JOIN raw.airbyte_artifacts    a
           ON c.repository_key  = a.repository_key
          AND c.artifact_path   = a.artifact_path
          AND c.checksum_sha256 = a.checksum_sha256
)

SELECT
    event_date,
    repository_key,
    COALESCE(package_type, 'unknown')                                             AS package_type,
    COALESCE(package_name, 'unknown')                                             AS package_name,
    actor_type,
    MAX(repository_name)                                                          AS repository_name,
    MAX(repository_mode)                                                          AS repository_mode,
    MAX(owning_team)                                                              AS owning_team,
    COUNT(*)                                                                      AS download_count,
    COUNT(DISTINCT user_id)                                                       AS unique_downloaders,
    SUM(artifact_size_bytes)                                                      AS total_downloaded_bytes,
    MIN(collector_tstamp)                                                         AS first_downloaded_at,
    MAX(collector_tstamp)                                                         AS last_downloaded_at
FROM enriched_events
GROUP BY 1, 2, 3, 4, 5

/*
 * Example analyst queries:
 *
 * -- Top 10 packages by downloads (last 30 days)
 * SELECT package_name, package_type, SUM(download_count) AS total_downloads
 * FROM gold_package_downloads_daily
 * WHERE event_date >= CURRENT_DATE - 30
 * GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10;
 *
 * -- Human vs CI bot split per repository (last 7 days)
 * SELECT repository_key, actor_type, SUM(download_count) AS downloads
 * FROM gold_package_downloads_daily
 * WHERE event_date >= CURRENT_DATE - 7
 * GROUP BY 1, 2 ORDER BY 1, 3 DESC;
 */
