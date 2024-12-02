from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Generic, TypeVar

from prompt_toolkit.application import Application
from prompt_toolkit.styles import Attrs, Style, StyleTransformation

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import Layout

DT = TypeVar("DT")
RT = TypeVar("RT")


class DisableColorTransformation(StyleTransformation):
    def __init__(self, no_ansi: bool = False):
        self.no_ansi = no_ansi

    def transform_attrs(self, attrs: Attrs) -> Attrs:
        if self.no_ansi:
            return Attrs("", "", False, False, False, False, False, False, False)
        return attrs


class BasePrompt(abc.ABC, Generic[RT]):
    @abc.abstractmethod
    def _build_layout(self) -> Layout:
        raise NotImplementedError

    @abc.abstractmethod
    def _build_style(self, style: Style) -> Style:
        raise NotImplementedError

    @abc.abstractmethod
    def _build_keybindings(self) -> KeyBindings:
        raise NotImplementedError

    def _build_application(self, no_ansi: bool, style: Style) -> Application:
        return Application(
            layout=self._build_layout(),
            style=self._build_style(style),
            style_transformation=DisableColorTransformation(no_ansi),
            key_bindings=self._build_keybindings(),
            mouse_support=True,
        )

    def prompt(
        self,
        no_ansi: bool = False,
        style: Style | None = None,
    ) -> RT:
        app = self._build_application(no_ansi=no_ansi, style=style or Style([]))
        return app.run()
