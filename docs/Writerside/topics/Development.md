# Development Guideline

Firework 目前仍处于激进的更新与迭代阶段，本 Topic 及其子 Topic 会持续更新，以跟踪各个组件的进度，并反映最新的功能和改进。

此外，本 Topic 将讨论如何围绕目前的代码库进行开发，即开发规范、代码风格、测试、文档等。我们也会谈到代码库中的基础设施，如 Actions、`pre-commit`、测试、CI/CD 等。我们将尽可能地用最短的篇幅提及这些所有。

## 代码库理念

Firework 通常被视为*平行世界的 Graia Project*，与主世界的 Graia Project 有所不同的是，Firework 不鼓励将组件分开为多个仓库，如 [launart](https://github.com/GraiaProject/launart) 在 Firework 仓库中被集成为 `firework.bootstrap` 组件，并在 `firework.bootstrap.external` 中提供对各式组件的集成，如 uvicorn 等。后者在一定程度上取代了原先的 [Amnesia](https://github.com/GraiaProject/Amnesia)。在 [Avilla](https://github.com/GraiaProject/Avilla) 中，Avilla 使用了 [Mina](https://github.com/GreyElaina/Mina) 将模块分为多个包进行分发，而 Firework 则反其道而行之，鼓励一次性的装载所有组件。

Firework 的主仓库分发名为 `firework.spark` 的 PyPI 包，这个包将 Firework 整合和深度相互集成的工具链一次性完整的交付到用户手中。Firework 以此鼓励各个组件之间建立深入的集成，以此提升整体的开发效率。

## 代码风格

Firework 仓库使用 ruff 进行通用检查与格式化，这一步骤通过配置了的 `pre-commit` 进行。此外，Firework 仓库推行激进的类型注解（Type Annotation）策略，要求代码应尽可能的在使用 Pyright 的 `standard` 或 `basic` 检查模式下通过检查，如果实在无法用类型描述这部分的逻辑或认为不值得，可以使用 `# type: ignore` 或 `# noqa` 静默警告或错误。

## Commit Message 规范

Firework 采取部分 Google Angular 规范，要求提交中必须包含一个 Header 和一个 Body，Header 与 Angular 规范相同，Body 可以且常常被省略。Header 与 Body 之间用一个空行分隔。

Header 的格式为：

```
<type>(<scope>): <subject>
```

其中 `<type>` 为提交类型，可以为以下之一：

- `feat`: 新功能；
- `fix`: 修复问题；
- `docs`: 文档；
- `style`: 格式（不影响代码运行的变动）；
- `refactor`: 重构，对接口的更改；
- `chore`: 构建过程或辅助工具的变动；
- `test`: 测试；
- `ci`: GitHub Action 配置变动；
- `misc`: 其他。

`<scope>` 为提交的范围，建议附加，建议遵循或模仿以下模式：

- `bootstrap`: 对模块 `firework.bootstrap` 的更改；
- `bootstrap/external`: 对模块 `firework.bootstrap.external` 的更改；
- `config`: 对模块 `firework.config` 的更改；
- `cli`: 对模块 `firework.cli` 的更改；
- `utils`: 对模块 `firework.util` 的更改；
- `meta`: 对 `pyproject.toml`、`.gitignore`、`.pre-commit-config.yaml` 等配置文件的更改；
- `lab`: 新增或修改 Lab 脚本；
- `test`: 对测试的更改，建议用 `test/<scope>` 格式以描述对象为特定模块或范畴；
- `workflow`: 对 `.github/workflows` 的更改；

`<subject>` 为提交的简短描述，强烈建议使用主动语态，适当采取缩写，例如 `impl` 代替 `implement(s)` 等。

对 Body 没有要求，可以自由发挥。

## 克隆仓库后的第一步

Firework 仓库使用并依赖于 PDM 进行各式各种工作，请先通过 `pip`、`pipx` 或 `uv` 安装 PDM，然后在仓库根目录运行 `pdm install -d` 安装开发依赖。我们不建议启用 PDM 的 PEP 517 模式，这可能会对 Firework 依赖的 Entry Point 机制造成影响（未定义行为），但目前还未测试过这方面。

```sh
pdm install -d
```

我们强制使用 `pre-commit` 进行代码风格检查，因此请在克隆仓库后运行 `pre-commit install` 安装 `pre-commit` 钩子。如果未安装 `pre-commit`，请先安装 `pre-commit`。

```sh
pip install pre-commit
pre-commit install
```

如果你需要围绕 Firework 的可选依赖组（Optional Dependency Group）进行开发，可以使用 `pdm install -g <group>` 安装对应的依赖组。例如，如果你需要围绕 `firework.bootstrap.external.aiohttp`，可以使用以下命令安装 `aiohttp` 的依赖：

```sh
pdm install -d -G aiohttp
```

对 `uvicorn` 等如法炮制，你可以一次指定多个依赖组，只需要将其用逗号（`,`）分割开来。

```sh
pdm install -d -G aiohttp,uvicorn
```

## 测试 (Lab)

Firework 目前不进行也不鼓励任何形式的单元测试，而是通过一种 Lab 机制来编写并运行调试脚本。

Lab 脚本通常放在 `zlab` 文件夹中并以 `lab_` 为前缀，文件名形如 `lab_<script>.py`（如 `lab_bootstrap.py`）。一般不推荐在提交中包含 Lab 脚本，除非脚本本身完善到可以作为供他人参考的范本。

使用 `pdm run lab [script]` 运行 Lab 脚本，如果未指定 `script`，则会列出所有可用的 Lab 脚本并提示选择。

## 文档

Firework 仓库使用 JetBrains 提供的 Writerside 工具编写文档并构建静态网页，静态网页托管在 Azure Static Web Apps 上，你需要按照 JetBrains 的指示安装 Writerside，并将仓库中的 `docs` 文件夹打开为 Writerside 项目。

当你提出 Pull Request 时，我们配置的 GitHub Action 会自动构建文档并将其部署到 Azure Static Web Apps 上，你可以在 PR 中查看文档的构建状态。

## CI/CD

Firework 目前不采用 CI/CD 来检查代码或是运行测试，仅用于构建并托管文档。我们计划在未来引入 CI/CD 来检查代码风格、运行测试等。

