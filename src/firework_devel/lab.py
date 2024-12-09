from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from typing_extensions import Annotated

from firework.cli.prompt import SelectPrompt


def main(lab: Annotated[str | None, typer.Argument()] = None):
    lab_folder = Path.cwd() / "zlab"

    if lab is None:
        available_labs = [f.stem[4:] for f in lab_folder.glob("lab_*.py")]

        try:
            lab = SelectPrompt("Choose a lab to run", choices=available_labs).prompt()
        except KeyboardInterrupt:
            typer.echo("Cancelled lab execution by user")
            return typer.Exit(1)

    target = Path.cwd() / "zlab" / f"lab_{lab}.py"
    if not target.exists():
        raise FileNotFoundError(f"Lab file {target} not found")

    typer.echo(f"Running lab {lab}")

    result = subprocess.run(  # noqa: S603
        [sys.executable, str(target)],
        check=False,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    return typer.Exit(result.returncode)


def via_typer():
    typer.run(main)
