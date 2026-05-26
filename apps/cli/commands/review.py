from __future__ import annotations

import json
import subprocess
import time
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

_POLL_INTERVALS = [0.5, 1, 2, 3, 5, 5, 5, 5, 5, 5]
_POLL_TIMEOUT = 120


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
    if resp.status_code != 202:
        typer.echo(f"Review failed ({resp.status_code}): {resp.text}", err=True)
        raise typer.Exit(code=1)

    data = resp.json()
    stream_url = data["stream_url"]
    status_url = data["status_url"]

    findings: list[dict] = []
    sse_ok = False
    event = ""

    try:
        with client.stream("GET", stream_url) as stream_resp:
            if stream_resp.status_code == 200:
                for line in stream_resp.iter_lines():
                    if not line:
                        continue
                    if line.startswith("event: "):
                        event = line[7:].strip()
                    elif line.startswith("data: "):
                        raw = line[6:].strip()
                        payload = json.loads(raw)
                        if event == "finding":
                            findings.append(payload)
                            _print_finding_live(payload)
                        elif event == "done":
                            sse_ok = True
                            break
                        elif event == "error":
                            typer.echo(f"Review error: {payload.get('message', 'unknown')}", err=True)
                            raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception:
        sse_ok = False

    if not sse_ok:
        findings = _poll_for_result(client, status_url)

    if not findings:
        typer.echo("No issues found.")
        return

    if sse_ok:
        typer.echo(f"\n{len(findings)} finding(s) found.")
    else:
        _print_findings(findings)


def _poll_for_result(client, status_url: str) -> list[dict]:
    typer.echo("Streaming unavailable, polling for results...")
    elapsed = 0.0
    intervals = list(_POLL_INTERVALS)
    while elapsed <= _POLL_TIMEOUT:
        interval = intervals.pop(0) if intervals else 5.0
        time.sleep(interval)
        elapsed += interval
        resp = client.get(status_url)
        if resp.status_code == 200:
            return resp.json().get("findings", [])
        if resp.status_code != 202:
            typer.echo(f"Polling error ({resp.status_code}): {resp.text}", err=True)
            raise typer.Exit(code=1)
    typer.echo("Review timed out after 120s.", err=True)
    raise typer.Exit(code=1)


def _get_diff(files: list[str] | None = None) -> str:
    cmd = ["git", "diff", "HEAD"]
    if files:
        cmd += ["--", *files]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as exc:
        typer.echo(f"Failed to compute git diff: {(exc.stderr or '').strip() or exc}", err=True)
        raise typer.Exit(code=1)
    except FileNotFoundError:
        typer.echo("`git` is not available on PATH.", err=True)
        raise typer.Exit(code=1)


def _print_finding_live(f: dict) -> None:
    sev = f.get("severity", "info").lower()
    color = _SEVERITY_COLOR.get(sev, "white")
    console.print(f"[{color}]{sev.upper()}[/{color}] [{f.get('file', '')}:{f.get('line_start', '')}] {f.get('title', '')} — {f.get('suggestion') or ''}")


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
