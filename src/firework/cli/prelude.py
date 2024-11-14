from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from firework.cli.core import CliCore


def plugin(core: CliCore):
    def aiohttp_client():
        from firework.bootstrap.external.aiohttp import AiohttpClient

        return AiohttpClient()

    core.add_service_integrate("aiohttp.client", aiohttp_client)

    def asgi_server_uvicorn():
        from firework.bootstrap.external.asgi import UvicornASGIService

        return UvicornASGIService("127.0.0.1", 8080)  # TODO: config

    core.add_service_integrate("asgi.server.uvicorn", asgi_server_uvicorn)

    def memcache():
        from firework.bootstrap.external.memcache import MemcacheService

        return MemcacheService()

    core.add_service_integrate("memcache", memcache)

    # TODO: add more integrations
