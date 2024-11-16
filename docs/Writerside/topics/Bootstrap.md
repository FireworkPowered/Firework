# Bootstrap

这不是正式文档，不过我希望这足够详细以方便后来者。

## 介绍

Bootstrap，即 `firework.bootstrap`，是用于统一管理组件内部的生命周期，以及在此之上处理组件之间依赖关系的子系统。它通过将组件的生命周期简单的划分为 `prepare`, `online`, `cleanup` 三个阶段，并利用 `asyncio` 实现了并行高效简洁的介面。

## 服务

Bootstrap 的组件以服务（Service）的形式存在，服务的基类可以直接从 `firework.bootstrap` 导入。在派生时，需填写 `id` 静态字段并实现 `launch` 方法。

```py
from firework.bootstrap import Service, ServiceContext

class MyService(Service):
    id = 'my_service'

    async def launch(self, ctx: ServiceContext):
        ...
```

在 `launch` 方法中，你需要使用 `ServiceContext` 提供的三个生命周期方法。

```py
async def launch(self, ctx: ServiceContext):
    async with ctx.prepare():
        ...
        
    async with ctx.online():
        ...
        
    async with ctx.cleanup():
        ...
```

在完成这一切后，你可以通过 `firework.bootstrap` 提供的 `Bootstrap` 类来启动服务。

```py
from firework.bootstrap import Bootstrap

bs = Bootstrap()
bs.add_initial_services(MyService())
bs.launch_blocking()
```

## 依赖

在 `Service` 中声明 `dependencies` 字段，可以指定服务的依赖关系。

```py
class MyService(Service):
    id = 'my_service'
    dependencies = ['another_service']

    async def launch(self, ctx: ServiceContext):
        ...
```

在启动时，Bootstrap 会自动检查依赖关系并按照依赖关系的顺序并行启动并调度服务。如果依赖关系存在循环，Bootstrap 会抛出异常。

## 动态增减任务

Bootstrap 可以使用 `start_lifespan` 方法在运行时动态增减任务，这一特性可以用于实现热重载等功能。

```py
bs = Bootstrap()

async def some_task():
    online_dispatch = await bs.start_lifespan([MyService()])
    # start_lifespan 方法会等待服务完成 prepare 阶段，并返回一个回调函数 online_dispatch.
    
    # 调用 online_dispatch 回调以指示服务进入并开始 online 阶段。
    # 这会返回一个 cleanup_dispatch 回调，用于结束服务。
    cleanup_dispatch = online_dispatch()
   
    # 调用 cleanup_dispatch 回调以指示服务进入并开始 cleanup 阶段。
    await cleanup_dispatch()
```

## 处理异常

`start_lifespan` 方法允许你传入一个用于盛放失败任务的 list。

```py
bs = Bootstrap()

async def some_task():
    failed_services = []
    online_dispatch = await bs.start_lifespan(
        [MyService()],
        failed_record=failed_services,
    )
    
    # ...
    
    cleanup_dispatch = online_dispatch()
    
    # ...
    
    await cleanup_dispatch()
    
    if failed_services:
        # 处理失败的服务
        pass
```

如果你希望在 `prepare` 阶段的某个步骤失败时回滚其影响，向 `start_lifespan` 方法传入 `rollback=True`。

```py
bs = Bootstrap()

async def some_task():
    failed_services = []
    online_dispatch = await bs.start_lifespan(
        [MyService()],
        failed_record=failed_services,
        rollback=True,
    )
    
    # ...
    
    cleanup_dispatch = online_dispatch()
    
    # ...
    
    await cleanup_dispatch()
    
    if failed_services:
        # 处理失败的服务
        pass
```

## Initial Services

Bootstrap 提供了 `add_initial_services` 与 `remove_initial_services` 方法，用于指定在第一次调用 `launch_blocking` 时启动的服务。

```py
bs = Bootstrap()
bs.add_initial_services(service := MyService())
bs.remove_initial_services(service)
bs.add_initial_services(service)
bs.launch_blocking()
```

## 总结

Bootstrap 在 Firework 中主要随 `firework run` 启动，其他子系统只构造 Service 并将状态托管其上。

`firework run` 负责从 `firework.toml` 中读取配置，使用辅助函数构造服务实例并托管给 Bootstrap。
除此之外还负责初始化 `firework.config` 子系统，具体的详情请参考其他文档。
