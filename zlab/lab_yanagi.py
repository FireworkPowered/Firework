from __future__ import annotations

from dataclasses import dataclass

from elaina_segment import Buffer

from firework.framework.command.core.debug import pretty_pattern
from firework.framework.command.core.model.snapshot import ProcessingState
from firework.framework.command.model import YanagiCommand, fragment, option


@dataclass
class TestCommand(YanagiCommand, keyword="test"):
    # header: str = header_fragment()

    name: str = fragment()
    age: str = fragment()

    with option("--from"):
        src: str = fragment()

    with option("--to"):
        dst: str = fragment()


patt = TestCommand.get_command_pattern()
print(pretty_pattern(patt))
print(TestCommand.__yanagi_mangled_names__)

a = TestCommand.parse(Buffer(["test alice 20 --from src --to dst"]), state=ProcessingState.HEADER)

print(a, a.__sistana_snapshot__)
