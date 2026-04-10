## Why

Narrio 当前已经验证了内容生成工作流本身可行，但还缺少一个面向开发者的高效实验环境，导致 prompt 调整需要反复手工拼接命令、重复跑完整链路、难以比较不同实验结果。现在需要优先补齐本地实验工作台能力，让开发者能够低成本、高并发地迭代 prompt，同时为未来 PWA 接入预留统一的执行与查询边界。

## What Changes

- 新增本地 gitignored prompt 实验工作台目录，用于按输入组合和运行实例保存中间产物、日志和元数据
- 新增统一的实验运行模型，支持 `combo-id`、`run-id`、manifest、事件日志和中间产物快照
- 将现有 chunkify、stylify、render 流程收敛为可复用步骤，支持从 `source`、`chunk`、`editorial` 阶段开始重跑
- 新增开发者 CLI 入口，支持命令式执行和交互式实验模式
- 在交互式模式中优先支持 `fzf` 驱动的选择体验，并在缺失时降级到普通终端输入
- 为未来 PWA 接入保留统一的 workflow/service 边界，避免把业务逻辑绑定在终端交互中

## Capabilities

### New Capabilities
- `prompt-experiment-workbench`: 提供本地实验目录、运行追踪、中间产物可见性和阶段重跑能力
- `developer-interactive-cli`: 提供面向开发者的命令式与交互式 CLI 入口，用于高效配置和执行 prompt 实验

### Modified Capabilities

## Impact

- 受影响代码主要位于后续新增的 CLI、workflow、service、storage 和工具层
- 需要引入本地 `.narrio/` 目录并加入 `.gitignore`
- 需要调整现有脚本的封装方式，使其从“直接脚本执行”演进为“可复用步骤 + 薄入口”
- 后续 PWA 可复用同一套执行和查询模型，减少重复实现
