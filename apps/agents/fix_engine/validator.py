"""
Multi-language patch validator.

Architecture
────────────
Each language (or family of languages) registers a validator function with
the signature:

    (patched_content: str, finding: FindingSchema) -> ValidationResult | None

Returning None means "this validator cannot handle this file" — the
dispatcher will fall through to the next registered handler.  Returning a
ValidationResult short-circuits further checks.

The dispatch order is:

    1. Exact-match language validators  (Python, JSON, JS/TS …)
    2. Process-based validators         (Go, Rust — require toolchain)
    3. Structural heuristic validator   (universal fallback)

Adding a new language requires only a new function decorated with
@register_validator(".ext") — nothing else changes.
"""

import ast
import json
import logging
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from shared.schemas.finding import FindingSchema

from .schemas import FixProposal, ValidationResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validator registry
# ---------------------------------------------------------------------------

# Maps file extension (e.g. ".py") → ordered list of validator callables.
ValidatorFn = Callable[[str, FindingSchema], ValidationResult | None]
_REGISTRY: dict[str, list[ValidatorFn]] = {}


def register_validator(*extensions: str):
    """Decorator: register a function as a validator for one or more extensions."""

    def decorator(fn: ValidatorFn) -> ValidatorFn:
        for ext in extensions:
            _REGISTRY.setdefault(ext.lower(), []).append(fn)
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Tier 1 — stdlib / in-process validators
# ---------------------------------------------------------------------------


@register_validator(".py")
def _validate_python(content: str, finding: FindingSchema) -> ValidationResult | None:
    try:
        ast.parse(content)
        return None  # pass — let the caller build the success result
    except SyntaxError as exc:
        logger.warning("Python SyntaxError in patch for '%s': %s", finding.title, exc)
        return ValidationResult(is_valid=False, error_message=f"SyntaxError: {exc}")


@register_validator(".json")
def _validate_json(content: str, finding: FindingSchema) -> ValidationResult | None:
    try:
        json.loads(content)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error in patch for '%s': %s", finding.title, exc)
        return ValidationResult(is_valid=False, error_message=f"JSONDecodeError: {exc}")


# ---------------------------------------------------------------------------
# Tier 2 — process-based validators (require toolchain on PATH)
# ---------------------------------------------------------------------------


def _run_process_validator(
    content: str,
    finding: FindingSchema,
    suffix: str,
    cmd_template: list[str],  # use "{file}" as the placeholder for the tmp path
    tool_name: str,
) -> ValidationResult | None:
    """
    Write content to a temp file, run an external checker, and return a
    ValidationResult on failure or None on success.  If the tool isn't
    installed we log a debug message and return None (graceful degradation).
    """
    binary = cmd_template[0]
    if not shutil.which(binary):
        logger.debug(
            "Validator tool '%s' not found on PATH — skipping for '%s'",
            tool_name,
            finding.file,
        )
        return None

    with tempfile.NamedTemporaryFile(suffix=suffix, mode="w", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        cmd = [c.replace("{file}", tmp_path) for c in cmd_template]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            error = (result.stderr or result.stdout).strip()
            logger.warning("%s check failed for patch on '%s': %s", tool_name, finding.title, error)
            return ValidationResult(
                is_valid=False,
                error_message=f"{tool_name}: {error[:300]}",  # cap noisy output
            )
        return None  # pass
    except subprocess.TimeoutExpired:
        logger.warning("%s timed out validating patch for '%s'", tool_name, finding.title)
        return None  # treat timeout as pass — don't block on slow toolchains
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@register_validator(".go")
def _validate_go(content: str, finding: FindingSchema) -> ValidationResult | None:
    # `gofmt` exits non-zero on syntax errors and writes errors to stderr.
    return _run_process_validator(
        content,
        finding,
        suffix=".go",
        cmd_template=["gofmt", "{file}"],
        tool_name="gofmt",
    )


@register_validator(".rs")
def _validate_rust(content: str, finding: FindingSchema) -> ValidationResult | None:
    # `rustfmt --check` exits 1 if the file is not well-formed.
    return _run_process_validator(
        content,
        finding,
        suffix=".rs",
        cmd_template=["rustfmt", "--check", "--edition", "2021", "{file}"],
        tool_name="rustfmt",
    )


@register_validator(".js", ".mjs", ".cjs")
def _validate_javascript(content: str, finding: FindingSchema) -> ValidationResult | None:
    # `node --check` parses without executing — available in any Node install.
    return _run_process_validator(
        content,
        finding,
        suffix=".js",
        cmd_template=["node", "--check", "{file}"],
        tool_name="node",
    )


@register_validator(".ts", ".tsx")
def _validate_typescript(content: str, finding: FindingSchema) -> ValidationResult | None:
    # `tsc --noEmit --allowJs` — requires typescript installed globally.
    return _run_process_validator(
        content,
        finding,
        suffix=".ts",
        cmd_template=["tsc", "--noEmit", "--skipLibCheck", "--allowJs", "{file}"],
        tool_name="tsc",
    )


@register_validator(".rb")
def _validate_ruby(content: str, finding: FindingSchema) -> ValidationResult | None:
    # `ruby -c` checks syntax only, no execution.
    return _run_process_validator(
        content,
        finding,
        suffix=".rb",
        cmd_template=["ruby", "-c", "{file}"],
        tool_name="ruby",
    )


@register_validator(".php")
def _validate_php(content: str, finding: FindingSchema) -> ValidationResult | None:
    return _run_process_validator(
        content,
        finding,
        suffix=".php",
        cmd_template=["php", "-l", "{file}"],
        tool_name="php",
    )


# ---------------------------------------------------------------------------
# Tier 3 — structural heuristic (universal fallback for unknown extensions)
# ---------------------------------------------------------------------------

# Languages that use brace-delimited blocks.
_BRACE_LANGUAGES = {".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cpp", ".cs", ".go", ".rs", ".swift", ".kt", ".scala", ".php"}


def _validate_structural(content: str, finding: FindingSchema) -> ValidationResult | None:
    """
    Language-agnostic sanity checks.  Not a parser — catches the most common
    Claude mistakes: unclosed brackets from a partial patch.
    """
    ext = Path(finding.file).suffix.lower()

    if ext in _BRACE_LANGUAGES:
        opens = content.count("{") - content.count("}")
        parens = content.count("(") - content.count(")")
        square = content.count("[") - content.count("]")

        if opens != 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"Structural error: unbalanced braces (net {opens:+d} '{{').",
            )
        if parens != 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"Structural error: unbalanced parentheses (net {parens:+d} '(').",
            )
        if square != 0:
            return ValidationResult(
                is_valid=False,
                error_message=f"Structural error: unbalanced brackets (net {square:+d} '[').",
            )

    return None  # pass — no issues detected


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def validate_patch(original_code: str, proposal: FixProposal, finding: FindingSchema) -> ValidationResult:
    lines = original_code.splitlines(keepends=True)

    start_idx = finding.line_start - 1
    end_idx = finding.line_end  # exclusive for slicing

    if start_idx < 0 or end_idx > len(lines):
        return ValidationResult(
            is_valid=False,
            error_message=(f"Finding line numbers ({finding.line_start}-{finding.line_end}) are out of bounds for file with {len(lines)} lines."),
        )

    patched_code = proposal.patched_code.strip("\n")
    replacement = [patched_code + "\n"] if patched_code else []
    patch_lines = len(replacement[0].splitlines()) if replacement else 0

    patched_lines = lines[:start_idx] + replacement + lines[end_idx:]
    patched_content = "".join(patched_lines)
    line_count = len(patched_content.splitlines())

    # --- Language-specific validators (tiers 1 and 2) ---
    ext = Path(finding.file).suffix.lower()
    for validator_fn in _REGISTRY.get(ext, []):
        result = validator_fn(patched_content, finding)
        if result is not None:
            result.patched_line_count = line_count
            result.patch_line_count = patch_lines
            return result

    # --- Tier 3: structural heuristic for all files ---
    structural_result = _validate_structural(patched_content, finding)
    if structural_result is not None:
        structural_result.patched_line_count = line_count
        structural_result.patch_line_count = patch_lines
        return structural_result

    return ValidationResult(
        is_valid=True,
        applied_patch=patched_content,
        patched_line_count=line_count,
        patch_line_count=patch_lines,
    )
