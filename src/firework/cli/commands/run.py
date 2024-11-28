from __future__ import annotations

import argparse
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from firework.bootstrap import Bootstrap
from firework.config.manager import ConfigManager
from firework.globals import CONFIG_MANAGER_CONTEXT
from firework.util._cvar import cvar

from ..base import Command
from ..config import LumaConfig
from ..core import CliCore
from ..exceptions import LumaConfigError
from ..term import UI
from ..util import ensure_config, load_from_string

if TYPE_CHECKING:
    from firework.bootstrap.service import Service


def plugin(core: CliCore):
    core.register_command(RunCommand)


@contextmanager
def handle_exc(msg: str, ui: UI):
    try:
        yield
    except Exception as e:
        ui.echo(f"[error]{msg}", err=True)
        raise LumaConfigError(e) from e


class RunCommand(Command):
    name = "run"
    description = "Run your bot."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "profile",
            nargs="?",
            default="default",
            help="The profile to run the application with. If not provided, the `default` profile will be used.",
        )

    @ensure_config
    def handle(self, core: CliCore, config: LumaConfig, options: argparse.Namespace) -> None:
        runtime_ctx: dict[str, Any] = {}

        # Set up runner core
        run_hook_target = core.hooks.targets.get("run")
        # Run configuration hooks
        # if config_target := core.hooks.targets.get("run_config"):
        #     config_target.warn_hooks(core.ui, pre=True, post=True)
        #     for hook_fn in config_target.core:
        #         hook_fn(core, runtime_ctx)

        if run_hook_target is not None:
            for pre_fn in run_hook_target.pre:
                pre_fn(core, runtime_ctx)

        config_manager = ConfigManager(config.config.sources)

        # collect services
        services: list[Service] = []

        if options.profile not in config.profile_services:
            raise LumaConfigError(f"Profile '{options.profile}' is not defined in the configuration.")

        for desc in config.profile_services[options.profile]:
            if desc.type == "entrypoint":
                factory = core.service_integrates.get(desc.entrypoint)
                if factory is None:
                    raise LumaConfigError(f"Service entrypoint {desc.entrypoint} is not registered!")

                services.append(factory(core))
            elif desc.type == "custom":
                services.append(load_from_string(desc.module)())
            else:
                ...

        if not services:
            core.ui.echo("[error]No services are configured, so nothing will happen.", err=True)
            return

        with cvar(CONFIG_MANAGER_CONTEXT, config_manager):
            bootstrap = Bootstrap()
            bootstrap.add_initial_services(*services)

            try:
                bootstrap.launch_blocking()
            finally:
                if run_hook_target is not None:
                    for post_fn in run_hook_target.post:
                        post_fn(core, runtime_ctx)
