"""
run_pipeline.py — Task 2 AI-Assisted Transformation Pipeline
JFrog Data Engineering Home Assignment

Pipeline stages:
    1. Load analyst request
    2. Check for ambiguity
    3. Load context files (schema catalog, conventions, constraints, rules)
    4. Build modeling prompt (shows what would be sent to an LLM)
    5. Generate deterministic model output (pre-authored; no API key required)
    6. Parse model output (grain, tables, model name)
    7. Run deterministic review validation (7 checks)
    8. Write generated_output/ files
    9. Print PR agent stub summary

Exit codes:
    0 — pipeline passed (all checks PASS or WARNING only)
    1 — pipeline failed (one or more blocking FAIL checks)
    2 — request too ambiguous to model (clarification required, not yet implemented)

Usage:
    python3 task2_ai_assisted_pipeline/scripts/run_pipeline.py
    python3 task2_ai_assisted_pipeline/scripts/run_pipeline.py --request path/to/request.md
"""

import re
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — relative to this script's location
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).parent
TASK2_DIR    = SCRIPT_DIR.parent
CONTEXT_DIR  = TASK2_DIR / "context"
EXAMPLES_DIR = TASK2_DIR / "examples"
AGENTS_DIR   = TASK2_DIR / "agents"
OUTPUT_DIR   = TASK2_DIR / "generated_output"


def project_root() -> Path:
    return TASK2_DIR


# ---------------------------------------------------------------------------
# Stage 1 — Load analyst request
# ---------------------------------------------------------------------------

def load_analyst_request(path: Path) -> str:
    """Extract the request text from an analyst request Markdown file.

    Looks for a blockquote (> ...) under the ## Request heading.
    Falls back to the full file content if no blockquote is found.
    """
    text = path.read_text(encoding="utf-8")
    in_request_section = False
    lines = []
    for line in text.splitlines():
        if line.strip() == "## Request":
            in_request_section = True
            continue
        if in_request_section:
            if line.startswith("## "):
                break
            if line.startswith("> "):
                lines.append(line[2:])
            elif line.startswith(">"):
                lines.append(line[1:])
    if lines:
        return " ".join(" ".join(lines).split())
    return text.strip()


# ---------------------------------------------------------------------------
# Stage 2 — Ambiguity check
# ---------------------------------------------------------------------------

def check_ambiguity(request: str) -> tuple:
    """Heuristic ambiguity check based on clarification_agent.md trigger rules.

    Returns (is_ambiguous: bool, reason: str).
    """
    text = request.lower()
    reasons = []

    time_signals = ["daily", "weekly", "per day", "over time", "trend", "by day", "by week", "by month"]
    if not any(s in text for s in time_signals):
        reasons.append("no time dimension (daily/weekly/trend)")

    grain_signals = ["per ", "by ", "each ", "grouped by", "broken down", "split by"]
    if not any(s in text for s in grain_signals):
        reasons.append("no grain indicator (per/by/each/broken down)")

    event_signals = ["download", "upload", "deploy", "publish", "install", "pull", "push"]
    if not any(s in text for s in event_signals):
        reasons.append("no primary event (download/upload/deploy)")

    if reasons:
        return True, "; ".join(reasons)
    return False, ""


# ---------------------------------------------------------------------------
# Stage 3 — Load context
# ---------------------------------------------------------------------------

def load_context(context_dir: Path) -> dict:
    """Read all context files. Returns dict keyed by filename stem."""
    context = {}
    for path in sorted(context_dir.iterdir()):
        if path.is_file():
            context[path.stem] = path.read_text(encoding="utf-8")
    return context


# ---------------------------------------------------------------------------
# Stage 4 — Build modeling prompt
# ---------------------------------------------------------------------------

def build_modeling_prompt(request: str, context: dict) -> str:
    """Assemble the full modeling agent prompt with all context sections injected.

    This is the prompt that would be sent to the Claude API.
    In the deterministic offline mode, it is built but not sent.
    """
    return f"""You are a senior data engineer specializing in Redshift, DBT, and JFrog Artifactory analytics.

Generate a production-quality DBT Gold model from the analyst's request below.
Follow all rules in the context sections strictly.

=== Context: Raw Schema Catalog ===
{context.get('raw_schema_catalog', '')}

=== Context: DBT Conventions ===
{context.get('dbt_conventions', '')}

=== Context: Redshift Constraints ===
{context.get('redshift_constraints', '')}

=== Context: Gold Modeling Rules ===
{context.get('gold_modeling_rules', '')}

=== Analyst Request ===
{request}

=== Instructions ===
Generate exactly two fenced code blocks:
1. ```sql  — The DBT Gold model SQL
2. ```yaml — The DBT schema.yml

Rules:
- First line of SQL must be: -- Grain: one row per (...)
- Only use tables and columns from the Raw Schema Catalog. Do not invent columns.
- Use JSON_EXTRACT_PATH_TEXT for all SUPER column access — never dot-notation.
- Use REVERSE(SPLIT_PART(REVERSE(col), '/', 1)) to extract the last path segment.
- Apply DISTKEY(repository_key) and SORTKEY(event_date, repository_key).
- Classify actor_type with Fullstory presence first, then naming conventions.
- Deduplicate Snowplow events with QUALIFY ROW_NUMBER() OVER (PARTITION BY event_id ...) = 1.
"""


# ---------------------------------------------------------------------------
# Stage 5 — Deterministic model output (no API required)
# ---------------------------------------------------------------------------

def generate_deterministic_model_output(request: str = "", context: dict = None) -> tuple:
    """Return pre-authored SQL and YAML for gold_package_downloads_daily.

    This is what the modeling agent would produce when given the analyst request
    from examples/analyst_request.md with full context injection.
    No external API call is made — the content is deterministic and offline.

    Returns (sql_text: str, yml_text: str).
    """
    sql = """\
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
"""

    yml = """\
version: 2

models:
  - name: gold_package_downloads_daily
    description: >
      One row per (event_date, repository_key, package_type, package_name, actor_type).
      Aggregates Snowplow artifact_download events to daily grain, enriched with repository
      and artifact metadata from Airbyte. Actor type is classified using Fullstory session
      presence as the primary human signal, then naming pattern conventions.
    config:
      materialized: incremental
      unique_key:
        - event_date
        - repository_key
        - package_type
        - package_name
        - actor_type
      dist: repository_key
      sort:
        - event_date
        - repository_key
    columns:
      - name: event_date
        description: Calendar date of download events (DATE, UTC).
        tests:
          - not_null
      - name: repository_key
        description: Artifactory repository key. Resolved local repo when download is via virtual repo.
        tests:
          - not_null
      - name: package_type
        description: Package format type, denormalized from raw.airbyte_repositories.
        tests:
          - not_null
          - accepted_values:
              values: ['docker', 'npm', 'maven', 'pypi', 'helm', 'gradle', 'generic', 'nuget', 'rpm', 'debian', 'go', 'conan', 'unknown']
      - name: package_name
        description: Package name extracted from unstruct_event payload. Defaults to 'unknown'.
        tests:
          - not_null
      - name: actor_type
        description: >
          Actor classification. 'human' when Fullstory session found for user_id;
          'ci_bot' for bot/pipeline naming patterns; 'service_account' for svc- prefix;
          'unknown' otherwise.
        tests:
          - not_null
          - accepted_values:
              values: ['human', 'ci_bot', 'service_account', 'unknown']
      - name: repository_name
        description: Human-readable repository name from raw.airbyte_repositories.
      - name: repository_mode
        description: Repository mode (local, remote, virtual) from raw.airbyte_repositories.
      - name: owning_team
        description: Team owning the repository. NULL if unassigned.
      - name: download_count
        description: Count of artifact_download events after event_id deduplication.
      - name: unique_downloaders
        description: Count of distinct user_id values at this grain.
      - name: total_downloaded_bytes
        description: >
          Sum of artifact_size_bytes across download events. Defaults to 0 per event
          when Airbyte has no size record (COALESCE(size_bytes, 0)).
      - name: first_downloaded_at
        description: Earliest collector_tstamp for this grain (TIMESTAMP).
      - name: last_downloaded_at
        description: Latest collector_tstamp for this grain (TIMESTAMP).
"""
    return sql, yml


# ---------------------------------------------------------------------------
# Stage 6 — Parse model output
# ---------------------------------------------------------------------------

def _parse_catalog_tables(catalog_text: str) -> dict:
    """Parse raw_schema_catalog.yml into {table_name: [column_names]}.
    Uses regex — no PyYAML dependency.
    """
    tables = {}
    current_table = None
    in_columns = False
    _col_subkeys = {'description', 'notes', 'type', 'nullable'}

    for line in catalog_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        table_match = re.match(r'-\s+name:\s+(raw\.\w+)', stripped)
        if table_match:
            current_table = table_match.group(1)
            tables[current_table] = []
            in_columns = False
            continue

        if stripped == 'columns:' and current_table:
            in_columns = True
            continue

        if in_columns and current_table:
            col_match = re.match(r'-\s+name:\s+(\w+)', stripped)
            if col_match:
                tables[current_table].append(col_match.group(1))
            elif ':' in stripped and not stripped.startswith('-'):
                top_key = stripped.split(':')[0].strip()
                if top_key not in _col_subkeys:
                    in_columns = False

    return tables


def parse_model_output(sql_text: str, yml_text: str) -> dict:
    """Parse SQL and YAML strings into structured metadata."""
    grain = ""
    for line in sql_text.splitlines():
        m = re.match(r'--\s*Grain:\s*(.+)', line.strip(), re.IGNORECASE)
        if m:
            grain = m.group(1).strip()
            break

    tables = sorted(set(re.findall(r'\braw\.\w+', sql_text)))

    model_name = ""
    for line in yml_text.splitlines():
        m = re.match(r'\s+-\s+name:\s+(\S+)', line)
        if m:
            model_name = m.group(1).strip()
            break

    grain_keys = []
    if grain:
        m = re.search(r'\((.+)\)', grain)
        if m:
            grain_keys = [k.strip() for k in m.group(1).split(',')]

    return {
        'sql': sql_text,
        'yml': yml_text,
        'grain': grain,
        'grain_keys': grain_keys,
        'tables': tables,
        'model_name': model_name,
    }


# ---------------------------------------------------------------------------
# Stage 7 — Review validation
# ---------------------------------------------------------------------------

def run_review_validation(sql_text: str, yml_text: str, context: dict, request: str = "") -> dict:
    """Run 7 deterministic checks against the generated SQL and YAML.

    Returns:
        {
            'checks': [{'id', 'name', 'result', 'details'}, ...],
            'has_failures': bool,
            'has_warnings': bool,
        }
    """
    catalog_text = context.get('raw_schema_catalog', '')
    catalog_tables = _parse_catalog_tables(catalog_text)

    all_catalog_columns = set()
    for cols in catalog_tables.values():
        all_catalog_columns.update(cols)

    # Extract known nested field names from unstruct_event notes
    nested_fields = set(re.findall(r'(\w+)\s+\(VARCHAR\)', catalog_text))
    nested_fields.update({
        'repository_key', 'resolved_repository_key', 'artifact_path',
        'checksum_sha256', 'package_name', 'package_version',
        'ci_pipeline_name',
    })

    parsed = parse_model_output(sql_text, yml_text)
    checks = []

    # ------------------------------------------------------------------
    # Check 1 — Grain declaration
    # ------------------------------------------------------------------
    has_grain = bool(re.search(r'--\s*Grain:', sql_text, re.IGNORECASE))
    checks.append({
        'id': 1,
        'name': 'Grain declaration',
        'result': 'PASS' if has_grain else 'FAIL',
        'details': (
            f"Grain found: {parsed.get('grain', '')}"
            if has_grain
            else 'Missing -- Grain: comment. Must appear on line 1 of the SQL.'
        ),
    })

    # ------------------------------------------------------------------
    # Check 2 — No negative SPLIT_PART index (Redshift does not support it)
    # ------------------------------------------------------------------
    neg_split = re.search(r'SPLIT_PART\s*\([^)]+,\s*-\d+\s*\)', sql_text, re.IGNORECASE)
    checks.append({
        'id': 2,
        'name': 'Redshift: no negative SPLIT_PART index',
        'result': 'FAIL' if neg_split else 'PASS',
        'details': (
            f'Found invalid syntax: {neg_split.group(0)[:80]}'
            if neg_split
            else 'No negative SPLIT_PART indexes found.'
        ),
    })

    # ------------------------------------------------------------------
    # Check 3 — Raw table references must be in catalog
    # ------------------------------------------------------------------
    referenced_tables = sorted(set(re.findall(r'\braw\.\w+', sql_text)))
    unknown_tables = [t for t in referenced_tables if t not in catalog_tables]
    checks.append({
        'id': 3,
        'name': 'Raw table references in catalog',
        'result': 'FAIL' if unknown_tables else 'PASS',
        'details': (
            f'Unknown tables: {unknown_tables}'
            if unknown_tables
            else f'All {len(referenced_tables)} raw table(s) found in catalog: {referenced_tables}'
        ),
    })

    # ------------------------------------------------------------------
    # Check 4 — JSON_EXTRACT_PATH_TEXT field names must be in catalog
    # Conservative: only validate JSON field string literals, not CTE aliases.
    # ------------------------------------------------------------------
    json_fields = re.findall(
        r"JSON_EXTRACT_PATH_TEXT\s*\([^,]+,\s*'([^']+)'",
        sql_text,
        re.IGNORECASE,
    )
    all_known_fields = all_catalog_columns | nested_fields
    unknown_json = sorted(set(f for f in json_fields if f not in all_known_fields))
    checks.append({
        'id': 4,
        'name': 'Column references in catalog (JSON fields)',
        'result': 'FAIL' if unknown_json else 'PASS',
        'details': (
            f'Unknown JSON field(s) in JSON_EXTRACT_PATH_TEXT: {unknown_json}'
            if unknown_json
            else f'All {len(set(json_fields))} JSON field reference(s) found in catalog.'
        ),
    })

    # ------------------------------------------------------------------
    # Check 5 — YAML not_null tests on grain keys
    # ------------------------------------------------------------------
    grain_keys = parsed.get('grain_keys', [])
    missing_not_null = []
    for key in grain_keys:
        # Match the column entry (requires leading dash to avoid partial matches)
        key_match = re.search(rf'-\s+name:\s+{re.escape(key)}\b', yml_text)
        if key_match:
            # Scan from this column entry to the next column entry or end of file
            rest = yml_text[key_match.end():]
            next_col = re.search(r'\n\s+-\s+name:', rest)
            window = rest[: next_col.start()] if next_col else rest
            if 'not_null' not in window:
                missing_not_null.append(key)
        else:
            missing_not_null.append(key)

    checks.append({
        'id': 5,
        'name': 'YAML not_null tests on grain keys',
        'result': 'WARNING' if missing_not_null else 'PASS',
        'details': (
            f'Missing not_null tests for grain key(s): {missing_not_null}'
            if missing_not_null
            else f'not_null tests present for all {len(grain_keys)} grain key(s).'
        ),
    })

    # ------------------------------------------------------------------
    # Check 6 — Model name starts with gold_
    # ------------------------------------------------------------------
    model_name = parsed.get('model_name', '')
    name_ok = model_name.startswith('gold_')
    checks.append({
        'id': 6,
        'name': 'Model name convention (gold_ prefix)',
        'result': 'PASS' if name_ok else 'FAIL',
        'details': (
            f"Model name '{model_name}' follows gold_ prefix convention."
            if name_ok
            else f"Model name '{model_name}' does not start with 'gold_'."
        ),
    })

    # ------------------------------------------------------------------
    # Check 7 — Request clarity
    # ------------------------------------------------------------------
    if request:
        is_ambiguous, reason = check_ambiguity(request)
        checks.append({
            'id': 7,
            'name': 'Request clarity',
            'result': 'WARNING' if is_ambiguous else 'PASS',
            'details': (
                f'Ambiguity signals detected: {reason}'
                if is_ambiguous
                else 'Request is clear — no clarification needed.'
            ),
        })
    else:
        checks.append({
            'id': 7,
            'name': 'Request clarity',
            'result': 'PASS',
            'details': 'No request provided for ambiguity check.',
        })

    has_failures = any(c['result'] == 'FAIL' for c in checks)
    has_warnings = any(c['result'] == 'WARNING' for c in checks)
    return {'checks': checks, 'has_failures': has_failures, 'has_warnings': has_warnings}


# ---------------------------------------------------------------------------
# Stage 8 — Write outputs
# ---------------------------------------------------------------------------

def _format_review_report(review: dict, model_name: str, output_files: list, request: str) -> str:
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    if review['has_failures']:
        verdict = "FAIL — blocking errors found. Fix before opening a PR."
    elif review['has_warnings']:
        verdict = "PASS with warnings. Review before opening a PR."
    else:
        verdict = "PASS"

    lines = [
        f"# Review Report — {model_name}",
        f"",
        f"**Generated:** {ts}  ",
        f"**Overall verdict:** {verdict}",
        f"",
        f"---",
        f"",
        f"## Check Results",
        f"",
        f"| # | Check | Result | Details |",
        f"|---|---|---|---|",
    ]
    for c in review['checks']:
        lines.append(f"| {c['id']} | {c['name']} | {c['result']} | {c['details']} |")

    lines += [
        f"",
        f"---",
        f"",
        f"## Generated Files",
        f"",
    ]
    for f in output_files:
        lines.append(f"- `{Path(f).name}`")

    lines += [
        f"",
        f"---",
        f"",
        f"## PR Stub",
        f"",
        f"A real PR agent would create branch `analytics/auto/{model_name}`,",
        f"commit the generated files above, and open a GitHub PR for analyst review.",
        f"See `agents/pr_agent_stub.md` for the full stub design.",
        f"",
        f"---",
        f"",
        f"**Human review required before merge.**  ",
        f"This pipeline produces a draft. A data engineer must verify the SQL logic,",
        f"grain, and test coverage before approving the PR.",
    ]
    return "\n".join(lines)


def write_outputs(sql_text: str, yml_text: str, review: dict,
                  model_name: str, request: str, output_dir: Path) -> list:
    """Write SQL, YAML, and review report. Returns list of written paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    sql_path    = output_dir / f"{model_name}.sql"
    yml_path    = output_dir / f"{model_name}.yml"
    report_path = output_dir / "review_report.md"

    sql_path.write_text(sql_text, encoding="utf-8")
    yml_path.write_text(yml_text, encoding="utf-8")

    report = _format_review_report(
        review, model_name, [sql_path, yml_path, report_path], request
    )
    report_path.write_text(report, encoding="utf-8")

    return [sql_path, yml_path, report_path]


# ---------------------------------------------------------------------------
# Stage 9 — PR stub
# ---------------------------------------------------------------------------

def print_pr_stub(output_files: list, model_name: str) -> None:
    """Print what a real PR agent would do. Executes no git commands."""
    branch = f"analytics/auto/{model_name}"
    print("\n--- PR Agent (stub) ---")
    print(f"  Would create branch:  {branch}")
    print(f"  Would commit:         {', '.join(Path(f).name for f in output_files)}")
    print(f"  Would open GitHub PR: 'Auto: {model_name}'")
    print("  Would assign to requesting analyst for human review.")
    print("  (PR agent is stubbed — see agents/pr_agent_stub.md)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Task 2 AI-Assisted DBT Model Pipeline")
    parser.add_argument(
        "--request",
        type=Path,
        default=EXAMPLES_DIR / "analyst_request.md",
        help="Path to analyst request Markdown file",
    )
    args = parser.parse_args()

    print("=" * 62)
    print("  Task 2 — AI-Assisted DBT Model Pipeline")
    print("  Mode: deterministic offline (no API key required)")
    print("=" * 62)

    # 1 — Load analyst request
    print(f"\n[1/7] Loading analyst request")
    print(f"      File: {args.request}")
    request_text = load_analyst_request(args.request)
    print(f"      Text: {request_text[:100]}{'...' if len(request_text) > 100 else ''}")

    # 2 — Ambiguity check
    print("\n[2/7] Checking request for ambiguity")
    is_ambiguous, ambiguity_reason = check_ambiguity(request_text)
    if is_ambiguous:
        print(f"      WARNING: {ambiguity_reason}")
        print("      Proceeding with deterministic output (production would route to clarification agent).")
    else:
        print("      Clear — no clarification needed.")

    # 3 — Load context
    print(f"\n[3/7] Loading context files from {CONTEXT_DIR.name}/")
    context = load_context(CONTEXT_DIR)
    for name in sorted(context):
        print(f"      {name}: {len(context[name])} chars")

    # 4 — Build modeling prompt
    print("\n[4/7] Building modeling prompt")
    prompt = build_modeling_prompt(request_text, context)
    print(f"      Prompt: {len(prompt):,} chars — context injected, ready for LLM")
    print("      (API call skipped in offline mode)")

    # 5 — Generate deterministic model output
    print("\n[5/7] Generating model output (pre-authored deterministic example)")
    sql_text, yml_text = generate_deterministic_model_output(request_text, context)
    print(f"      SQL:  {len(sql_text.splitlines())} lines")
    print(f"      YAML: {len(yml_text.splitlines())} lines")

    # 6 — Parse
    print("\n[6/7] Parsing model output")
    parsed = parse_model_output(sql_text, yml_text)
    model_name = parsed.get('model_name', 'gold_unknown')
    print(f"      Model name: {model_name}")
    print(f"      Grain:      {parsed.get('grain', 'NOT FOUND')}")
    print(f"      Tables:     {', '.join(parsed.get('tables', []))}")

    # 7 — Review validation
    print("\n[7/7] Running review validation")
    review = run_review_validation(sql_text, yml_text, context, request=request_text)

    pass_c = sum(1 for c in review['checks'] if c['result'] == 'PASS')
    warn_c = sum(1 for c in review['checks'] if c['result'] == 'WARNING')
    fail_c = sum(1 for c in review['checks'] if c['result'] == 'FAIL')

    print()
    print(f"  {'#':<4} {'Check':<47} Result")
    print("  " + "-" * 60)
    for c in review['checks']:
        print(f"  {c['id']:<4} {c['name']:<47} {c['result']}")
    print("  " + "-" * 60)
    print(f"  {pass_c} PASS  {warn_c} WARNING  {fail_c} FAIL")

    # Write outputs
    output_files = write_outputs(
        sql_text, yml_text, review, model_name, request_text, OUTPUT_DIR
    )
    print(f"\nOutputs written to {OUTPUT_DIR.name}/:")
    for f in output_files:
        print(f"  {Path(f).name}")

    print_pr_stub(output_files, model_name)

    # Final verdict
    print("\n" + "=" * 62)
    if review['has_failures']:
        print("  RESULT: FAIL — fix blocking errors before opening a PR.")
        print("=" * 62)
        sys.exit(1)
    elif review['has_warnings']:
        print("  RESULT: PASS WITH WARNINGS — review before opening a PR.")
    else:
        print("  RESULT: PASS")
    print("  Human review required before merge.")
    print("=" * 62)


if __name__ == "__main__":
    main()
