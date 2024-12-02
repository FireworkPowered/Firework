from __future__ import annotations

import json

from firework.cli.config import LumaConfig
from firework.config.schema_gen import SchemaGenerator
from firework.util.importlib import pkg_resources

FIREWORK_CLI_CONFIG_MOD = "firework.cli.config"


def main():
    schema = SchemaGenerator.from_dc(LumaConfig)
    with pkg_resources.path(FIREWORK_CLI_CONFIG_MOD, "schema.json") as f:
        f.write_text(json.dumps(schema, indent=4))
