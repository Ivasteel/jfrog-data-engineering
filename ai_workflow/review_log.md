# Review Log — Task 1

This log summarizes the issues found during the Lead Data Engineer review (Prompt 2) and the final critical review (Prompt 4), and the fixes applied during the controlled fix pass (Prompt 3) and the optional improvement pass (Prompt 5).

Review confidence after generation: **7.5 / 10**
Review confidence after fixes: **9.0 / 10**

---

## Issues Found and Fixed

---

### Issue 1 — Invalid Redshift SQL: SPLIT_PART negative index

**Severity:** Critical  
**File:** `models/gold_fact_artifact_usage_daily.sql`  
**Finding:** `SPLIT_PART(e.artifact_path, '/', -1)` is not valid Redshift SQL. Redshift's `SPLIT_PART` function only accepts positive integer indexes. This would cause a runtime error.  
**Fix applied:** Replaced with `REVERSE(SPLIT_PART(REVERSE(e.artifact_path), '/', 1))` — a Redshift-compatible equivalent that extracts the last path segment by reversing the string, splitting on `/`, taking the first segment, and reversing back.

---

### Issue 2 — SCD contradiction across four files

**Severity:** Critical  
**Files:** `README.md`, `erd.mmd`, `assumptions.md`, `models/model_definitions.md`  
**Finding:** The ERD showed `scd_valid_from`, `scd_valid_to`, and `scd_status` columns in `gold_dim_repository` and `gold_dim_user_identity` entity boxes — implying SCD2 was implemented. The README dimension table said "SCD2 for ownership/mode changes." model_definitions.md and assumptions.md correctly stated SCD1 only. A reviewer reading all four files would see a direct contradiction.  
**Fix applied:**
- ERD: Removed SCD2 columns from entity boxes; replaced with `%%` comments stating they are not implemented in this submission.
- README: Updated dimension table to "SCD1 implemented / SCD2 recommended for ownership history."
- model_definitions.md: Aligned SCD wording on both dimensions to "SCD2 is recommended … **this submission implements SCD1**."
- assumptions.md: Wording already correct; no change needed.

---

### Issue 3 — Actor classification priority inconsistency

**Severity:** Critical  
**Files:** `assumptions.md`, `models/gold_fact_artifact_usage_daily.sql`  
**Finding:** The CASE statement shown in assumptions.md checked bot/pipeline naming conventions before checking Fullstory presence. The SQL correctly checked Fullstory first (via LEFT JOIN + `h.user_id IS NOT NULL`). A human with "bot" in their username would be misclassified as `ci_bot` under the assumptions.md version.  
**Fix applied:** Reordered the CASE in assumptions.md to show Fullstory human detection first. Added an explanatory sentence: "Fullstory presence is checked first — it is the strongest human signal and overrides naming conventions."

---

### Issue 4 — ERD relationship label inaccuracies

**Severity:** Critical  
**File:** `erd.mmd`  
**Finding 4a:** The artifact relationship label read `"artifact_path + checksum"` — missing `repository_key`, which is part of the actual join key used in the SQL.  
**Finding 4b:** The user identity relationship label read `"actor lookup (actor_type)"` — implying a runtime JOIN. In the SQL, `gold_dim_user_identity` is not joined into the fact table; `actor_type` is classified inline in a staging CTE and denormalized directly.  
**Fix applied:**
- Artifact label changed to: `"repository_key + artifact_path + checksum"`.
- User identity label changed to: `"conceptual — actor_type denormalized into fact"`.

---

### Issue 5 — Missing Airbyte sync frequency assumption

**Severity:** Documentation gap  
**File:** `assumptions.md`  
**Finding:** `storage_bytes_eod` and `artifact_count_eod` in `gold_fact_repository_traffic_daily` depend on Airbyte having a daily snapshot, but no assumption documented the sync frequency or the approximation nature of end-of-day values.  
**Fix applied:** Added Assumption 15 — Airbyte syncs daily after midnight UTC; end-of-day storage values are approximations based on the most recent available snapshot, not a true point-in-time value.

---

### Issue 6 — artifact_id and last_modified_at not explained

**Severity:** Documentation gap  
**Files:** `assumptions.md`, `docs/raw_to_gold_mapping.md`  
**Finding:** `artifact_id` was defined in the assumed `raw.airbyte_artifacts` schema but never referenced in any SQL or mapping. `last_modified_at` was defined but also never mapped to a Gold column. Neither was explained, leaving open questions about whether they were intentionally excluded.  
**Fix applied:**
- `assumptions.md`: Added inline comments to the schema block — `artifact_id` marked as "Airbyte internal surrogate; NOT used as join key"; `last_modified_at` marked as "not mapped to Gold; artifacts are immutable after publish." Added a prose explanation below the schema block.
- `raw_to_gold_mapping.md`: Added explicit callouts in the Airbyte Artifact Manifest Mapping section.

---

### Issue 7 — checksum_sha256 NULL grain-key risk (optional)

**Severity:** Optional — production edge case  
**File:** `models/gold_fact_artifact_usage_daily.sql`  
**Finding:** `checksum_sha256` is extracted from the Snowplow payload via `JSON_EXTRACT_PATH_TEXT`, which returns NULL if the field is absent. Since `checksum_sha256` is a grain key, NULL rows would aggregate together under a single NULL key, conflating distinct artifacts. Not a bug in the stub context (code is not run), but a meaningful production risk.  
**Fix applied:** Added a three-line production note in the SQL directly above the `checksum_sha256` extraction, explaining the risk and recommending a `COALESCE` fallback or NULL pre-filter in production.

---

### Issue 8 — total_bytes_downloaded description misleading (optional)

**Severity:** Optional — documentation clarity  
**File:** `models/schema.yml`  
**Finding:** The column description read "artifact_size_bytes × download_count" — implying a multiplication. The SQL actually computes `SUM(downloaded_bytes)` where `downloaded_bytes` is set to `artifact_size_bytes` per event row in a staging CTE. Each event contributes its own size value; there is no multiplication in the final SELECT.  
**Fix applied:** Rewrote the description to: "Computed as SUM(downloaded_bytes) where downloaded_bytes equals artifact_size_bytes per download event row (0 when Airbyte has no size record). Not a simple multiplication — each event row contributes its own size value."

---

## Issues Identified But Not Applied

| Recommendation | Reason not applied |
|---|---|
| Add note in README that analysts don't need to join `gold_dim_user_identity` for most queries | Cosmetic — the use case table is accurate; adding a caveat would clutter the executive summary. |
| Add explicit Gold-on-Gold dependency statement for `gold_fact_repository_traffic_daily` | Already stated in model_definitions.md source field; adding more verbiage would be redundant. |
| Add DISTSTYLE ALL caveat for large artifact catalog in schema.yml | Covered by Assumption 13 in assumptions.md; duplicate note in schema.yml adds no value. |

---

## Final State After All Fixes

| File | Changes Made |
|---|---|
| `models/gold_fact_artifact_usage_daily.sql` | SPLIT_PART fix, deduplication comment, incremental filter note, NULL checksum production note |
| `assumptions.md` | Actor classification order fix, artifact_id/last_modified_at clarification, Assumption 15 added |
| `erd.mmd` | SCD columns removed, relationship labels corrected |
| `models/model_definitions.md` | SCD wording aligned, actor_type grain design note added |
| `README.md` | SCD table aligned, "What I Would Do Next" schema.yml item corrected |
| `models/schema.yml` | Source description aligned, total_bytes_downloaded description clarified |
| `docs/raw_to_gold_mapping.md` | Supplementary Snowplow note clarified, artifact_id and last_modified_at callouts added |
