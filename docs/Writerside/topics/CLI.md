# CLI

Firework 的 CLI 部分修改自 [Luma](https://github.com/BlueGlassBlock/Luma)。
本文档着重于基于 Firework CLI 现有基础设施的开发，例如如何添加新的命令等。
由于设计高度借鉴了 PDM 的插件系统，因此你也可以参考 PDM 的[插件开发文档](https://pdm-project.org/zh-cn/latest/dev/write/)。

## 声明插件

Firework CLI 的插件通过 [Entry Point](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) 机制进行声明。

在你的 `pyproject.toml` 中如此声明插件：

```toml
[project.entry-points."firework.cli.plugin"]
your_plugin = "your_plugin:plugin"
```

其中 `your_plugin` 为插件的名称，`your_plugin:plugin` 为插件的入口点函数。
在完成修改后，你需要重新将你的项目以 editable 模式安装到你的 venv 环境中，如重新运行 `pdm install`。

确保你已经激活 venv 环境后，Firework CLI 将能够识别并在运行时自动装载你的插件。

```sh
firework --help
```

## 插件开发

入口点函数形如：

```py
from firework.cli.core import CliCore

def plugin(core: CliCore):
    ...
```

`CliCore` 是 Firework CLI 的核心类，你可以通过它来注册新的命令、子命令等。

## 添加子命令

接下来我们将为 Firework CLI 添加一个 `echo` 命令，该指令基本上与常规的 `echo` 指令类似，但我们希望在传入 `--red` 选项时将输出改为红色。

由于 Firework CLI 使用了 [Rich](https://github.com/Textualize/rich) 美化输出，我们将类似的使用 Rich 的 [Markup 语法](https://rich.readthedocs.io/en/latest/markup.html) 来实现红色输出。

在 `pyproject.toml` 中声明插件：

```toml
[project.entry-points."firework.cli.plugin"]
do_echo = "your_plugin:plugin"
```

在插件中添加如下代码：

```py
import argparse

from firework.cli.base import Command
from firework.cli.core import CliCore


class EchoCommand(Command):
    name = "echo"
    description = "Echo a message, with optional color."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("message", nargs="+", help="The message to echo.")
        parser.add_argument("--red", action="store_true", help="Print in red color.")

    def handle(self, core: CliCore, options: argparse.Namespace) -> None:
        message = " ".join(options.message)
        if options.red:
            message = f"[red]{message}[/red]"
        core.ui.echo(message)

def plugin(core: CliCore):
    core.register_command(EchoCommand)
```

运行 `pdm install` 将插件安装到虚拟环境中，然后你可以在 Firework CLI 中使用 `firework echo` 命令了。

```sh
firework echo hello world
```

```sh
firework echo hello world --red
```

由于 Firework CLI 是 `argparse` 的包装，在 `add_arguments` 方法中你可以使用 `argparse` 的 API 来为命令添加参数，并通过 `handle` 方法中传递的 `options` 参数来获取用户传入的参数。关于 argparse，请参考 [Python 文档](https://docs.python.org/3/library/argparse.html)。

## Firework 仓库中的插件

Firework 的代码库中已经包含了 `init`, `run` 等插件， 这些插件被声明在 `firework.cli.commands` 包中，可以参考这些插件的已有实现。

## `firework run` 指令

`firework run` 指令是 Firework CLI 的核心指令，它负责从 `firework.toml` 中读取配置，使用辅助函数构造服务实例并托管给 Bootstrap，并由后者展开后续任务。

该指令被视作启动 Firework 应用的唯一入口。

关于 `firework.toml`，请参考 [](Config.md) 文档。

如果需要调试应用，我们提供了 `__main__.py` 的实现，使得可以直接使用 `python -m firework.cli` 指令启动 Firework CLI。这里以 VSCode 为例，你可以在 `.vscode/launch.json` 中添加如下配置：

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Firework: Run",
            "type": "python",
            "request": "launch",
            "module": "firework.cli",
            "args": ["run"],
            "console": "integratedTerminal"
        },
        {
            "name": "Firework: Debug Run",
            "type": "debugpy",
            "request": "launch",
            "module": "firework.cli",
            "args": ["run"],
            "console": "integratedTerminal"
        }
    ]
}
```

如此配置后，你便可以在 VSCode 中使用其调试功能启动 Firework CLI 并运行 `firework run`。
