from __future__ import annotations

import asyncio

from firework.bootstrap import Bootstrap, Service, ServiceContext

from contextlib import contextmanager

@contextmanager
def _xx():
    try:
        yield
    except:
        import traceback
        traceback.print_exc()

async def reporter(id: str, context: ServiceContext):
    while not context.should_exit:
        print(f"[{id}] reporter is running, current: {context._status}")
        await asyncio.sleep(2)

class TestService1(Service):
    id = "test_service_1"

    async def launch(self, context: ServiceContext):
        asyncio.create_task(reporter(self.id, context))

        async with context.prepare():
            print(self.id, "prepare")
            # await asyncio.sleep(3)
            print(self.id, "prepare done")

        async with context.online():
            print(self.id, "online")
            # await asyncio.sleep(3)
            print(self.id, "online done")

        async with context.cleanup():
            print(self.id, "cleanup")
            # await asyncio.sleep(3)
            print(self.id, "cleanup done")


class TestService2(Service):
    id = "test_service_2"

    async def launch(self, context: ServiceContext):
        asyncio.create_task(reporter(self.id, context))
    
        async with context.prepare():
            print(self.id, "prepare")
            # await asyncio.sleep(3)
            print(self.id, "prepare done")

        async with context.online():
            print(self.id, "online")
            # await asyncio.sleep(3)
            print(self.id, "online done")

        async with context.cleanup():
            print(self.id, "cleanup")
            # await asyncio.sleep(3)
            print(self.id, "cleanup done")

class TestService3(Service):
    id = "test_service_3"

    @property
    def dependencies(self) -> tuple[str, ...]:
        return ("test_service_2",)

    @_xx()
    async def launch(self, context: ServiceContext):
        asyncio.create_task(reporter(self.id, context))

        async with context.prepare():
            print(self.id, "prepare")
            # await asyncio.sleep(3)
            print(self.id, "prepare done")

        async with context.online():
            print(self.id, "online")
            # await asyncio.sleep(3)
            print(self.id, "online done")

        async with context.cleanup():
            print(self.id, "cleanup")
            # await asyncio.sleep(3)
            print(self.id, "cleanup done")


bootstrap = Bootstrap()

bootstrap.launch_blocking([
    TestService1(),
    TestService2(),
    TestService3(),
])
