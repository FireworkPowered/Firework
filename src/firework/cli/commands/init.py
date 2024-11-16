import argparse
from pathlib import Path

from firework.util.importlib import pkg_resources

from ..base import Command
from ..core import CliCore
from ..exceptions import LumaUsageError


def plugin(core: CliCore):
    core.register_command(InitCommand)


class InitCommand(Command):
    name = "init"
    description = "Initialize a firework.toml"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--non-interactive", action="store_true", help="Run in non-interactive mode.")
        parser.add_argument("--force", action="store_true", help="Force initialization.")

    def handle(self, core: CliCore, options: argparse.Namespace) -> None:
        core.ui.echo("[primary]Initializing [req]firework.toml")

        interactive: bool = not options.non_interactive
        force: bool = options.force

        if not interactive:
            core.ui.echo("[warning]Running in non-interactive mode.")

        file = Path.cwd() / "firework.toml"
        if file.exists():
            if force:
                core.ui.echo("[warning]firework.toml already exists, overwriting.")
            else:
                raise LumaUsageError("firework.toml already exists.")

        file.touch()
        file.write_text(pkg_resources.read_text(__name__, "init_template.toml", "utf-8"))

        core.ui.echo("[success]firework.toml initialized.")

        core.ui.echo("[info]You can now edit the firework.toml file to suit your needs.")
        core.ui.echo("[info]For more information, visit [link]https://firework.majoium.com/docs/config")
        core.ui.echo("[info]To get started, run [req]firework run")
        core.ui.echo("[info]For help, run [req]firework --help")
