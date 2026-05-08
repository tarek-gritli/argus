"""
AST-based static analysis for the quality agent.

Runs BEFORE the LLM. Produces structured metrics that Claude uses as evidence,
not as the final word. Fast, deterministic, zero cost.
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class FunctionMetrics:
    name: str
    file: str
    line_start: int
    line_end: int
    cyclomatic_complexity: int
    max_nesting_depth: int
    line_count: int
    arg_count: int
    return_count: int


@dataclass
class FileMetrics:
    file: str
    functions: list[FunctionMetrics] = field(default_factory=list)
    class_count: int = 0
    import_count: int = 0
    unused_imports: list[str] = field(default_factory=list)
    magic_numbers: list[tuple[int, int | float]] = field(default_factory=list)  # (line, value)
    duplicate_block_hashes: list[str] = field(default_factory=list)
    parse_error: str | None = None


@dataclass
class StaticAnalysisResult:
    files: list[FileMetrics] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        """Render metrics as a readable block for the LLM prompt."""
        lines: list[str] = ["=== Static Analysis Metrics ==="]
        for fm in self.files:
            lines.append(f"\nFile: {fm.file}")
            if fm.parse_error:
                lines.append(f"  [parse error — skipped]: {fm.parse_error}")
                continue

            if fm.functions:
                lines.append("  Functions:")
                for fn in fm.functions:
                    lines.append(f"    {fn.name} (lines {fn.line_start}-{fn.line_end}): complexity={fn.cyclomatic_complexity}, nesting={fn.max_nesting_depth}, length={fn.line_count}L, args={fn.arg_count}")

            if fm.unused_imports:
                lines.append(f"  Unused imports: {', '.join(fm.unused_imports)}")

            if fm.magic_numbers:
                nums = ", ".join(f"line {ln}: {val}" for ln, val in fm.magic_numbers[:10])
                lines.append(f"  Magic numbers: {nums}")

            if fm.duplicate_block_hashes:
                lines.append(f"  Potential duplicate blocks detected: {len(fm.duplicate_block_hashes)}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Complexity calculation
# ---------------------------------------------------------------------------

# AST node types that each add 1 to cyclomatic complexity
_COMPLEXITY_NODES = (
    ast.If,
    ast.For,
    ast.While,
    ast.ExceptHandler,
    ast.With,
    ast.Assert,
    ast.comprehension,
    ast.BoolOp,  # `and` / `or` chains
)


def _cyclomatic_complexity(node: ast.AST) -> int:
    """Count decision points inside a function node. Baseline of 1."""
    count = 1
    for child in ast.walk(node):
        if isinstance(child, _COMPLEXITY_NODES):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Nesting depth
# ---------------------------------------------------------------------------

_NESTING_NODES = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)


def _max_nesting_depth(node: ast.AST, current: int = 0) -> int:
    depth = current
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _NESTING_NODES):
            depth = max(depth, _max_nesting_depth(child, current + 1))
        else:
            depth = max(depth, _max_nesting_depth(child, current))
    return depth


# ---------------------------------------------------------------------------
# Magic number detection
# ---------------------------------------------------------------------------

_MAGIC_NUMBER_WHITELIST = {0, 1, -1, 2, 100, 1000}


def _find_magic_numbers(tree: ast.AST) -> list[tuple[int, int | float]]:
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if node.value not in _MAGIC_NUMBER_WHITELIST:
                results.append((node.lineno, node.value))
    return results


# ---------------------------------------------------------------------------
# Unused import detection
# ---------------------------------------------------------------------------


def _find_unused_imports(tree: ast.AST, source: str) -> list[str]:
    imported_names: dict[str, str] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".")[0]
                imported_names[name] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                imported_names[name] = f"{node.module}.{alias.name}"

    used = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\b", source))
    return [
        full
        for local, full in imported_names.items()
        if local not in used or source.count(local) <= 1  # only in import line
    ]


# ---------------------------------------------------------------------------
# Duplicate block detection (hash-based)
# ---------------------------------------------------------------------------

_MIN_BLOCK_LINES = 6  # minimum lines to consider a block for duplication


def _hash_blocks(source: str) -> list[str]:
    """
    Slide a window over source lines, normalize whitespace, and hash blocks.
    Returns hashes that appear more than once.
    """
    lines = [ln.strip() for ln in source.splitlines() if ln.strip()]
    if len(lines) < _MIN_BLOCK_LINES:
        return []

    seen: dict[str, int] = {}
    for i in range(len(lines) - _MIN_BLOCK_LINES + 1):
        block = "\n".join(lines[i : i + _MIN_BLOCK_LINES])
        h = hashlib.md5(block.encode()).hexdigest()  # noqa: S324 — not crypto
        seen[h] = seen.get(h, 0) + 1

    return [h for h, count in seen.items() if count > 1]


# ---------------------------------------------------------------------------
# Per-file analysis
# ---------------------------------------------------------------------------


def analyze_file(file_path: str, source: str) -> FileMetrics:
    metrics = FileMetrics(file=file_path)

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        metrics.parse_error = str(exc)
        return metrics

    # Imports
    metrics.import_count = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)))
    metrics.unused_imports = _find_unused_imports(tree, source)

    # Magic numbers
    metrics.magic_numbers = _find_magic_numbers(tree)

    # Duplicate blocks
    metrics.duplicate_block_hashes = _hash_blocks(source)

    # Classes
    metrics.class_count = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))

    # Functions
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        end_line = getattr(node, "end_lineno", node.lineno)
        fn = FunctionMetrics(
            name=node.name,
            file=file_path,
            line_start=node.lineno,
            line_end=end_line,
            cyclomatic_complexity=_cyclomatic_complexity(node),
            max_nesting_depth=_max_nesting_depth(node),
            line_count=end_line - node.lineno + 1,
            arg_count=len(node.args.args) + len(node.args.posonlyargs) + len(node.args.kwonlyargs),
            return_count=sum(1 for n in ast.walk(node) if isinstance(n, ast.Return)),
        )
        metrics.functions.append(fn)

    return metrics


# ---------------------------------------------------------------------------
# Entry point — called by the agent
# ---------------------------------------------------------------------------


def run_static_analysis(changed_files: dict[str, str]) -> StaticAnalysisResult:
    """
    Analyze all changed Python files.

    Args:
        changed_files: mapping of repo-relative file path → full file source.
                       Non-Python files are skipped.

    Returns:
        StaticAnalysisResult with metrics for every Python file.
    """
    result = StaticAnalysisResult()
    for path, source in changed_files.items():
        if not path.endswith(".py"):
            continue
        result.files.append(analyze_file(path, source))
    return result
