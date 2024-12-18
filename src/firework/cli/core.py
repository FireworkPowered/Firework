r"""
 _____ _                             _
|  ___(_)_ __ _____      _____  _ __| | __
| |_  | | '__/ _ \ \ /\ / / _ \| '__| |/ /
|  _| | | | |  __/\ V  V / (_) | |  |   <
|_|   |_|_|  \___| \_/\_/ \___/|_|  |_|\_\
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import importlib_metadata as pkg_meta
from typing_extensions import Self

from . import term
from .base import Command, ErrorArgumentParser, LumaFormatter, project_root_option, python_option, verbose_option
from .config import LumaConfig, into_config
from .exceptions import LumaArgumentError, LumaError
from .hook import HookManager
from .util import load_from_string

if TYPE_CHECKING:
    from firework.bootstrap import Service


class CliCore:
    def __init__(self) -> None:
        self.parser: ErrorArgumentParser = ErrorArgumentParser(
            "firework",
            description=term.style(__doc__, style="primary"),  # type: ignore
            formatter_class=LumaFormatter,
        )
        self.subparsers = self.parser.add_subparsers(parser_class=argparse.ArgumentParser)
        self.ui: term.UI = term.UI()
        self.config: LumaConfig | None = None
        self.python = sys.executable
        self.version: str = pkg_meta.version("firework-spark") or "development"
        self.hooks: HookManager = HookManager(self.ui)
        self.component_handlers: dict[str, Callable[[Self, dict[str, Any]], None]] = {}
        self.service_integrates: dict[str, Callable[[CliCore], Service]] = {}
        self.called_components: set[str] = set()
        self._tweak_parser()
        self._load_plugins()

    def _tweak_parser(self):
        self.parser.add_argument(
            "-V",
            "--version",
            action="version",
            version="{}, version {}".format(
                term.style("Firework Spark (Luma)", style="bold"),
                term.style(self.version, style="success"),
            ),
            help="show the version and exit",
        )
        project_root_option.add_to_parser(self.parser)
        python_option.add_to_parser(self.parser)
        verbose_option.add_to_parser(self.parser)
        self.parser._positionals.title = "Commands"

    def _load_plugins(self):
        for plugin in pkg_meta.entry_points(group="firework.cli.plugin"):
            try:
                plugin.load()(self)
            except Exception as e:
                self.ui.echo(
                    f"Failed to load plugin {plugin.name}={plugin.value}: {e!r}",
                    style="error",
                    err=True,
                )

    def _load_luma_file(self, config_file: Path) -> None:
        from tomlkit.exceptions import ParseError

        if config_file.exists():
            try:
                self.config = into_config(config_file)
                # if (metadata_v := self.config.metadata.version) != "0.1":
                #     self.ui.echo(f"[error]Incompatible [req]firework.toml[/req] version: {metadata_v}")
                #     self.config = None
                #     return
            except ParseError as e:
                self.ui.echo(f"[req]firework.toml[/req] is invalid TOML file: {e!r}", err=True)
            except ValueError as e:  # JSON Schema error
                self.ui.echo("[req]firework.toml[/req] is not valid", err=True)
                if self.ui.verbosity and "firework.toml" in str(e):
                    for exc in e.args[1]:
                        self.ui.echo(f"[error]{exc!r}", err=True)
            except Exception as e:
                self.ui.echo(f"[error]Error during loading [req]firework.toml[/req]: {e!r}", err=True)

    def register_command(self, command: type[Command]) -> None:
        self.ui.echo(f"Registering command [info]{command.name}[/info]", verbosity=2)
        command.register_to(self.subparsers)

    def _reforge_interpreter_env(self, py_path: str | None):
        orig_py_path = py_path

        if py_path is None:
            self.ui.echo("[info]Guessing Python path from invoking subprocess...", verbosity=1)
            py_path = subprocess.run(  # noqa: S603
                ["python", "-X", "utf8", "-c", "import sys;print(sys.executable, end='')"],  # noqa: S607
                encoding="utf-8",
                stdout=subprocess.PIPE,
                check=False,
            ).stdout

        if self.python != py_path:
            self.ui.echo("[info]Regenerating [primary]Luma[/primary] process")
            venv_luma = subprocess.run(  # noqa: S603
                [
                    py_path,
                    "-c",
                    "\n".join(
                        [
                            "import site",
                            "import sys",
                            f"site.addsitepackages(set(sys.path), [{json.dumps(sys.prefix)}])",
                            "from firework.cli import main",
                            "main()",
                        ]
                    ),
                ]
                + sys.argv[1:]
                + (["--python-path", py_path] if orig_py_path is None else []),
                check=False,
            )
            sys.exit(venv_luma.returncode)

    def _load_components(self) -> None:
        for ep in pkg_meta.entry_points(group="firework.cli.components"):
            # NOTE: Here we assume EVERY component is CORRECTLY implemented.
            ep.load()(self)

    # def _call_component(self, component: Component) -> None:
    #     name, _, sub = component.endpoint.partition(":")
    #     try:
    #         handler = self.component_handlers[name]
    #     except KeyError as exc:
    #         msg = f"Component {name} does not exist!"
    #         raise LumaConfigError(msg) from exc
    #     args = {"__sub__": sub or None, **component.args}
    #     handler(self, args)
    #     self.called_components.union((name, component.endpoint))

    def _bootstrap_luma_file(self):
        if not self.config:
            return
        # for component in self.config.components:
        #     self._call_component(component)
        for hook in self.config.hooks:
            hook_fn = load_from_string(hook.endpoint)
            if not callable(hook_fn):
                self.ui.echo(f"[error][info]{hook.endpoint}[/info] is not callable, skipping", err=True)
                continue
            self.hooks.add_hook(hook.target, hook_fn)

    def add_service_integrate(self, entrypoint: str, integrate: Callable[[CliCore], Service]):
        self.service_integrates[entrypoint] = integrate

    def main(self, args: list[str] | None) -> None:
        args = args or sys.argv[1:]
        try:
            options = self.parser.parse_args(args)
        except LumaArgumentError as e:
            self.parser.error(str(e.__cause__))
        self.ui.set_verbosity(options.verbose)

        try:
            f = options.handler
        except AttributeError:
            self.parser.print_help(sys.stderr)
            sys.exit(1)

        path_str = options.path or os.getenv("FIREWORK_PROJECT_ROOT") or os.getenv("PROJECT_ROOT")
        if path_str:
            self.project_root = Path(path_str)
        else:
            self.project_root = Path.cwd()

        try:
            self._reforge_interpreter_env(options.python_path)
            self._load_luma_file(self.project_root / "firework.toml")
            self._load_components()
            self._bootstrap_luma_file()
            f(self, options)
        except Exception as exc:
            should_show_tb = not isinstance(exc, LumaError)
            if self.ui.verbosity > term.Verbosity.NORMAL and should_show_tb:
                import traceback

                traceback.print_exc()

                # self.ui.echo(Traceback(), err=True)
                sys.exit(1)
            self.ui.echo(rf"[error]\[{exc.__class__.__name__}][/]: {exc}", err=True)
            if should_show_tb:
                self.ui.echo("Add '-v' to see the detailed traceback", style="warning", err=True)
            sys.exit(1)


def main(args: list[str] | None = None) -> None:
    """The CLI entry function"""
    return CliCore().main(args)
