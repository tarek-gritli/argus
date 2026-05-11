"""
Regex / line-scan patterns that complement AST analysis.

Used for checks that are easier to express as text patterns than AST walks:
- TODO/FIXME/HACK markers left in changed lines
- Overly long lines in the diff
- print() debug statements
- Commented-out code blocks
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class PatternHit:
    file: str
    line: int
    pattern_name: str
    matched_text: str


@dataclass
class PatternScanResult:
    hits: list[PatternHit] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        if not self.hits:
            return "=== Pattern Scan: no hits ==="
        lines = ["=== Pattern Scan Hits ==="]
        for hit in self.hits:
            lines.append(f"  {hit.file}:{hit.line} [{hit.pattern_name}] {hit.matched_text[:120]}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("debug_print", re.compile(r"^\+\s*print\s*\(")),
    ("todo_fixme", re.compile(r"^\+.*\b(TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)),
    ("commented_code", re.compile(r"^\+\s*#\s*(def |class |import |return |if |for )")),
    ("long_line", re.compile(r"^\+.{121,}")),  # >120 chars added lines
    ("bare_except", re.compile(r"^\+\s*except\s*:")),
    ("mutable_default_arg", re.compile(r"^\+\s*def .+\(.*(=\s*\[\]|=\s*\{\})")),
]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def scan_diff_patterns(diff: str, file_path: str) -> PatternScanResult:
    """
    Scan the raw unified diff of a single file for known patterns.

    Only inspects lines starting with '+' (additions).
    """
    result = PatternScanResult()
    current_line = 0

    for raw_line in diff.splitlines():
        # Track line numbers from diff hunk headers: @@ -a,b +c,d @@
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw_line)
        if hunk_match:
            current_line = int(hunk_match.group(1)) - 1
            continue

        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            current_line += 1
            for name, pattern in _PATTERNS:
                if pattern.search(raw_line):
                    result.hits.append(
                        PatternHit(
                            file=file_path,
                            line=current_line,
                            pattern_name=name,
                            matched_text=raw_line[1:].strip(),  # strip leading '+'
                        )
                    )
        elif not raw_line.startswith("-"):
            current_line += 1

    return result
