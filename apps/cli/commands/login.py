from __future__ import annotations

import time
import webbrowser

import typer
from auth import save_token
from client import make_client

_POLL_INTERVAL = 3
_MAX_POLLS = 100


def login():
    """Log in to Argus. Opens your browser to complete authentication."""
    client = make_client()
    resp = client.post("/api/v1/auth/cli/session")
    if resp.status_code != 200:
        typer.echo(f"Error: could not start login session ({resp.status_code})", err=True)
        raise typer.Exit(code=1)

    data = resp.json()
    session_id = data["session_id"]
    browser_url = data["browser_url"]

    typer.echo(f"Opening browser: {browser_url}")
    webbrowser.open(browser_url)
    typer.echo("Waiting for authentication...")

    for _ in range(_MAX_POLLS):
        time.sleep(_POLL_INTERVAL)
        poll = client.get(f"/api/v1/auth/cli/token/{session_id}")
        if poll.status_code == 200:
            token = poll.json()["token"]
            save_token(token)
            typer.echo("Logged in successfully.")
            return

    typer.echo("Login timed out. Please try again.", err=True)
    raise typer.Exit(code=1)
