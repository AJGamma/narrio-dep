## Why

当前仓库结构同时承载了代码、静态资产（prompt/style）、输入内容与运行产物，职责边界不清晰，导致：难以协作、难以回溯一次运行的完整上下文、以及难以按 docs 的演进路径继续模块化与平台化。

## What Changes

- 将仓库目录结构对齐 [technical-design.md](file:///Users/mac/code/narrio/docs/technical-design.md) 的推荐布局：明确区分代码、资产、内容、导出物与本地工作台产物。
- 引入并固化“规范路径”与“运行时路径”的边界（例如 workbench 仍在 `.narrio/`，且保持 gitignored），统一路径解析入口，减少硬编码。
- 将遗留原型/脚本与当前可运行实现纳入迁移期的 `legacy/` 边界（仅保留兼容入口，逐步下线）。
- **BREAKING**：仓库根目录下 `input/ process/ output/ narrio/` 等路径将被迁移/重命名为 docs 定义的路径（通过兼容层或软链接提供过渡期支持，最终移除旧路径）。

## Capabilities

### New Capabilities
- `repository-layout`: 定义并约束 Narrio 的仓库目录结构、关键路径约定（assets/content/exports/.narrio/workbench/src）、以及迁移期兼容策略与可验证的约束。

### Modified Capabilities

## Impact

- 代码：路径解析与资源查找逻辑将集中化调整（例如 `narrio/legacy.py`、workbench、脚本导入与默认路径）。
- 资产与数据：prompt/style/reference image、source content、exports 目录需要迁移与重命名；历史产物需要兼容读取或迁移策略。
- 测试与 CI：需要新增/更新针对目录结构与路径解析的测试，避免未来回归。
