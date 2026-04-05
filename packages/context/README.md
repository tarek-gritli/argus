# Argus Context

Vector embeddings, dependency graph analysis, and AST parsing for context enrichment.

## Components

- **Embeddings** - Qdrant client for semantic code search
- **Dependency Graph** - Neo4j integration for codebase dependency analysis
- **AST Parsing** - Language-specific AST parsers for code analysis

## Usage

```python
from context import CodeEmbedder, DependencyGraph, LanguageParser

embedder = CodeEmbedder()
graph = DependencyGraph()
parser = LanguageParser("python")
```