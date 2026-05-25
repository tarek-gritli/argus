from __future__ import annotations

import typer
from commands.login import login
from commands.review import review

app = typer.Typer(name="argus", add_completion=False, no_args_is_help=True)
app.command()(login)
app.command()(review)

if __name__ == "__main__":
    app()
