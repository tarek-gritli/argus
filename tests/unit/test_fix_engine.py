"""
Unit tests for the Fix Engine pipeline.

Mocking strategy:
- `generate_patch` is mocked at the pipeline level (fix_engine.pipeline.generate_patch)
  so tests never touch the Anthropic API.
- `validate_patch` and `score_patch` are tested directly with real logic so
  their behaviour is verified independently of the pipeline.
- `process_finding` is tested end-to-end (generator mocked, real validator +
  scorer) to confirm the full flow integrates correctly.
"""

import subprocess
from unittest.mock import patch

import pytest
from fix_engine.pipeline import process_finding, run_fix_pipeline
from fix_engine.schemas import FixProposal, ValidationResult
from fix_engine.scorer import score_patch
from fix_engine.validator import validate_patch
from shared.schemas.finding import FindingSchema

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_finding():
    return FindingSchema(
        agent="quality",
        severity="medium",
        file="test.py",
        line_start=2,
        line_end=2,
        title="Unused import",
        description="The os module is imported but never used",
        confidence=0.9,
    )


ORIGINAL_CODE = "import sys\nimport os\n\ndef hello():\n    print('hi')\n"


# ---------------------------------------------------------------------------
# Validator tests — Tier 1 (in-process)
# ---------------------------------------------------------------------------


def test_validator_python_valid_patch(mock_finding):
    """Empty patched_code deletes the flagged lines (unused import removal)."""
    proposal = FixProposal(patched_code="", description="Removed import")

    result = validate_patch(ORIGINAL_CODE, proposal, mock_finding)

    assert result.is_valid is True
    assert result.applied_patch is not None
    assert "import os" not in result.applied_patch
    assert result.patched_line_count > 0


def test_validator_python_invalid_syntax(mock_finding):
    """A patch that introduces a SyntaxError is rejected."""
    proposal = FixProposal(patched_code="def broken_func(", description="Broken")

    result = validate_patch(ORIGINAL_CODE, proposal, mock_finding)

    assert result.is_valid is False
    assert result.error_message is not None
    assert "SyntaxError" in result.error_message


def test_validator_json_valid(mock_finding):
    """A valid JSON patch is accepted."""
    mock_finding.file = "config.json"
    original = '{\n  "key": "old_value",\n  "other": 1\n}\n'
    mock_finding.line_start = 2
    mock_finding.line_end = 2
    proposal = FixProposal(patched_code='  "key": "new_value",', description="Updated key")

    result = validate_patch(original, proposal, mock_finding)

    assert result.is_valid is True
    assert '"new_value"' in result.applied_patch


def test_validator_json_invalid(mock_finding):
    """A patch that breaks JSON structure is rejected."""
    mock_finding.file = "config.json"
    original = '{\n  "key": "value"\n}\n'
    mock_finding.line_start = 2
    mock_finding.line_end = 2
    proposal = FixProposal(patched_code='  "key": value_missing_quotes', description="Bad patch")

    result = validate_patch(original, proposal, mock_finding)

    assert result.is_valid is False
    assert "JSONDecodeError" in result.error_message


# ---------------------------------------------------------------------------
# Validator tests — Tier 2 (process-based, tool availability guarded)
# ---------------------------------------------------------------------------


def test_validator_javascript_unbalanced_braces_caught(mock_finding):
    """
    JS files go through the structural fallback when node isn't available,
    and the structural validator catches unbalanced braces.

    The patch must replace ALL lines that contain the matching closing brace,
    otherwise the surviving lines re-balance the count and the check passes.
    Here we replace the entire 3-line function with only its opening line,
    so the patched file is left with one unmatched '{'.
    """
    mock_finding.file = "app.js"
    # A self-contained function: open and close brace are both inside the finding span.
    js_code = "function hello() {\n  console.log('hi');\n}\n"
    mock_finding.line_start = 1
    mock_finding.line_end = 3  # replace all 3 lines — closing '}' is gone after patch
    proposal = FixProposal(patched_code="function hello() {", description="Bad patch")

    with patch("fix_engine.validator.shutil.which", return_value=None):
        result = validate_patch(js_code, proposal, mock_finding)

    # patched file: "function hello() {\n" — one '{', zero '}' → unbalanced
    assert result.is_valid is False
    assert "unbalanced braces" in result.error_message.lower()


def test_validator_process_tool_timeout_treated_as_pass(mock_finding):
    """If an external validator times out, the patch is treated as valid."""
    mock_finding.file = "main.go"
    go_code = 'package main\n\nfunc main() {\n\tfmt.Println("hello")\n}\n'
    mock_finding.line_start = 4
    mock_finding.line_end = 4
    proposal = FixProposal(patched_code='\tfmt.Println("world")', description="Changed output")

    with patch("fix_engine.validator.shutil.which", return_value="/usr/bin/gofmt"), patch("fix_engine.validator.subprocess.run", side_effect=subprocess.TimeoutExpired("gofmt", 10)):
        result = validate_patch(go_code, proposal, mock_finding)

    assert result.is_valid is True


def test_validator_process_tool_not_installed_falls_through(mock_finding):
    """Missing toolchain binary degrades gracefully — patch is not rejected."""
    mock_finding.file = "main.rs"
    rs_code = 'fn main() {\n    println!("hello");\n}\n'
    mock_finding.line_start = 2
    mock_finding.line_end = 2
    proposal = FixProposal(patched_code='    println!("world");', description="Changed output")

    with patch("fix_engine.validator.shutil.which", return_value=None):
        result = validate_patch(rs_code, proposal, mock_finding)

    assert result.is_valid is True


# ---------------------------------------------------------------------------
# Validator tests — Tier 3 (structural heuristic)
# ---------------------------------------------------------------------------


def test_validator_structural_balanced_braces_pass(mock_finding):
    """A well-formed Java patch passes structural validation."""
    mock_finding.file = "Hello.java"
    java_code = 'public class Hello {\n    void greet() {\n        System.out.println("hi");\n    }\n}\n'
    mock_finding.line_start = 3
    mock_finding.line_end = 3
    proposal = FixProposal(
        patched_code='        System.out.println("hello");',
        description="Updated greeting",
    )

    result = validate_patch(java_code, proposal, mock_finding)

    assert result.is_valid is True


def test_validator_structural_unbalanced_parens_rejected(mock_finding):
    """An unbalanced parenthesis in a C++ patch is caught by the structural validator."""
    mock_finding.file = "main.cpp"
    cpp_code = '#include <iostream>\nint main() {\n    std::cout << "hi";\n    return 0;\n}\n'
    mock_finding.line_start = 3
    mock_finding.line_end = 3
    # Unclosed paren
    proposal = FixProposal(
        patched_code='    std::cout << "hello" << std::endl;(\n',
        description="Bad patch",
    )

    result = validate_patch(cpp_code, proposal, mock_finding)

    assert result.is_valid is False
    assert "unbalanced parentheses" in result.error_message.lower()


def test_validator_unknown_extension_always_passes(mock_finding):
    """Files with unknown extensions (.yaml, .md, etc.) always pass validation."""
    mock_finding.file = "config.yaml"
    yaml_code = "key: value\nother: 123\n"
    mock_finding.line_start = 1
    mock_finding.line_end = 1
    # Deliberately garbled — no validator runs for .yaml
    proposal = FixProposal(patched_code="key: {{{broken", description="Broken YAML")

    result = validate_patch(yaml_code, proposal, mock_finding)

    assert result.is_valid is True


# ---------------------------------------------------------------------------
# Validator tests — shared behaviour
# ---------------------------------------------------------------------------


def test_validator_line_numbers_out_of_bounds(mock_finding):
    """A finding whose line numbers exceed the file length returns an error."""
    mock_finding.line_start = 99
    mock_finding.line_end = 100
    proposal = FixProposal(patched_code="x = 1", description="Some fix")

    result = validate_patch(ORIGINAL_CODE, proposal, mock_finding)

    assert result.is_valid is False
    assert "out of bounds" in result.error_message.lower()


def test_validator_no_double_blank_line_at_boundary(mock_finding):
    """
    Regression: patched_code with leading/trailing newlines must not create
    double blank lines when spliced into the file.
    """
    proposal = FixProposal(
        patched_code="\nimport sys as system\n\n",
        description="Renamed import",
    )

    result = validate_patch(ORIGINAL_CODE, proposal, mock_finding)

    assert result.is_valid is True
    assert "\n\n\n" not in result.applied_patch


# ---------------------------------------------------------------------------
# Scorer tests
# ---------------------------------------------------------------------------


def test_scorer_invalid_result_always_zero(mock_finding):
    invalid_res = ValidationResult(is_valid=False, error_message="error")
    assert score_patch(invalid_res, mock_finding) == 0.0


def test_scorer_medium_severity(mock_finding):
    # baseline 0.9 − medium penalty 0.05 = 0.85, no churn (patched_line_count=0)
    valid_res = ValidationResult(is_valid=True, applied_patch="x = 1", patched_line_count=0)
    assert score_patch(valid_res, mock_finding) == 0.85


def test_scorer_critical_severity(mock_finding):
    # baseline 0.9 − critical penalty 0.15 = 0.75
    mock_finding.severity = "critical"
    valid_res = ValidationResult(is_valid=True, applied_patch="x = 1", patched_line_count=0)
    assert score_patch(valid_res, mock_finding) == 0.75


def test_scorer_high_severity(mock_finding):
    # baseline 0.9 − high penalty 0.10 = 0.80
    mock_finding.severity = "high"
    valid_res = ValidationResult(is_valid=True, applied_patch="x = 1", patched_line_count=0)
    assert score_patch(valid_res, mock_finding) == 0.80


def test_scorer_low_severity(mock_finding):
    # baseline 0.9 − low penalty 0.0 = 0.90
    mock_finding.severity = "low"
    valid_res = ValidationResult(is_valid=True, applied_patch="x = 1", patched_line_count=0)
    assert score_patch(valid_res, mock_finding) == 0.90


def test_scorer_info_severity(mock_finding):
    # info is treated identically to low — no penalty
    mock_finding.severity = "info"
    valid_res = ValidationResult(is_valid=True, applied_patch="x = 1", patched_line_count=0)
    assert score_patch(valid_res, mock_finding) == 0.90


def test_scorer_churn_penalty_applied(mock_finding):
    """
    A 1-line finding whose patch results in a very large file triggers the
    churn penalty (baseline 0.85 − churn 0.15 = 0.70).
    """
    # finding spans line 2–2 (1 line); patched file is 1000 lines → ratio = 1000
    valid_res = ValidationResult(is_valid=True, applied_patch="x = 1", patched_line_count=1000)
    score = score_patch(valid_res, mock_finding)
    # Should be 0.85 - 0.15 = 0.70
    assert score == pytest.approx(0.70, abs=1e-4)


def test_scorer_no_churn_penalty_below_threshold(mock_finding):
    """A modest file size after patching must NOT trigger the churn penalty."""
    # finding spans 1 line; patched file is 10 lines → ratio = 10, at boundary
    valid_res = ValidationResult(is_valid=True, applied_patch="x = 1", patched_line_count=10)
    score = score_patch(valid_res, mock_finding)
    # ratio == threshold, penalty should NOT apply → 0.85
    assert score == pytest.approx(0.85, abs=1e-4)


# ---------------------------------------------------------------------------
# Pipeline integration tests  (generator mocked, real validator + scorer)
# ---------------------------------------------------------------------------


@patch("fix_engine.pipeline.generate_patch")
def test_pipeline_success(mock_generate, mock_finding):
    """
    A valid patch above the confidence threshold populates finding.fix.
    Empty patched_code = delete the flagged lines (unused import).
    """
    mock_generate.return_value = FixProposal(patched_code="", description="Removed unused import")

    updated_finding = process_finding(mock_finding, ORIGINAL_CODE)

    assert updated_finding.fix is not None
    assert updated_finding.fix.diff == ""
    assert updated_finding.fix.description == "Removed unused import"


@patch("fix_engine.pipeline.generate_patch")
def test_pipeline_syntax_error_discarded(mock_generate, mock_finding):
    """A patch that fails syntax validation must NOT populate finding.fix."""
    mock_generate.return_value = FixProposal(patched_code="def ( {", description="Bad patch")

    updated_finding = process_finding(mock_finding, ORIGINAL_CODE)

    assert updated_finding.fix is None


@patch("fix_engine.pipeline.generate_patch")
def test_pipeline_no_patch_generated(mock_generate, mock_finding):
    """When the generator returns None, finding.fix stays unset."""
    mock_generate.return_value = None

    updated_finding = process_finding(mock_finding, ORIGINAL_CODE)

    assert updated_finding.fix is None


@patch("fix_engine.pipeline.generate_patch")
def test_pipeline_low_confidence_discarded(mock_generate, mock_finding):
    """
    A patch that is syntactically valid but scores at or below the threshold
    must NOT populate finding.fix.

    Math for this case:
      baseline 0.9 − critical penalty 0.15 − churn penalty 0.15 = 0.60
    The threshold is also 0.60, and the check is `<= threshold`, so the fix
    is discarded even when the score lands exactly on the boundary.
    """
    mock_finding.severity = "critical"
    # Return a patch that will produce a huge patched file to trigger churn.
    # We achieve this by targeting a 1-line finding and returning a massive block.
    big_patch = "\n".join(f"x_{i} = {i}" for i in range(5000))
    mock_generate.return_value = FixProposal(patched_code=big_patch, description="Suspicious large patch")

    updated_finding = process_finding(mock_finding, ORIGINAL_CODE)

    assert updated_finding.fix is None


@patch("fix_engine.pipeline.process_finding")
def test_run_fix_pipeline_calls_process_for_known_files(mock_process, mock_finding):
    """run_fix_pipeline delegates to process_finding for each finding with a known file."""
    mock_process.return_value = mock_finding
    findings = [mock_finding]
    files = {"test.py": ORIGINAL_CODE}

    result = run_fix_pipeline(findings, files)

    assert len(result) == 1
    mock_process.assert_called_once_with(mock_finding, ORIGINAL_CODE)


@patch("fix_engine.pipeline.process_finding")
def test_run_fix_pipeline_skips_unknown_files(mock_process, mock_finding):
    """Findings whose file is not in files_content are passed through untouched."""
    findings = [mock_finding]
    files = {}  # test.py not provided

    result = run_fix_pipeline(findings, files)

    assert len(result) == 1
    mock_process.assert_not_called()
    assert result[0].fix is None


def test_run_fix_pipeline_empty_inputs():
    """Empty findings list returns an empty list without errors."""
    result = run_fix_pipeline([], {})
    assert result == []
