from __future__ import annotations

import asyncio
from contextlib import contextmanager

from firework.bootstrap import Bootstrap, Service, ServiceContext


@contextmanager
def _xx():
    try:
        yield
    except:  # noqa: E722
        import traceback

        traceback.print_exc()


async def reporter(id: str, context: ServiceContext):
    while not context.should_exit:
        print(f"[{id}] reporter is running, current: {context._status}")
        await asyncio.sleep(2)


class TestService1(Service):
    id = "test_service_1"

    async def launch(self, context: ServiceContext):
        # asyncio.create_task(reporter(self.id, context))

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

    @_xx()
    async def launch(self, context: ServiceContext):
        # asyncio.create_task(reporter(self.id, context))

        async with context.prepare():
            print(self.id, "prepare")
            # await asyncio.sleep(3)
            print(self.id, "prepare done")

        async with context.online():
            print(self.id, "online")
            # await asyncio.sleep(3)
            print("[test sideload] starting")
            # await context.bootstrap.update([TestService3()])
            # print("[test sideload] update called")
            # srv = context.bootstrap.get_service(TestService3)
            # context.bootstrap.get_context(TestService3).dispatch_online()
            # print(f"[test sideload] service obtained: {srv}")
            # await context.bootstrap.offline([srv])
            # print("[test sideload] offline called")

            # print("[test sideload] starting second phase")

            # print("[test sideload] starting")
            # await context.bootstrap.update([TestService3()])
            # print("[test sideload] update called")
            # srv = context.bootstrap.get_service(TestService3)
            # context.bootstrap.get_context(TestService3).dispatch_online()
            # print(f"[test sideload] service obtained: {srv}")
            # await context.bootstrap.offline([srv])
            # print("[test sideload] offline called")

            ## using Bootstrap.lifespan

            print("[test sideload/lifespan] starting")
            online_callback = await context.bootstrap.start_lifespan([TestService3()])
            print("[test sideload/lifespan] lifespan called:", online_callback)
            offline_callback = online_callback()
            print("[test sideload/lifespan] online called:", offline_callback)
            await offline_callback()
            print("[test sideload] completed")

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
bootstrap.add_initial_services(TestService1(), TestService2())
bootstrap.launch_blocking()
