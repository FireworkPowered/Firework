from __future__ import annotations

import asyncio
import functools
import logging
from typing import Callable, TypeVar

from loguru import logger

from firework.bootstrap import Service, ServiceContext
from firework.util import any_completed

try:
    from uvicorn import Config, Server
except ImportError:
    raise ImportError("dependency 'uvicorn' is required for asgi service")


MAX_QUEUE_SIZE = 10

T = TypeVar("T")
U = TypeVar("U")


async def _empty_asgi_handler(scope, receive, send):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
                return
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    await send(
        {
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-length", b"0")],
        }
    )
    await send({"type": "http.response.body"})


class _LoguruHandler(logging.Handler):
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


class _Server(Server):
    def install_signal_handlers(self) -> None:
        pass


class DispatcherMiddleware:
    def __init__(self, mounts: dict[str, Callable]) -> None:
        self.mounts = mounts

    async def __call__(self, scope, receive: Callable, send: Callable) -> None:
        if scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        else:
            for path, app in self.mounts.items():
                if scope["path"].startswith(path):
                    scope["path"] = scope["path"][len(path) :] or "/"
                    return await app(scope, receive, send)

            if scope["type"] == "http":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 404,
                        "headers": [(b"content-length", b"0")],
                    }
                )
                await send({"type": "http.response.body"})
            elif scope["type"] == "websocket":
                await send({"type": "websocket.close"})

    async def _handle_lifespan(self, scope, receive, send) -> None:
        self.app_queues = {path: asyncio.Queue(MAX_QUEUE_SIZE) for path in self.mounts}
        self.startup_complete = {path: False for path in self.mounts}
        self.shutdown_complete = {path: False for path in self.mounts}

        tasks = []
        try:
            for path, app in self.mounts.items():
                tasks.append(
                    asyncio.create_task(
                        app(
                            scope,
                            self.app_queues[path].get,
                            functools.partial(self.send, path, send),  # type: ignore
                        )
                    )
                )

            while True:
                message = await receive()
                for queue in self.app_queues.values():
                    await queue.put(message)
                if message["type"] == "lifespan.shutdown":
                    break
        finally:
            await asyncio.wait(tasks)

    async def send(self, path: str, send: Callable, message: dict) -> None:
        if message["type"] == "lifespan.startup.complete":
            self.startup_complete[path] = True
            if all(self.startup_complete.values()):
                await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown.complete":
            self.shutdown_complete[path] = True
            if all(self.shutdown_complete.values()):
                await send({"type": "lifespan.shutdown.complete"})


class UvicornASGIService(Service):
    id = "asgi.server.uvicorn"

    middleware: DispatcherMiddleware
    host: str
    port: int

    def __init__(self, host: str, port: int, mounts: dict[str, Callable] | None = None):
        self.host = host
        self.port = port
        self.middleware = DispatcherMiddleware(mounts or {"\0\0\0": _empty_asgi_handler})

    async def launch(self, context: ServiceContext) -> None:
        async with context.prepare():
            self.server = _Server(Config(self.middleware, host=self.host, port=self.port, factory=False))

            level = logging.getLevelName(20)  # default level for uvicorn
            logging.basicConfig(handlers=[_LoguruHandler()], level=level)
            PATCHES = ["uvicorn.error", "uvicorn.asgi", "uvicorn.access", ""]
            for name in PATCHES:
                target = logging.getLogger(name)
                target.handlers = [_LoguruHandler(level=level)]
                target.propagate = False

            serve_task = asyncio.create_task(self.server.serve())

        async with context.online():
            await any_completed([serve_task, context.wait_for_sigexit()])

        async with context.cleanup():
            logger.warning("try to shutdown uvicorn server...")
            self.server.should_exit = True
            await any_completed([serve_task, asyncio.sleep(5)])
            if not serve_task.done():
                logger.warning("timeout, force exit uvicorn server...")
