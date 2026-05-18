# apps/agents/specialized/ticket_compliance/providers/base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TicketData:
    id: str
    title: str
    description: str
    url: str


class TicketProvider(Protocol):
    """Fetches a single ticket by ID. Return None if not found or not configured."""

    def fetch(self, ticket_id: str) -> TicketData | None: ...
