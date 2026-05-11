import json
import logging
import re

import anthropic
from shared.config import get_settings
from shared.schemas.finding import FindingSchema

from .prompts import FIX_GENERATION_SYSTEM_PROMPT
from .schemas import FixProposal

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5"
_MAX_TOKENS = 2048

# Lines of context to include above and below the finding window.
# Enough for Claude to understand surrounding scope (imports, enclosing
# function, etc.) without sending the whole file.
_CONTEXT_WINDOW = 20


def _extract_snippets(file_content: str, line_start: int, line_end: int) -> tuple[str, str] | None:
    """
    Return (context_snippet, original_snippet), or None if line numbers are invalid.

    context_snippet  — _CONTEXT_WINDOW lines before and after the finding,
                       used in the user prompt so Claude has enough scope.
    original_snippet — the exact flagged lines only, stored on FixProposal
                       for the scorer and diff tooling.
    """
    lines = file_content.splitlines()
    total = len(lines)

    # 1-indexed → 0-indexed
    start_idx = line_start - 1
    end_idx = line_end  # exclusive for slicing

    if start_idx < 0 or end_idx > total or start_idx >= end_idx:
        return None

    original_snippet = "\n".join(lines[start_idx:end_idx])

    ctx_start = max(0, start_idx - _CONTEXT_WINDOW)
    ctx_end = min(total, end_idx + _CONTEXT_WINDOW)
    context_snippet = "\n".join(lines[ctx_start:ctx_end])

    return context_snippet, original_snippet


def generate_patch(finding: FindingSchema, file_content: str) -> FixProposal | None:
    snippets = _extract_snippets(file_content, finding.line_start, finding.line_end)
    if snippets is None:
        logger.error(
            "Invalid line numbers (%d-%d) for finding '%s' — skipping LLM call",
            finding.line_start,
            finding.line_end,
            finding.title,
        )
        return None
    context_snippet, original_snippet = snippets

    user_prompt = (
        f"File: {finding.file}\n\n"
        f"Finding:\n"
        f"  Title: {finding.title}\n"
        f"  Description: {finding.description}\n"
        f"  Severity: {finding.severity}\n"
        f"  Lines: {finding.line_start}-{finding.line_end}\n\n"
        f"Flagged lines ({finding.line_start}-{finding.line_end}):\n"
        f"```\n{original_snippet}\n```\n\n"
        f"Surrounding context (lines shown for reference only — do NOT rewrite these):\n"
        f"```\n{context_snippet}\n```\n"
    )

    settings = get_settings()
    if not settings.anthropic_api_key:
        logger.error("No Anthropic API key configured — cannot generate patch")
        return None

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        message = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            system=FIX_GENERATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = next(
            (getattr(block, "text", None) for block in message.content if getattr(block, "text", None)),
            None,
        )
        if not raw:
            logger.error("Claude returned an empty response for finding '%s'", finding.title)
            return None

        match = re.search(r"<fix>(.*?)</fix>", raw, re.DOTALL)
        if not match:
            logger.error(
                "No <fix> tags found in Claude response for finding '%s'",
                finding.title,
            )
            return None

        data = json.loads(match.group(1).strip())

        # Empty patched_code signals Claude's "cannot auto-fix" escape hatch.
        if not data.get("patched_code"):
            logger.info(
                "Claude declined to auto-fix finding '%s': %s",
                finding.title,
                data.get("description", "no reason given"),
            )
            return None

        proposal = FixProposal(**data, original_snippet=original_snippet)
        return proposal

    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Claude JSON for finding '%s': %s", finding.title, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected error generating patch for finding '%s': %s", finding.title, exc)
        return None
