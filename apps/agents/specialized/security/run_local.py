from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.shared.schemas import AgentTask

from .agent import run_security_agent


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="argus-security-local")
    parser.add_argument("--diff", required=True, help="Path to unified diff file")
    parser.add_argument("--pr", required=True, type=int, help="Pull request number")
    parser.add_argument("--repo", required=True, help="Repository identifier (owner/name)")
    parser.add_argument(
        "--exempt",
        nargs="*",
        default=["tests/", "fixtures/"],
        help="Path prefixes to exclude from scanning",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    diff_path = Path(args.diff)
    if not diff_path.exists():
        raise SystemExit(
            "Diff file not found: "
            f"{diff_path}. "
            "Create it first (example: git diff > sample.diff) "
            "or pass an existing file via --diff."
        )

    diff_text = diff_path.read_text(encoding="utf-8")

    task = AgentTask(
        diff=diff_text,
        pr_number=args.pr,
        repo_id=args.repo,
        repo_config={
            "exempt_paths": args.exempt,
            "severity_overrides": {},
        },
    )

    result = run_security_agent(task)
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    main()
