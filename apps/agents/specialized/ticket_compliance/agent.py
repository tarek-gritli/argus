# apps/agents/specialized/ticket_compliance/agent.py
from __future__ import annotations

import json
import logging
import re
from typing import Any

import anthropic
from shared.config import get_settings
from shared.schemas.finding import FindingSchema
from shared.telemetry import langfuse_context, observe

from .extractor import extract_ticket_refs
from .prompts.system import TICKET_COMPLIANCE_SYSTEM_PROMPT
from .providers.base import TicketData, TicketProvider
from .schemas import AgentInput
from .validator import validate_findings

logger = logging.getLogger(__name__)

_MODEL = "claude-haiku-4-5"
_MAX_TOKENS = 2048


def run_ticket_compliance_agent(
    agent_input: AgentInput,
    providers: dict[str, TicketProvider],
) -> list[FindingSchema]:
    """
    Pipeline:
      1. Extract issue references from PR title + body
      2. Fetch the first resolvable issue from any configured provider
      3. LLM: compare issue description vs. diff
      4. Validate confidence floor
      5. Return FindingSchema list
    """
    refs = extract_ticket_refs(agent_input.pr_title, agent_input.pr_description)
    if not refs:
        logger.info("ticket_compliance: no issue refs in PR #%d — skipping", agent_input.pr_number)
        return []

    ticket = _resolve_ticket(refs, providers)
    if ticket is None:
        logger.info("ticket_compliance: could not fetch any issue for PR #%d", agent_input.pr_number)
        return []

    logger.info("ticket_compliance: reviewing PR #%d against issue #%s", agent_input.pr_number, ticket.id)
    user_prompt = _build_user_prompt(agent_input, ticket)
    raw = _call_claude(user_prompt)
    raw_findings = _parse_findings(raw)
    validated = validate_findings(raw_findings)
    return _to_finding_schemas(validated)


def _resolve_ticket(
    refs: list[tuple[str, str]],
    providers: dict[str, TicketProvider],
) -> TicketData | None:
    for provider_name, ticket_id in refs:
        provider = providers.get(provider_name)
        if provider is None:
            continue
        try:
            ticket = provider.fetch(ticket_id)
        except Exception:
            logger.debug("ticket_compliance: provider %s failed for %s", provider_name, ticket_id, exc_info=True)
            continue
        if ticket is not None:
            return ticket
    return None


def _build_user_prompt(agent_input: AgentInput, ticket: TicketData) -> str:
    return "\n".join(
        [
            "## GitHub Issue",
            f"Issue #{ticket.id}: {ticket.title}",
            f"URL: {ticket.url}",
            "",
            f"Description:\n{ticket.description[:3000]}",
            "",
            "## Pull Request",
            f"Title: {agent_input.pr_title}",
            f"PR #{agent_input.pr_number} — {agent_input.repo_full_name}",
            "",
            f"PR Description:\n{agent_input.pr_description[:1000]}",
            "",
            "## Diff",
            "```diff",
            agent_input.diff[:30_000],
            "```",
            "",
            "Compare the issue requirements to the diff. Output ONLY a JSON array of findings.",
            "If the PR fully satisfies the issue, return: []",
        ]
    )


@observe(as_type="generation")
def _call_claude(user_prompt: str) -> str:
    settings = get_settings()
    if langfuse_context is not None:
        try:
            langfuse_context.update_current_observation(
                model=_MODEL,
                input={"system": TICKET_COMPLIANCE_SYSTEM_PROMPT, "user": user_prompt},
            )
        except Exception:
            logger.debug("telemetry update failed", exc_info=True)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=TICKET_COMPLIANCE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    for block in message.content:
        text = getattr(block, "text", None)
        if text:
            if langfuse_context is not None:
                try:
                    langfuse_context.update_current_observation(output=text)
                except Exception:
                    logger.debug("telemetry update failed", exc_info=True)
            return text
    raise ValueError("Claude response contained no text")


def _parse_findings(raw: str) -> list[dict[str, Any]]:
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        logger.warning("ticket_compliance: failed to parse LLM JSON response")
        return []
    if not isinstance(parsed, list):
        logger.warning("ticket_compliance: LLM output is not a JSON array")
        return []
    return [item for item in parsed if isinstance(item, dict)]


def _to_finding_schemas(findings: list[dict[str, Any]]) -> list[FindingSchema]:
    results = []
    for f in findings:
        try:
            results.append(FindingSchema(**f))
        except Exception:
            logger.warning("ticket_compliance: invalid finding dropped: %s", f)
    return results
