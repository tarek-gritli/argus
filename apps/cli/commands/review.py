from __future__ import annotations

import subprocess
from typing import Optional

import typer
from auth import load_token
from client import make_client
from rich.console import Console
from rich.table import Table

console = Console(width=200)

_SEVERITY_COLOR = {
    "critical": "red",
    "high": "orange3",
    "medium": "yellow",
    "low": "cyan",
    "info": "dim",
}


def review(files: Optional[list[str]] = typer.Argument(default=None)):
    """Review local changes. Optionally pass specific files to scope the review."""
    token = load_token()
    if not token:
        typer.echo("Not logged in. Run `argus login` first.", err=True)
        raise typer.Exit(code=1)

    diff = _get_diff(files)
    if not diff.strip():
        typer.echo("No changes detected.")
        return

    client = make_client(token=token)
    body: dict = {"diff": diff}
    if files:
        body["files"] = list(files)

    resp = client.post("/api/v1/reviews/local", json=body)
    if resp.status_code == 401:
        typer.echo("Session expired. Run `argus login` again.", err=True)
        raise typer.Exit(code=1)
    if resp.status_code != 200:
        typer.echo(f"Review failed ({resp.status_code}): {resp.text}", err=True)
        raise typer.Exit(code=1)

    findings = resp.json().get("findings", [])
    if not findings:
        typer.echo("No issues found.")
        return

    _print_findings(findings)


def _get_diff(files: list[str] | None = None) -> str:
    cmd = ["git", "diff", "HEAD"]
    if files:
        cmd += ["--", *files]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def _print_findings(findings: list[dict]) -> None:
    table = Table(title=f"{len(findings)} finding(s)", show_lines=True)
    table.add_column("Severity", style="bold", width=10)
    table.add_column("File", width=30)
    table.add_column("Line", width=8)
    table.add_column("Title")
    table.add_column("Suggestion")

    for f in findings:
        sev = f.get("severity", "info").lower()
        color = _SEVERITY_COLOR.get(sev, "white")
        table.add_row(
            f"[{color}]{sev.upper()}[/{color}]",
            f.get("file", ""),
            str(f.get("line_start", "")),
            f.get("title", ""),
            f.get("suggestion") or "",
        )

    console.print(table)
