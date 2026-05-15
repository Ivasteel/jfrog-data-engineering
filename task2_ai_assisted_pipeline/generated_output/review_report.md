# Review Report — gold_package_downloads_daily

**Generated:** 2026-05-15 06:36 UTC  
**Overall verdict:** PASS

---

## Check Results

| # | Check | Result | Details |
|---|---|---|---|
| 1 | Grain declaration | PASS | Grain found: one row per (event_date, repository_key, package_type, package_name, actor_type) |
| 2 | Redshift: no negative SPLIT_PART index | PASS | No negative SPLIT_PART indexes found. |
| 3 | Raw table references in catalog | PASS | All 4 raw table(s) found in catalog: ['raw.airbyte_artifacts', 'raw.airbyte_repositories', 'raw.fullstory_events', 'raw.snowplow_events'] |
| 4 | Column references in catalog (JSON fields) | PASS | All 6 JSON field reference(s) found in catalog. |
| 5 | YAML not_null tests on grain keys | PASS | not_null tests present for all 5 grain key(s). |
| 6 | Model name convention (gold_ prefix) | PASS | Model name 'gold_package_downloads_daily' follows gold_ prefix convention. |
| 7 | Request clarity | PASS | Request is clear — no clarification needed. |

---

## Generated Files

- `gold_package_downloads_daily.sql`
- `gold_package_downloads_daily.yml`
- `review_report.md`

---

## PR Stub

A real PR agent would create branch `analytics/auto/gold_package_downloads_daily`,
commit the generated files above, and open a GitHub PR for analyst review.
See `agents/pr_agent_stub.md` for the full stub design.

---

**Human review required before merge.**  
This pipeline produces a draft. A data engineer must verify the SQL logic,
grain, and test coverage before approving the PR.