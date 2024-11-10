from __future__ import annotations

import json

from firework.cli.config import LumaConfig
from firework.config.schema_gen import SchemaGenerator
from firework.util.importlib import pkg_resources


def main():
    schema = SchemaGenerator.from_dc(LumaConfig)  # type: ignore
    with pkg_resources.path(__name__, "schema.json") as f:
        f.write_text(json.dumps(schema, indent=4))
