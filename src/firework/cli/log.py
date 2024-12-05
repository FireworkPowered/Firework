import logging
import sys
import types
from datetime import UTC, datetime
from logging import LogRecord
from types import TracebackType
from typing import Any, Callable, Iterable, TypeAlias

from loguru import logger
from loguru._logger import Core
from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler
from rich.text import Text
from rich.theme import Theme

for lv in Core().levels.values():
    logging.addLevelName(lv.no, lv.name)


class _LoguruSinkLoggingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def highlight(style: str) -> dict[str, Callable[[Text], Text]]:
    """Add `style` to RichHandler's log text.

    Example:
    ```py
    logger.warning("Sth is happening!", **highlight("red bold"))
    ```
    """

    def highlighter(text: Text) -> Text:
        return Text(text.plain, style=style)

    return {"highlighter": highlighter}


class LoguruRichHandler(RichHandler):
    """
    Interpolate RichHandler in a better way

    Example:

    ```py
    logger.warning("Sth is happening!", style="red bold")
    logger.warning("Sth is happening!", **highlight("red bold"))
    logger.warning("Sth is happening!", alt="[red bold]Sth is happening![/red bold]")
    logger.warning("Sth is happening!", text=Text.from_markup("[red bold]Sth is happening![/red bold]"))
    ```
    """

    def render_message(self, record: LogRecord, message: str) -> "ConsoleRenderable":
        # alternative time log
        time_format = None if self.formatter is None else self.formatter.datefmt
        time_format = time_format or self._log_render.time_format
        log_time = datetime.fromtimestamp(record.created, tz=UTC)
        if callable(time_format):
            log_time_display = time_format(log_time)
        else:
            log_time_display = Text(log_time.strftime(time_format))
        if not (log_time_display == self._log_render._last_time and self._log_render.omit_repeated_times):
            self.console.print(log_time_display, style="log.time")
            self._log_render._last_time = log_time_display

        # add extra attrs to record
        extra: dict = getattr(record, "extra", {})
        if "rich" in extra:
            return extra["rich"]
        if "style" in extra:
            record.__dict__.update(highlight(extra["style"]))
        elif "highlighter" in extra:
            record.highlighter = extra["highlighter"]
        if "alt" in extra:
            message = extra["alt"]
            record.markup = True
        if "markup" in extra:
            record.markup = extra["markup"]
        if "text" in extra:
            record.highlighter = lambda _: extra["text"]
        return super().render_message(record, message)


class RichPlainHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        record.msg = Text.from_markup(record.getMessage()).plain
        super().emit(record)


ExceptionHook: TypeAlias = "Callable[[type[BaseException], BaseException, TracebackType | None], Any]"


def _loguru_exc_hook(typ: type[BaseException], val: BaseException, tb: TracebackType | None):
    logger.opt(exception=(typ, val, tb)).error("Exception:")


def install_richuru(
    rich_console: Console | None = None,
    exc_hook: ExceptionHook | None = _loguru_exc_hook,
    tb_ctx_lines: int = 3,
    tb_theme: str | None = None,
    tb_suppress: Iterable[str | types.ModuleType] = (),
    time_format: str | Callable[[datetime], Text] = "[%x %X]",
    keywords: list[str] | None = None,
    level: int | str = 20,
    *,
    rich_traceback: bool = True,
    rich_style_enabled: bool = True,
    logging_sink: bool = True,
    plain_fallback: bool = True,
) -> None:
    """Install Rich logging and Loguru exception hook"""

    if logging_sink:
        logging.basicConfig(handlers=[_LoguruSinkLoggingHandler()], level=0)

    if rich_style_enabled:
        logger.configure(
            handlers=[
                {
                    "sink": LoguruRichHandler(
                        console=rich_console
                        or Console(
                            theme=Theme(
                                {
                                    "logging.level.success": "green",
                                    "logging.level.trace": "bright_black",
                                }
                            )
                        ),
                        rich_tracebacks=rich_traceback,
                        tracebacks_show_locals=True,
                        tracebacks_suppress=tb_suppress,
                        tracebacks_extra_lines=tb_ctx_lines,
                        tracebacks_theme=tb_theme,
                        show_time=False,
                        log_time_format=time_format,
                        keywords=keywords,
                    ),
                    "format": (lambda _: "{message}") if rich_traceback else "{message}",
                    "level": level,
                }
            ]
        )
    elif plain_fallback:
        logger.configure(
            handlers=[
                {
                    "sink": RichPlainHandler(),
                    "format": "<lk>{time:YYYY-MM-DD HH:mm:ss}</lk> <lvl>{level:8}</lvl> | <m><u>{name}</u></m> <lvl>{message}</lvl>",
                    "level": level,
                }
            ]
        )

    if exc_hook is not None:
        sys.excepthook = exc_hook
