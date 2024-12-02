from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.application import get_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.lexers import SimpleLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator

from .base import BasePrompt
from .util import BOOLEAN_STRING, str2bool

if TYPE_CHECKING:
    from prompt_toolkit.formatted_text import AnyFormattedText


class ConfirmPrompt(BasePrompt[bool]):
    """Simple Confirm Prompt.

    Style class guide:

    ```
    [?] Choose a choice and return? (Y/n)
    └┬┘ └──────────────┬──────────┘ └─┬─┘
    questionmark    question      annotation
    ```
    """

    def __init__(
        self,
        question: str,
        default_choice: bool | None = None,
        *,
        question_mark: str | None = None,
    ):
        self.question: str = question
        self.question_mark: str = "[?]" if question_mark is None else question_mark
        self.default_choice: bool | None = default_choice

    def _reset(self):
        self._answered: bool = False
        self._buffer: Buffer = Buffer(
            validator=Validator.from_callable(self._validate),
            name=DEFAULT_BUFFER,
            accept_handler=self._submit,
        )

    def _build_layout(self) -> Layout:
        self._reset()
        return Layout(
            HSplit(
                [
                    Window(
                        BufferControl(self._buffer, lexer=SimpleLexer("class:answer")),
                        dont_extend_height=True,
                        get_line_prefix=self._get_prompt,
                    )
                ]
            )
        )

    def _build_style(self, style: Style) -> Style:
        default = Style(
            [
                ("questionmark", "fg:#673AB7 bold"),
                ("question", "bold"),
                ("annotation", "fg:#7F8C8D"),
                ("answer", "fg:#FF9D00"),
            ]
        )
        return Style([*default.style_rules, *style.style_rules])

    def _build_keybindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("enter", eager=True)
        def enter(event: KeyPressEvent):  # noqa: ARG001
            self._buffer.validate_and_handle()

        @kb.add("c-c", eager=True)
        @kb.add("c-q", eager=True)
        def quit(event: KeyPressEvent):  # noqa: A001
            if self.default_choice is None:
                event.app.exit(exception=KeyboardInterrupt("Cannot exit without answering the prompt."))
            else:
                event.app.exit(result=self.default_choice)

        return kb

    def _get_prompt(self, line_number: int, wrap_count: int) -> AnyFormattedText:  # noqa: ARG002
        prompts: AnyFormattedText = []
        if self.question_mark:
            prompts.append(("class:questionmark", self.question_mark))
            prompts.append(("", " "))
        prompts.append(("class:question", self.question.strip()))
        prompts.append(("", " "))
        if not self._answered:
            if self.default_choice is None:
                prompts.append(("class:annotation", "(y/n)"))
            elif self.default_choice:
                prompts.append(("class:annotation", "(Y/n)"))
            else:
                prompts.append(("class:annotation", "(y/N)"))
            prompts.append(("", " "))
        return prompts

    def _validate(self, text: str) -> bool:
        return text.lower() in BOOLEAN_STRING if text else self.default_choice is not None

    def _submit(self, buffer: Buffer) -> bool:
        self._answered = True
        if input_text := buffer.document.text:
            get_app().exit(result=str2bool(input_text))
        else:
            buffer.insert_text("Yes" if self.default_choice else "No")
            get_app().exit(result=self.default_choice)
        return True
