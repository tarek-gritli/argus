"""Run the documentation agent locally against a diff file."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .agent import run_documentation_agent
from .schemas import AgentInput


def main() -> None:
    parser = argparse.ArgumentParser(prog="argus-docs-local")
    parser.add_argument("--diff", required=True, help="Path to a unified diff file")
    parser.add_argument("--repo", default="local/repo", help="owner/repo")
    parser.add_argument("--pr", type=int, default=1, help="PR number")
    args = parser.parse_args()

    diff_path = Path(args.diff)
    if not diff_path.exists():
        raise SystemExit(f"Diff file not found: {diff_path}")

    diff_text = diff_path.read_text(encoding="utf-8")

    # Build changed_files from added lines in the diff
    changed_files: dict[str, str] = {}
    current_file = ""
    lines_buf: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            if current_file and lines_buf:
                changed_files[current_file] = "\n".join(lines_buf)
            current_file = line[6:].strip()
            lines_buf = []
        elif line.startswith("+") and not line.startswith("+++"):
            lines_buf.append(line[1:])
    if current_file and lines_buf:
        changed_files[current_file] = "\n".join(lines_buf)

    agent_input = AgentInput(
        diff=diff_text,
        changed_files=changed_files,
        repo_full_name=args.repo,
        pr_number=args.pr,
        head_sha="local000",
        base_sha="local001",
    )

    findings = run_documentation_agent(agent_input)
    print(json.dumps([f.model_dump(mode="json") for f in findings], indent=2))


if __name__ == "__main__":
    main()
