"""
AST-based test coverage analysis for the testing agent.

Runs BEFORE the LLM. Gives Claude structured facts:
- Which public functions/methods were added or modified in the diff
- Which test functions exist in the diff
- Assertion quality metrics (how many assertions per test, which assertion types)
- Whether test files were touched at all
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class PublicSymbol:
    name: str
    file: str
    line_start: int
    line_end: int
    kind: str  # "function" | "method" | "class"
    is_async: bool = False
    args: list[str] = field(default_factory=list)


@dataclass
class TestFunction:
    name: str
    file: str
    line_start: int
    line_end: int
    assertion_count: int
    assertion_types: list[str]  # e.g. ["assertEqual", "assertRaises", "assert"]
    # Names referenced inside the test body — used to guess what it covers
    referenced_names: list[str] = field(default_factory=list)


@dataclass
class FileTestMetrics:
    file: str
    is_test_file: bool
    public_symbols: list[PublicSymbol] = field(default_factory=list)
    test_functions: list[TestFunction] = field(default_factory=list)
    has_fixtures: bool = False  # pytest fixtures present
    has_parametrize: bool = False  # @pytest.mark.parametrize present
    parse_error: str | None = None


@dataclass
class CoverageAnalysisResult:
    files: list[FileTestMetrics] = field(default_factory=list)

    @property
    def source_files(self) -> list[FileTestMetrics]:
        return [f for f in self.files if not f.is_test_file]

    @property
    def test_files(self) -> list[FileTestMetrics]:
        return [f for f in self.files if f.is_test_file]

    @property
    def untested_symbols(self) -> list[tuple[PublicSymbol, str]]:
        """
        Returns (symbol, reason) pairs for public symbols with no apparent test coverage.
        Uses name-matching heuristic — not a coverage tool, just a diff-level signal.
        """
        tested_names: set[str] = set()
        for tf in self.test_files:
            for test_fn in tf.test_functions:
                tested_names.update(test_fn.referenced_names)

        result = []
        for sf in self.source_files:
            for sym in sf.public_symbols:
                if sym.name.startswith("_"):
                    continue
                # Heuristic: is the symbol name referenced in any test body?
                if sym.name not in tested_names:
                    result.append((sym, "no test references this name in the diff"))
        return result

    def to_prompt_context(self) -> str:
        lines = ["=== Test Coverage Analysis ==="]

        # Source file summary
        lines.append("\nSource files changed:")
        for sf in self.source_files:
            if sf.parse_error:
                lines.append(f"  {sf.file}: [parse error] {sf.parse_error}")
                continue
            sym_names = [s.name for s in sf.public_symbols if not s.name.startswith("_")]
            lines.append(f"  {sf.file}: {len(sf.public_symbols)} public symbols ({', '.join(sym_names[:8])}{'...' if len(sym_names) > 8 else ''})")

        # Test file summary
        lines.append("\nTest files changed:")
        if not self.test_files:
            lines.append("  [NONE — no test files were modified in this PR]")
        else:
            for tf in self.test_files:
                if tf.parse_error:
                    lines.append(f"  {tf.file}: [parse error] {tf.parse_error}")
                    continue
                lines.append(f"  {tf.file}: {len(tf.test_functions)} test functions, fixtures={'yes' if tf.has_fixtures else 'no'}, parametrize={'yes' if tf.has_parametrize else 'no'}")
                for test in tf.test_functions:
                    lines.append(f"    {test.name}: {test.assertion_count} assertions ({', '.join(set(test.assertion_types)) or 'none'})")

        # Untested symbols
        untested = self.untested_symbols
        if untested:
            lines.append(f"\nPotentially untested public symbols ({len(untested)}):")
            for sym, reason in untested[:12]:
                lines.append(f"  {sym.file}:{sym.line_start} {sym.kind} `{sym.name}` — {reason}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_test_file(path: str) -> bool:
    name = path.split("/")[-1]
    return name.startswith("test_") or name.endswith("_test.py")


def _get_public_symbols(tree: ast.AST, file_path: str) -> list[PublicSymbol]:
    symbols = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("__") and node.name.endswith("__"):
                continue  # skip dunder methods
            end_line = getattr(node, "end_lineno", node.lineno)
            args = [a.arg for a in node.args.args if a.arg != "self"]
            symbols.append(
                PublicSymbol(
                    name=node.name,
                    file=file_path,
                    line_start=node.lineno,
                    line_end=end_line,
                    kind="method" if _is_in_class(tree, node) else "function",
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    args=args,
                )
            )
        elif isinstance(node, ast.ClassDef):
            end_line = getattr(node, "end_lineno", node.lineno)
            symbols.append(
                PublicSymbol(
                    name=node.name,
                    file=file_path,
                    line_start=node.lineno,
                    line_end=end_line,
                    kind="class",
                )
            )
    return symbols


def _is_in_class(tree: ast.AST, target: ast.AST) -> bool:
    """Check if a function node is directly inside a class body."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in ast.walk(node):
                if item is target:
                    return True
    return False


# Assertion methods and builtins that indicate a test is actually asserting something
_ASSERTION_METHODS = {
    "assertEqual",
    "assertNotEqual",
    "assertTrue",
    "assertFalse",
    "assertIsNone",
    "assertIsNotNone",
    "assertIn",
    "assertNotIn",
    "assertRaises",
    "assertRaisesRegex",
    "assertAlmostEqual",
    "assertGreater",
    "assertLess",
    "assertGreaterEqual",
    "assertLessEqual",
    "assertRegex",
    "assertDictEqual",
    "assertListEqual",
    "assertSetEqual",
}


def _analyze_test_function(node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str) -> TestFunction:
    assertion_types = []
    referenced_names = set()

    for child in ast.walk(node):
        # Collect assert statements
        if isinstance(child, ast.Assert):
            assertion_types.append("assert")

        # Collect method calls (unittest-style assertions)
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Attribute):
                if child.func.attr in _ASSERTION_METHODS:
                    assertion_types.append(child.func.attr)
            # Collect all referenced names to guess coverage
            if isinstance(child.func, ast.Name):
                referenced_names.add(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                referenced_names.add(child.func.attr)

        # Also collect Name references (function/class names used in test body)
        if isinstance(child, ast.Name):
            referenced_names.add(child.id)

    end_line = getattr(node, "end_lineno", node.lineno)
    return TestFunction(
        name=node.name,
        file=file_path,
        line_start=node.lineno,
        line_end=end_line,
        assertion_count=len(assertion_types),
        assertion_types=assertion_types,
        referenced_names=list(referenced_names),
    )


def _has_fixtures(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Attribute) and decorator.attr == "fixture":
                    return True
                if isinstance(decorator, ast.Name) and decorator.id == "fixture":
                    return True
    return False


def _has_parametrize(tree: ast.AST) -> bool:
    source_check = ast.dump(tree)
    return "parametrize" in source_check


# ---------------------------------------------------------------------------
# Per-file analysis
# ---------------------------------------------------------------------------


def analyze_file(file_path: str, source: str) -> FileTestMetrics:
    is_test = _is_test_file(file_path)
    metrics = FileTestMetrics(file=file_path, is_test_file=is_test)

    if not file_path.endswith(".py"):
        return metrics

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as exc:
        metrics.parse_error = str(exc)
        return metrics

    if is_test:
        metrics.has_fixtures = _has_fixtures(tree)
        metrics.has_parametrize = _has_parametrize(tree)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_") or node.name.startswith("test"):
                    metrics.test_functions.append(_analyze_test_function(node, file_path))
    else:
        metrics.public_symbols = _get_public_symbols(tree, file_path)

    return metrics


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_coverage_analysis(changed_files: dict[str, str]) -> CoverageAnalysisResult:
    """
    Analyze all changed Python files for test coverage signals.

    Args:
        changed_files: mapping of repo-relative path → full file source.

    Returns:
        CoverageAnalysisResult with metrics for every Python file.
    """
    result = CoverageAnalysisResult()
    for path, source in changed_files.items():
        if not path.endswith(".py"):
            continue
        result.files.append(analyze_file(path, source))
    return result
