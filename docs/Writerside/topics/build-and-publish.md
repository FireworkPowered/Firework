# 编译与发布流程

## 编译

由于目前 Firework 仅使用 Python 编写，我们只需要简单的打包即可。

```sh
pdm build
```

`pdm build` 会在 `dist` 目录下生成打包成品，可供分发。

## 发布

Firework 采用 PyPI 的 Trusted Publisher 流程发布 PyPI 包，其包名为 `firework-spark`，与 `pyproject.toml` 中的 `name` 字段一致。

我们采用 GitHub Actions 自动化发布流程，当一个新的 Release 被创建并发布时，GitHub Actions 会自动构建并发布 PyPI 包。

请在发布前按顺序确认以下事项：

- `pyproject.toml` 中的 `version` 字段已经被更新；
- `firework.cli.config` 中的 `schema.json` 已更新（[相关文档](CLI.md#regenerate-cli-schema)）。

当更新工作流文件 `.github/workflows/pypi-publish.yml`，或是使用 `git tag` 新增名为 `build/*` 的标记时，GitHub Actions 会自动触发构建流程。当且仅当 Release 会触发发布流程。
