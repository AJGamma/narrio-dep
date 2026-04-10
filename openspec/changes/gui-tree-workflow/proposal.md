## Why

当前 Narrio 的测试/实验工作流主要依赖 CLI 的线性执行，这在“单一风格、单次运行”的开发者调试场景下足够高效，但无法覆盖“用户上传内容后，选择多个风格并行生成，并持续观察每个分支的执行状态与产物”的产品化使用方式。我们需要把工作流从线性链条升级为可视化的树状结构，使用户能实时看见每一步的进展，并在任意节点上触发重跑，从而显著降低多风格生成与质量调优的操作成本。

## What Changes

- 新增基于 Web GUI 的树状工作流工作台，支持上传文章内容、选择多个 style 并行创建分支运行，并在同一视图中展示整棵运行树
- 新增运行树的统一数据模型（run tree / node / edge / status / artifact refs），替代仅凭文件命名约定进行上下游关联的方式
- 新增实时状态更新通道（WebSocket 或等价机制），使每个 step 的状态/日志/产物路径能在 GUI 的树图中实时刷新
- 新增节点级操作：从某个节点边界重跑（例如从 chunk 之后重跑 stylify+render），并生成新的分支或新的 run 实例以保留历史可追溯性
- 复用既有 workbench 运行目录与 manifest/事件日志的理念，使 GUI 与 CLI 能共享同一套执行与追踪机制

## Capabilities

### New Capabilities
- `workflow-tree-gui`: 提供 Web GUI 的树状工作流可视化与交互操作（上传、选风格并发、实时刷新、节点重跑）
- `workflow-tree-api`: 提供运行树状态查询、事件流订阅与节点重跑的 API 契约，供 GUI（及未来 PWA）复用

### Modified Capabilities

## Impact

- 代码层面将新增一个 Web 服务入口与 GUI 界面层，并补齐运行树的数据结构与事件流
- 需要引入/固定 Web 服务相关依赖（例如 FastAPI/NiceGUI、WebSocket 支持与 ASGI server）
- 执行侧需要支持“同一 source 的多 style 分支并行”，并确保每个分支仍可独立追踪、可重跑、可复用中间产物
