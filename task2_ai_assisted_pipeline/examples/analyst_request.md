# Analyst Request — Clear (Happy Path)

This is the primary example request used by `scripts/run_pipeline.py` as its default input.

---

## Request

> I need a daily model that shows how many times each package was downloaded,
> broken down by package type and repository. I also want to know how many distinct
> users downloaded each package per day, and whether those were humans or CI bots.

---

## Why This Request Is Clear

| Signal | Present | Value |
|---|---|---|
| Time grain | Yes | "daily" |
| Primary entity | Yes | "package" |
| Primary event | Yes | "downloaded" |
| Breakdown dimensions | Yes | "package type and repository" |
| Measures | Yes | "how many times", "distinct users" |
| Actor breakdown | Yes | "humans or CI bots" |

No clarification needed. Routes directly to the modeling agent.

---

## Expected Model Output

- **Model name:** `gold_package_downloads_daily`
- **Grain:** one row per `(event_date, repository_key, package_type, package_name, actor_type)`
- **Primary source:** `raw.snowplow_events` WHERE `event_name = 'artifact_download'`
- **Enrichment:** `raw.airbyte_repositories` for package_type, repository_name; `raw.airbyte_artifacts` for size_bytes
- **Actor classification:** `raw.fullstory_events` for human detection (Fullstory presence checked first; then naming patterns)
- **Key measures:** `download_count`, `unique_downloaders`, `total_downloaded_bytes`, `first_downloaded_at`, `last_downloaded_at`
- **Actor split:** represented as the `actor_type` grain dimension (`human`, `ci_bot`, `service_account`, `unknown`), not as separate measure columns
- **Denormalized dims:** `repository_name`, `repository_mode`, `owning_team`

See `generated_output/gold_package_downloads_daily.sql` and `.yml` for the pipeline output.
