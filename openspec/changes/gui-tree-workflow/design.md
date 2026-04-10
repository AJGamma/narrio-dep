## Context

Narrio 当前的执行路径以 CLI 为主，流程逻辑以线性步骤为中心（chunkify → stylify → render），并通过 workbench 目录、manifest 与中间产物来承载运行的可追踪性。随着“用户上传内容后可选择多个 style 并行生成”的产品化诉求出现，单次运行将从线性链条扩展为树状结构：同一个 source 在 chunkify 之后分叉为多个 style 分支，每个分支独立产出 editorial 与页面渲染结果。与此同时，用户需要在可视化界面里实时观察每个节点的状态变化，并能在任意节点发起“从该节点边界重跑”的操作。

本变更目标是在不引入数据库与复杂分布式编排的前提下，基于现有 workbench/manifest 思路补齐：

- 运行树的数据模型与 API 契约
- 实时更新机制（事件流到 GUI）
- 节点级重跑与分支生成策略

## Goals / Non-Goals

**Goals:**
- 提供一个 Web GUI，支持上传文章内容后选择多个 style 并行生成，并以树状图可视化展示整棵运行树
- 每个节点/步骤的状态更新能够实时反映到树图（运行中、成功、失败、产物路径、错误信息）
- 允许用户对树节点执行“从此处重跑”的操作，并以新分支/新 run 的形式记录，保留历史可追溯性
- GUI 与 CLI 共享同一套执行与追踪基础（workbench、manifest、事件日志），避免重复实现核心业务逻辑

**Non-Goals:**
- 不在本阶段引入数据库作为唯一事实来源
- 不在本阶段建设多租户、权限体系、团队协作与远程部署能力
- 不在本阶段实现复杂的图编辑（拖拽改编排、任意 DAG 编辑）；仅需展示与节点操作

## Decisions

### 1) 技术栈：Python Web GUI + ASGI 服务

选择以 Python 为主的实现路径：后端负责执行与事件流，前端以 Web UI 进行可视化与交互。

- 方案 A：FastAPI + React Flow（交互能力上限最高，但需要独立前端工程与构建链）
- 方案 B：NiceGUI + 图组件（开发效率高，主要逻辑保持在 Python；图可视化通过内嵌 Cytoscape.js 等成熟组件实现）

本变更优先选择方案 B（NiceGUI）作为默认落地路径，以满足“语言使用 Python”的约束并快速迭代交互；同时将运行树 API 契约独立出来，保证未来可切换到 React/PWA 而不重写执行逻辑。

### 2) 运行树模型：以 workbench 为事实来源，显式化 node/edge/status

以 workbench 目录与 manifest/事件日志作为事实来源，新增“运行树”视角的数据模型：

- RunTree：一棵树对应一次“用户提交”的顶层工作流（source + 多 style 分支）
- Node：对应一个可执行的边界（例如 source-normalize、chunkify、stylify(style=X)、render(style=X)）
- Edge：定义父子关系（chunkify → stylify(style=X) → render(style=X)）
- Status：queued/running/completed/failed/canceled 等
- Artifacts：每个节点关联其 request/response/产物路径（例如 chunk.json、editorial.json、png）

节点的幂等与重跑边界以阶段划分（from-source/from-chunk/from-editorial）为基础，GUI 仅触发“从某边界开始”的重跑，而不直接操纵底层业务步骤。

### 3) 实时更新：事件日志 + WebSocket 推送

执行侧在每个节点生命周期内写入结构化事件（started/request/response/validated/artifact_persisted/failed 等），GUI 通过订阅事件流获得实时更新：

- 事件落盘：workbench 下的 events.jsonl（与现有 append_event 机制对齐）
- 实时推送：WebSocket 订阅 run_tree_id 或 run_id，将新事件增量推送给前端

这样既能实时更新，又能在 GUI 刷新/重连后通过“回放 events + 读取 manifest”恢复当前状态。

### 4) 并发模型：分支级并行，节点内顺序

支持“同一 source，多 style 分支并行”。并发粒度保持在“分支 run”级（或 node 子树级），每个分支内部仍按阶段顺序执行，以保证中间产物清晰可追踪，并便于节点级重跑。

执行实现优先复用现有 `narrio/experiment.py` 中的并发执行模式（线程池/任务级并行），后续如需更强可靠性再引入队列化（RQ/Celery）。

## Risks / Trade-offs

- [长耗时任务导致 UI 断线] → 以事件落盘为准，UI 重连后可从 manifest/events 回放恢复状态
- [并发分支写入冲突] → 每个分支 run 使用独立目录与独立 manifest/events，避免共享写入；聚合层只做只读汇总
- [节点级重跑语义不清] → 将重跑入口限制为显式边界（from-source/from-chunk/from-editorial），并在 API 中强制校验所需中间产物存在且兼容
- [未来切换到独立前端成本] → 将 GUI 依赖隔离在界面层，运行树 API 与数据模型保持独立可复用
