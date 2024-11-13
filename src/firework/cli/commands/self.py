import argparse

from ..base import Command
from ..core import CliCore


def plugin(core: CliCore):
    core.register_command(SelfCommand)


class SelfCommand(Command):
    name = "self"
    description = "Act with luma itself."

    def handle(self, core: CliCore, options: argparse.Namespace) -> None: ...
