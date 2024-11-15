from __future__ import annotations

from loguru import logger

from firework.bootstrap import Service, ServiceContext
from firework.config import bootstrap, save_all


class ConfigLoadSerice(Service):
    id = "firework.config"

    async def launch(self, context: ServiceContext):
        async with context.prepare():
            bootstrap()
            logger.info("config loaded")

        async with context.online():
            pass

        async with context.cleanup():
            save_all()
            logger.info("config saved")  # TODO: better log message
