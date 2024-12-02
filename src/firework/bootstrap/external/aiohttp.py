from __future__ import annotations

from firework.bootstrap import Service, ServiceContext

try:
    from aiohttp import ClientSession, ClientTimeout
except ImportError as e:
    raise ImportError(
        "dependency 'aiohttp' is required for aiohttp client service\nplease install it or install 'graia-amnesia[aiohttp]'"
    ) from e


class AiohttpClient(Service):
    id = "aiohttp.client"

    def __init__(self, session: ClientSession | None = None):
        self._session = session

    @property
    def session(self) -> ClientSession:
        if self._session is None:
            raise ValueError("session not initialized")

        return self._session

    async def launch(self, context: ServiceContext):
        async with context.prepare():
            self._session = self._session or ClientSession(timeout=ClientTimeout(total=10))

        async with context.online():
            pass

        async with context.cleanup():
            await self._session.close()
