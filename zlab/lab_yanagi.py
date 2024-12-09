from __future__ import annotations

from dataclasses import dataclass

from elaina_segment import Buffer

from firework.framework.command.core.model.snapshot import ProcessingState
from firework.framework.command.model import YanagiCommand, fragment, header_fragment, option


@dataclass
class TestCommand(YanagiCommand, keyword="test"):
    # header: str = header_fragment()

    name: str = fragment()
    age: str = fragment()

    with option("--from"):
        fr: str = header_fragment()
        src: str = fragment()

    with option("--to"):
        dst: str = fragment()


@dataclass
class Sub1Command(YanagiCommand, keyword="sub1"):
    name: str = fragment()


Sub1Command.register_to(TestCommand)

a = TestCommand.parse(Buffer(["test alice 20 --from src --to dst"]), state=ProcessingState.PREFIX)

print(a)

a = TestCommand.parse(Buffer(["test alice 20 --from src --to dst sub1 bob"]), state=ProcessingState.PREFIX)

print(a)
