import argparse
from pathlib import Path

from ..base import Command
from ..core import CliCore
from ..exceptions import LumaUsageError


def plugin(core: CliCore):
    core.register_command(InitCommand)


class InitCommand(Command):
    name = "init"
    description = "Initialize a firework.toml"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--non-interactive", default=False, help="Run in non-interactive mode.")

    def handle(self, core: CliCore, options: argparse.Namespace) -> None:
        core.ui.echo("[primary]Initializing [req]firework.toml")
        interactive: bool = not options.non_interactive
        if not interactive:
            core.ui.echo("[warning]Running in non-interactive mode.")
        file = Path.cwd() / "firework.toml"
        if file.exists():
            raise LumaUsageError("firework.toml already exists.")
