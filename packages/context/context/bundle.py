from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ContextBundle:
    similar_chunks: list[dict] = field(default_factory=list)
    repo_id: str = ""

    @classmethod
    def empty(cls) -> ContextBundle:
        return cls()
