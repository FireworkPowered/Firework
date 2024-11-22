from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING, Any, Iterable

from exceptiongroup import BaseExceptionGroup
from loguru import logger

from firework.globals import BOOTSTRAP_CONTEXT
from firework.util import TaskGroup, any_completed, cvar, unity

from .context import ServiceContext
from .service import resolve_services_dependency, validate_service_removal
from .status import Phase, Stage

if TYPE_CHECKING:
    from .service import Service


def _cancel_alive_tasks(loop: asyncio.AbstractEventLoop):
    to_cancel = asyncio.tasks.all_tasks(loop)
    if to_cancel:
        for tsk in to_cancel:
            tsk.cancel()
        loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

        for task in to_cancel:  # pragma: no cover
            # BELIEVE IN PSF
            if task.cancelled():
                continue
            if task.exception() is not None:
                logger.opt(exception=task.exception()).error(f"Unhandled exception when shutting down {task}:")


class UnhandledExit(Exception):
    pass


class Bootstrap:
    initial_services: dict[str, Service]
    services: dict[str, Service]
    contexts: dict[str, ServiceContext]
    daemon_tasks: dict[str, asyncio.Task]
    task_group: TaskGroup

    def __init__(self) -> None:
        self.initial_services = {}
        self.services = {}
        self.contexts = {}
        self.daemon_tasks = {}
        self.task_group = TaskGroup()

    @staticmethod
    def current():
        return BOOTSTRAP_CONTEXT.get()

    @property
    def running(self):
        return self.task_group.main is not None and not self.task_group.main.done()

    def get_service(self, service_or_id: type[Service] | str) -> Service:
        if isinstance(service_or_id, type):
            service_or_id = service_or_id.id

        return self.services[service_or_id]

    def get_context(self, service_or_id: type[Service] | str) -> ServiceContext:
        if isinstance(service_or_id, type):
            service_or_id = service_or_id.id

        return self.contexts[service_or_id]

    def add_initial_services(self, *services: Service):
        for service in services:
            self.initial_services[service.id] = service

    def remove_initial_services(self, *services: type[Service]):
        for service in services:
            self.initial_services.pop(service.id)

    async def start_lifespan(
        self, services: Iterable[Service], *, rollback: bool = False, failed_record: list[asyncio.Task] | None = None
    ):
        failed = await self._handle_stage_prepare(services)

        if failed_record is not None and failed is not None:
            done, curr = failed

            failed_record.extend([i for i in curr if i.done()])

            if rollback:
                self.task_group.drop(done)

                for i in done:
                    self.contexts[i.get_name()].dispatch_online()

                for i in curr:
                    if not i.done():
                        self.contexts[i.get_name()].dispatch_online()

                await self._handle_stage_cleanup([self.services[i.get_name()] for i in curr if not i.done()])
                await self._handle_stage_cleanup([self.services[i.get_name()] for i in done])

                def _dummy_online():
                    async def _dummy_offline(exit: bool = True):
                        pass

                    return _dummy_offline

                return _dummy_online

        def _online():
            for service in services:
                self.contexts[service.id].dispatch_online()

            async def _offline(exit: bool = True):
                failed_offline = await self._handle_stage_cleanup(services, trigger_exit=exit)

                if failed_record is not None and failed_offline is not None:
                    failed_record.extend(failed_offline)

            return _offline

        return _online

    async def _service_daemon(self, service: Service, context: ServiceContext):
        await service.launch(context)
        context.exit_complete()

    async def _handle_stage_prepare(self, services: Iterable[Service]):
        bind = {service.id: service for service in services}
        resolved = resolve_services_dependency(services, exclude=self.services.keys())
        previous_tasks: list[asyncio.Task] = []

        for layer in resolved:
            _services = {i: bind[i] for i in layer}
            _contexts = {i: ServiceContext(self) for i in layer}
            _daemons = {i: self._service_daemon(_services[i], _contexts[i]) for i in layer}

            self.services.update(_services)
            self.contexts.update(_contexts)

            daemon_tasks = {k: asyncio.create_task(v, name=k) for k, v in _daemons.items()}
            self.daemon_tasks.update(daemon_tasks)

            awaiting_daemon_exit = asyncio.create_task(any_completed(daemon_tasks.values()))
            awaiting_dispatch_ready = asyncio.create_task(
                unity([i.wait_for(Stage.PREPARE, Phase.WAITING) for i in _contexts.values()])
            )  # awaiting_prepare
            completed_task, _ = await any_completed([awaiting_daemon_exit, awaiting_dispatch_ready])

            if completed_task is awaiting_daemon_exit and not awaiting_dispatch_ready.done():
                return previous_tasks, daemon_tasks.values()

            for context in _contexts.values():
                context.dispatch_prepare()

            awaiting_prepare = asyncio.create_task(
                unity([i.wait_for(Stage.PREPARE, Phase.COMPLETED) for i in _contexts.values()]),  # awaiting_prepare
            )
            completed_task, _ = await any_completed([awaiting_prepare, awaiting_daemon_exit])

            if completed_task is awaiting_daemon_exit and not awaiting_prepare.done():
                return previous_tasks, daemon_tasks.values()

            layer_tasks = [asyncio.create_task(i.wait_for(Stage.ONLINE, Phase.COMPLETED)) for i in _contexts.values()]
            self.task_group.update(layer_tasks)
            previous_tasks.extend(layer_tasks)

    async def _handle_stage_cleanup(self, services: Iterable[Service], trigger_exit: bool = True):
        service_bind = {}
        for service in services:
            if service.id not in self.services:
                raise ValueError(f"Service {service.id} is not registered")
            service_bind[service.id] = service

        daemon_bind = {service.id: self.daemon_tasks[service.id] for service in services}

        validate_service_removal(self.services.values(), services)
        resolved = resolve_services_dependency(services, reverse=True, exclude=self.services.keys())

        for layer in resolved:
            _contexts = {i: self.contexts[i] for i in layer}
            daemon_tasks = [daemon_bind[i] for i in layer]

            if trigger_exit:
                self._sigexit_trig([service_bind[i] for i in layer])

            awaiting_daemon_exit = asyncio.create_task(any_completed(daemon_tasks))
            awaiting_dispatch_ready = unity([i.wait_for(Stage.CLEANUP, Phase.WAITING) for i in _contexts.values()])  # awaiting_prepare
            completed_task, _ = await any_completed([awaiting_daemon_exit, awaiting_dispatch_ready])

            if completed_task is awaiting_daemon_exit:
                unresolved = [task for task in daemon_tasks if task.done()]
                return unresolved

            for context in _contexts.values():
                context.dispatch_cleanup()

            awaiting_cleanup = asyncio.create_task(
                unity([i.wait_for(Stage.CLEANUP, Phase.COMPLETED) for i in _contexts.values()]),  # awaiting_prepare
            )
            completed_task, _ = await any_completed([awaiting_cleanup, awaiting_daemon_exit])
            await any_completed([awaiting_cleanup, awaiting_daemon_exit])  # update asyncio.Task state

            if completed_task is awaiting_daemon_exit and not awaiting_cleanup.done():
                completed_daemon = [task for task in daemon_tasks if task.done()]
                return completed_daemon

            await asyncio.gather(*[i.wait_for(Stage.EXIT, Phase.COMPLETED) for i in _contexts.values()])

            for target in layer:
                self.services.pop(target)
                self.contexts.pop(target)
                self.daemon_tasks.pop(target)

    async def launch(self):
        if not self.initial_services:
            raise ValueError("No services to launch.")

        with cvar(BOOTSTRAP_CONTEXT, self):
            failed = []

            online_dispatch = await self.start_lifespan(self.initial_services.values(), failed_record=failed, rollback=True)
            offline_callback = online_dispatch()

            try:
                if not failed:
                    logger.success("Service startup complete, Ctrl-C to exit application.", style="green bold")
                    await self.task_group.wait()
            finally:
                await offline_callback(False)

                if failed:
                    exceptions = [i.exception() or UnhandledExit() for i in failed]
                    raise BaseExceptionGroup("service cleanup failed", exceptions)

    def launch_blocking(
        self,
        *,
        loop: asyncio.AbstractEventLoop | None = None,
        stop_signal: Iterable[signal.Signals] = (signal.SIGINT,),
    ):
        import contextlib
        import threading

        loop = asyncio.new_event_loop()

        logger.info("Starting launart main task...", style="green bold")

        launch_task = loop.create_task(self.launch(), name="amnesia-launch")
        handled_signals: dict[signal.Signals, Any] = {}

        def signal_handler(x, y):
            return self._on_sys_signal(launch_task)

        if threading.current_thread() is threading.main_thread():  # pragma: worst case
            try:
                for sig in stop_signal:
                    handled_signals[sig] = signal.getsignal(sig)
                    signal.signal(sig, signal_handler)
            except ValueError:  # pragma: no cover
                # `signal.signal` may throw if `threading.main_thread` does
                # not support signals
                handled_signals.clear()

        loop.run_until_complete(launch_task)

        for sig, handler in handled_signals.items():
            if signal.getsignal(sig) is signal_handler:
                signal.signal(sig, handler)

        try:
            _cancel_alive_tasks(loop)
            loop.run_until_complete(loop.shutdown_asyncgens())
            with contextlib.suppress(RuntimeError, AttributeError):
                # LINK: https://docs.python.org/3.10/library/asyncio-eventloop.html#asyncio.loop.shutdown_default_executor
                loop.run_until_complete(loop.shutdown_default_executor())  # type: ignore
        finally:
            asyncio.set_event_loop(None)
            logger.success("asyncio shutdown complete.", style="green bold")

    def _sigexit_trig(self, services: Iterable[Service]):
        for service in services:
            self.contexts[service.id].exit()

    def _on_sys_signal(self, launch_task: asyncio.Task):
        self._sigexit_trig(self.services.values())

        if self.task_group is not None:
            self.task_group.stop()
            if self.task_group.main is not None:  # pragma: worst case
                self.task_group.main.cancel()

        if not launch_task.done():
            launch_task.cancel()
            # wakeup loop if it is blocked by select() with long timeout
            launch_task._loop.call_soon_threadsafe(lambda: None)
            logger.warning("Ctrl-C triggered by user.", style="dark_orange bold")
