# Argus Agents

LangGraph-based agent orchestration for parallel code review.

## Agents

1. **Security Agent** - Detects vulnerabilities, secrets, OWASP risks
2. **Quality Agent** - Code style, complexity, maintainability
3. **Performance Agent** - Performance anti-patterns, algorithmic issues
4. **Testing Agent** - Test coverage, test quality assessment
5. **Docs Agent** - Documentation completeness, docstrings
6. **Best Practices Agent** - Language/framework patterns

## Architecture

```
Review Request
      │
      ▼
┌─────────────────┐
│  Orchestrator   │◀── LangGraph state machine
│  (LangGraph)    │
└────────┬────────┘
         │
    ┌────┴────┬────┬────┬────┬────┐
    ▼         ▼    ▼    ▼    ▼    ▼
  Sec     Quality Perf Test Docs Best
  Agent   Agent   Agent Agent Agent Agent
    │         │    │    │    │    │
    └─────────┴────┴────┴────┴────┘
              │
              ▼
      ┌───────────────┐
      │  Synthesizer  │
      │  (Aggregation)│
      └───────────────┘
              │
              ▼
       PR Comment
```

## Fix Suggestions

Auto-generated code fixes for common issues via:
- AST-based transformation
- LLM-generated patches
- Template-based corrections