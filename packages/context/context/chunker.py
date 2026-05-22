from __future__ import annotations

from dataclasses import dataclass

import tiktoken

_TOKENIZER = tiktoken.get_encoding("cl100k_base")
_MAX_TOKENS = 1000
_OVERLAP_LINES = 15

_LANG_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".c": "c",
    ".h": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
}

# node types that represent top-level named definitions per language
_NODE_TARGETS: dict[str, set[str]] = {
    "python": {"function_definition", "class_definition", "decorated_definition"},
    "javascript": {"function_declaration", "class_declaration", "export_statement", "lexical_declaration"},
    "typescript": {"function_declaration", "class_declaration", "export_statement", "lexical_declaration"},
    "go": {"function_declaration", "method_declaration", "type_declaration"},
    "java": {"class_declaration", "method_declaration", "interface_declaration", "enum_declaration"},
    "kotlin": {"function_declaration", "class_declaration", "object_declaration"},
    "cpp": {"function_definition", "class_specifier", "struct_specifier"},
    "c": {"function_definition"},
    "csharp": {"class_declaration", "method_declaration", "interface_declaration", "enum_declaration"},
    "ruby": {"method", "class", "module", "singleton_method"},
    "php": {"function_definition", "class_declaration", "method_declaration"},
}

# node types whose first named child is the identifier (name)
_NAME_NODE_TYPES = {
    "function_definition",
    "function_declaration",
    "method_declaration",
    "class_declaration",
    "class_definition",
    "class_specifier",
    "method",
    "singleton_method",
    "module",
    "object_declaration",
}

# languages that are class containers (for class_name extraction)
_CLASS_CONTAINERS = {
    "class_declaration",
    "class_definition",
    "class_specifier",
    "class",
    "module",
    "struct_specifier",
}


@dataclass
class CodeChunk:
    filepath: str
    start_line: int
    end_line: int
    content: str
    token_count: int
    function_name: str | None = None
    class_name: str | None = None


def extension_to_language(filepath: str) -> str:
    ext = "." + filepath.rsplit(".", 1)[-1] if "." in filepath else ""
    return _LANG_MAP.get(ext.lower(), "")


def chunk_file(source: str, language: str, filepath: str) -> list[CodeChunk]:
    if not source.strip():
        return []
    if language in _NODE_TARGETS:
        chunks = _ast_chunks(source, language, filepath)
        if chunks:
            return chunks
    return _window_chunks(source, filepath)


def _get_ts_language(language: str):
    if language == "python":
        import tree_sitter_python as m

        return m.language()
    if language in ("javascript", "typescript"):
        import tree_sitter_javascript as m

        return m.language()
    if language == "go":
        import tree_sitter_go as m

        return m.language()
    if language == "java":
        import tree_sitter_java as m

        return m.language()
    if language == "kotlin":
        import tree_sitter_kotlin as m

        return m.language()
    if language == "cpp":
        import tree_sitter_cpp as m

        return m.language()
    if language == "c":
        import tree_sitter_c as m

        return m.language()
    if language == "csharp":
        import tree_sitter_c_sharp as m

        return m.language()
    if language == "ruby":
        import tree_sitter_ruby as m

        return m.language()
    if language == "php":
        import tree_sitter_php as m

        return m.language()
    raise ValueError(f"unsupported language: {language}")


def _node_name(node) -> str | None:
    if node.type in _NAME_NODE_TYPES:
        for child in node.children:
            if child.type in ("identifier", "name", "type_identifier"):
                return child.text.decode("utf-8", errors="replace")
    return None


def _ast_chunks(source: str, language: str, filepath: str) -> list[CodeChunk]:
    try:
        from tree_sitter import Language, Parser

        lang = Language(_get_ts_language(language))
        parser = Parser(lang)
        tree = parser.parse(source.encode())
        target_types = _NODE_TARGETS[language]
        lines = source.splitlines(keepends=True)
        chunks: list[CodeChunk] = []

        def collect(node, current_class: str | None = None) -> None:
            is_class = node.type in _CLASS_CONTAINERS
            node_name = _node_name(node)
            next_class = node_name if is_class else current_class

            if node.type in target_types:
                start = node.start_point[0]
                end = node.end_point[0]
                text = "".join(lines[start : end + 1])
                fn_name = node_name if not is_class else None
                _split_and_collect(
                    text,
                    filepath,
                    start + 1,
                    end + 1,
                    chunks,
                    function_name=fn_name,
                    class_name=next_class if not is_class else node_name,
                )
            else:
                for child in node.children:
                    collect(child, next_class)

        collect(tree.root_node)

        # cover top-level code not inside any definition
        covered: set[int] = set()
        for c in chunks:
            covered.update(range(c.start_line, c.end_line + 1))
        remainder = [(i + 1, line) for i, line in enumerate(lines) if (i + 1) not in covered and line.strip()]
        if remainder:
            text = "".join(ln for _, ln in remainder)
            _split_and_collect(text, filepath, remainder[0][0], remainder[-1][0], chunks)

        return sorted(chunks, key=lambda c: c.start_line)
    except Exception:
        return []


def _split_and_collect(
    text: str,
    filepath: str,
    start_line: int,
    end_line: int,
    out: list[CodeChunk],
    function_name: str | None = None,
    class_name: str | None = None,
) -> None:
    tokens = _TOKENIZER.encode(text)
    if len(tokens) <= _MAX_TOKENS:
        out.append(
            CodeChunk(
                filepath=filepath,
                start_line=start_line,
                end_line=end_line,
                content=text,
                token_count=len(tokens),
                function_name=function_name,
                class_name=class_name,
            )
        )
        return

    lines = text.splitlines(keepends=True)
    window: list[str] = []
    window_start = start_line

    for _i, line in enumerate(lines):
        candidate = window + [line]
        toks = len(_TOKENIZER.encode("".join(candidate)))
        if toks > _MAX_TOKENS and window:
            # emit current window before adding the overflowing line
            content = "".join(window)
            line_end = window_start + len(window) - 1
            out.append(
                CodeChunk(
                    filepath=filepath,
                    start_line=window_start,
                    end_line=line_end,
                    content=content,
                    token_count=len(_TOKENIZER.encode(content)),
                    function_name=function_name,
                    class_name=class_name,
                )
            )
            overlap = window[-_OVERLAP_LINES:]
            window_start = line_end - len(overlap) + 1
            window = overlap + [line]
        else:
            window.append(line)

    if window:
        content = "".join(window)
        out.append(
            CodeChunk(
                filepath=filepath,
                start_line=window_start,
                end_line=start_line + len(lines) - 1,
                content=content,
                token_count=len(_TOKENIZER.encode(content)),
                function_name=function_name,
                class_name=class_name,
            )
        )


def _window_chunks(source: str, filepath: str) -> list[CodeChunk]:
    lines = source.splitlines(keepends=True)
    chunks: list[CodeChunk] = []
    window: list[str] = []
    window_start = 1

    for line_no, line in enumerate(lines, 1):
        candidate = window + [line]
        toks = len(_TOKENIZER.encode("".join(candidate)))
        if toks > _MAX_TOKENS and window:
            content = "".join(window)
            line_end = line_no - 1
            chunks.append(
                CodeChunk(
                    filepath=filepath,
                    start_line=window_start,
                    end_line=line_end,
                    content=content,
                    token_count=len(_TOKENIZER.encode(content)),
                )
            )
            overlap = window[-_OVERLAP_LINES:]
            window_start = line_end - len(overlap) + 1
            window = overlap + [line]
        else:
            window.append(line)

    if window:
        content = "".join(window)
        chunks.append(
            CodeChunk(
                filepath=filepath,
                start_line=window_start,
                end_line=window_start + len(window) - 1,
                content=content,
                token_count=len(_TOKENIZER.encode(content)),
            )
        )

    return chunks
