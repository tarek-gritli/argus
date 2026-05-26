from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

import typer
from commands.login import login
from commands.review import review


def _version_callback(value: bool) -> None:
    if value:
        try:
            v = version("cli")
        except PackageNotFoundError:
            v = "dev"
        typer.echo(f"argus {v}")
        raise typer.Exit()


app = typer.Typer(name="argus", add_completion=False, no_args_is_help=True)
app.command()(login)
app.command()(review)


@app.callback()
def main(
    version: bool = typer.Option(  # noqa: ARG001
        None,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    pass


if __name__ == "__main__":
    app()
