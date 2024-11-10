from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import noneprompt
import typer
from typing_extensions import Annotated


def main(lab: Annotated[str | None, typer.Argument()] = None):
    lab_folder = Path.cwd() / "zlab"

    if lab is None:
        available_labs = [f.stem[4:] for f in lab_folder.glob("lab_*.py")]

        try:
            result = noneprompt.ListPrompt[str](
                "Choose a lab to run",
                choices=[noneprompt.Choice(i, i) for i in available_labs],
            ).prompt()
        except noneprompt.CancelledError:
            typer.echo("Cancelled lab execution by user")
            return typer.Exit(1)

        lab = result.data

    target = Path.cwd() / "zlab" / f"lab_{lab}.py"
    if not target.exists():
        raise FileNotFoundError(f"Lab file {target} not found")

    typer.echo(f"Running lab {lab}")

    result = subprocess.run(
        [sys.executable, str(target)],
        check=True,
        stdin=sys.stdin,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    return typer.Exit(result.returncode)


def via_typer():
    typer.run(main)
