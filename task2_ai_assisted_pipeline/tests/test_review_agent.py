"""
test_review_agent.py — Unit tests for run_pipeline review validation logic.

Run:
    python3 -m pytest task2_ai_assisted_pipeline/tests/test_review_agent.py -v

All tests run unconditionally (no skip), including:
    test_valid_generated_sql_passes_review
    test_negative_split_part_fails_review
    test_unknown_raw_table_fails_review

Remaining tests validate individual check logic and also run unconditionally.
"""

import sys
from pathlib import Path

import pytest

# Add scripts/ to sys.path so run_pipeline can be imported directly.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from run_pipeline import (
    run_review_validation,
    parse_model_output,
    load_context,
    check_ambiguity,
    generate_deterministic_model_output,
    CONTEXT_DIR,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def context():
    """Load real context files once per module."""
    return load_context(CONTEXT_DIR)


@pytest.fixture(scope="module")
def valid_sql_yml():
    """Return the deterministic generated SQL and YAML."""
    return generate_deterministic_model_output()


# ---------------------------------------------------------------------------
# Required test 1 — valid generated SQL and YAML must pass review
# ---------------------------------------------------------------------------

def test_valid_generated_sql_passes_review(context, valid_sql_yml):
    """The pre-authored model output passes all review checks (no FAIL results)."""
    sql, yml = valid_sql_yml
    review = run_review_validation(sql, yml, context, request=(
        "I need a daily model that shows how many times each package was downloaded, "
        "broken down by package type and repository."
    ))
    fail_checks = [c for c in review['checks'] if c['result'] == 'FAIL']
    assert fail_checks == [], (
        f"Expected no FAIL checks but got: {fail_checks}"
    )
    assert review['has_failures'] is False


# ---------------------------------------------------------------------------
# Required test 2 — negative SPLIT_PART index causes Check 2 to FAIL
# ---------------------------------------------------------------------------

def test_negative_split_part_fails_review(context):
    """SQL containing SPLIT_PART with a negative index fails Check 2."""
    sql = (
        "-- Grain: one row per (event_date)\n"
        "SELECT SPLIT_PART(artifact_path, '/', -1) AS artifact_name\n"
        "FROM raw.snowplow_events\n"
    )
    yml = "version: 2\nmodels:\n  - name: gold_test\n"
    review = run_review_validation(sql, yml, context)
    check2 = next(c for c in review['checks'] if c['id'] == 2)
    assert check2['result'] == 'FAIL', (
        f"Expected Check 2 FAIL for negative SPLIT_PART but got: {check2['result']}"
    )
    assert review['has_failures'] is True


# ---------------------------------------------------------------------------
# Required test 3 — unknown raw table causes Check 3 to FAIL
# ---------------------------------------------------------------------------

def test_unknown_raw_table_fails_review(context):
    """SQL referencing a raw table not in the catalog fails Check 3."""
    sql = (
        "-- Grain: one row per (event_date)\n"
        "SELECT event_id FROM raw.nonexistent_events_table\n"
    )
    yml = "version: 2\nmodels:\n  - name: gold_test\n"
    review = run_review_validation(sql, yml, context)
    check3 = next(c for c in review['checks'] if c['id'] == 3)
    assert check3['result'] == 'FAIL', (
        f"Expected Check 3 FAIL for unknown table but got: {check3['result']}"
    )
    assert 'raw.nonexistent_events_table' in check3['details']


# ---------------------------------------------------------------------------
# Check 1 — Grain declaration
# ---------------------------------------------------------------------------

def test_grain_declaration_pass(context):
    """SQL with -- Grain: comment passes Check 1."""
    sql = "-- Grain: one row per (event_date)\nSELECT 1 FROM raw.snowplow_events\n"
    yml = "version: 2\nmodels:\n  - name: gold_test\n"
    review = run_review_validation(sql, yml, context)
    check1 = next(c for c in review['checks'] if c['id'] == 1)
    assert check1['result'] == 'PASS'


def test_grain_declaration_fail_missing(context):
    """SQL without -- Grain: comment fails Check 1."""
    sql = "SELECT event_id FROM raw.snowplow_events\n"
    yml = "version: 2\nmodels:\n  - name: gold_test\n"
    review = run_review_validation(sql, yml, context)
    check1 = next(c for c in review['checks'] if c['id'] == 1)
    assert check1['result'] == 'FAIL'


# ---------------------------------------------------------------------------
# Check 4 — JSON field references
# ---------------------------------------------------------------------------

def test_unknown_json_field_fails_check4(context):
    """JSON_EXTRACT_PATH_TEXT with an unknown field name fails Check 4."""
    sql = (
        "-- Grain: one row per (event_date)\n"
        "SELECT JSON_EXTRACT_PATH_TEXT(unstruct_event, 'totally_made_up_field') AS x\n"
        "FROM raw.snowplow_events\n"
    )
    yml = "version: 2\nmodels:\n  - name: gold_test\n"
    review = run_review_validation(sql, yml, context)
    check4 = next(c for c in review['checks'] if c['id'] == 4)
    assert check4['result'] == 'FAIL'
    assert 'totally_made_up_field' in check4['details']


# ---------------------------------------------------------------------------
# Check 6 — Model name convention
# ---------------------------------------------------------------------------

def test_model_name_without_gold_prefix_fails_check6(context):
    """Model name without gold_ prefix fails Check 6."""
    sql = "-- Grain: one row per (event_date)\nSELECT 1 FROM raw.snowplow_events\n"
    yml = "version: 2\nmodels:\n  - name: package_downloads_daily\n"
    review = run_review_validation(sql, yml, context)
    check6 = next(c for c in review['checks'] if c['id'] == 6)
    assert check6['result'] == 'FAIL'


# ---------------------------------------------------------------------------
# Check 7 — Ambiguity detection
# ---------------------------------------------------------------------------

def test_clear_request_is_not_ambiguous():
    """The standard analyst request from examples/analyst_request.md is not flagged."""
    request = (
        "I need a daily model that shows how many times each package was downloaded, "
        "broken down by package type and repository. I also want to know how many distinct "
        "users downloaded each package per day, and whether those were humans or CI bots."
    )
    is_ambiguous, _ = check_ambiguity(request)
    assert is_ambiguous is False


def test_vague_request_is_ambiguous():
    """A vague request with no grain, time, or event is flagged as ambiguous."""
    is_ambiguous, reason = check_ambiguity("I want something showing package activity.")
    assert is_ambiguous is True
    assert reason != ""


# ---------------------------------------------------------------------------
# parse_model_output
# ---------------------------------------------------------------------------

def test_parse_extracts_grain_and_model_name(valid_sql_yml):
    """parse_model_output correctly extracts grain and model name."""
    sql, yml = valid_sql_yml
    parsed = parse_model_output(sql, yml)
    assert parsed['model_name'] == 'gold_package_downloads_daily'
    assert 'event_date' in parsed['grain']
    assert len(parsed['tables']) >= 3  # snowplow, airbyte_repositories, airbyte_artifacts, fullstory
