## Context

Narrio 当前处于“可运行原型”阶段：以文件系统为驱动，围绕 chunkify → stylify → render 的主流程产出中间 JSON 与图片结果。随着输入内容、prompt/style 版本与脚本数量增长，现有结构会把代码、静态资产与运行产物混在一起，难以协作与演进。

本次变更的依据是 [technical-design.md](file:///Users/mac/code/narrio/docs/technical-design.md) 的推荐目录结构与分层原则：明确区分 assets / domain / workflows / interfaces，并用 `.narrio/workbench` 承载实验运行与可回放产物。

## Goals / Non-Goals

**Goals:**
- 将仓库目录结构对齐 docs 推荐布局，建立可持续演进的职责边界（代码、资产、内容、导出、工作台、legacy）。
- 统一路径解析与资源发现策略：canonical 优先，legacy 兜底，逐步消除硬编码与重复逻辑。
- 在迁移期保持可运行：CLI 能在新结构下运行，并为旧结构提供过渡兼容策略与可回滚方案。

**Non-Goals:**
- 不在本次变更中引入数据库/队列/微服务等平台化基础设施。
- 不在本次变更中把所有 prompt/style 变成动态后台配置。
- 不要求一次性完成 domain/workflows/services/adapters 的完整拆分；本次以“结构对齐 + 入口稳定 + 可渐进迁移”为主。

## Decisions

1. 采用 docs 的 canonical 目录结构作为最终目标
   - 选择：引入 `src/`、`assets/`、`content/`、`exports/`、`legacy/`，并保留 `.narrio/` 作为本地工作台根目录
   - 原因：明确生命周期边界（可提交资产 vs 运行产物），降低协作成本，且与后续分层（domain/workflows/interfaces）对齐
   - 备选：维持当前根目录扁平结构，仅做命名清理
   - 未选原因：仍会混淆职责边界，迁移成本会在后续叠加放大

2. 路径解析采用“canonical 优先 + legacy 兜底”的迁移期策略
   - 选择：所有入口（CLI/脚本）统一通过一个路径解析模块发现 sources/prompts/styles，并按优先级搜索
   - 原因：在保持可运行的同时允许内容与资产逐步迁移，避免一次性大搬家导致不可控回归
   - 备选：一次性删除旧路径并强制所有使用者立即迁移
   - 未选原因：对原型迭代阶段过于激进，且会阻塞验证与回归定位

3. `src/` 布局采用渐进迁移
   - 选择：先保证新目录结构落地与路径解析稳定，再将现有 `narrio/` 包迁移至 `src/narrio/` 并更新打包配置
   - 原因：源码目录迁移会连带影响打包、导入路径与测试发现；分阶段可降低回归面
   - 备选：先做 `src/` 迁移，再做 assets/content/exports
   - 未选原因：先动 import 面会放大不确定性，降低对“结构对齐”本身的验证效率

## Risks / Trade-offs

- 目录迁移导致运行脚本/导入路径不一致 → 通过统一路径解析模块与兼容候选路径缓解，并提供回滚映射
- 历史产物与新结构共存导致混淆 → 明确 `.narrio/` 为运行工作台、`exports/` 为“可分享结果”，其余产物不承诺长期保留
- `src/` 迁移影响打包与 CLI 入口 → 分阶段完成，并在每阶段提供最小可运行验证（`python -m narrio --help`、dry-run、compileall、tests）

## Migration Plan

1. 引入 canonical 顶层目录并落地 assets/content/exports/legacy（不立即删除旧路径）
2. 抽出路径解析与资源发现模块：统一 sources/prompts/styles 的 resolve 与 list 行为
3. 迁移现有静态资产到 `assets/`（prompts、styles、reference images），并让 CLI 优先使用新路径
4. 迁移现有输入到 `content/`（article sources、podcast transcripts），并更新 CLI 的列表与解析逻辑
5. 明确输出落点：运行产物进入 `.narrio/workbench/...`；可分享结果写入 `exports/`
6. 将遗留脚本与原型目录收敛到 `legacy/`（保留可选兼容入口），逐步下线旧路径
7. 最后进行 `src/` 布局迁移与打包配置更新，保证 `narrio` CLI 入口不变

## Acceptance Checklist

**路径映射：**
- `process/prompt/*` → `assets/prompts/*`（`process/prompt` 保持为指向新目录的兼容入口）
- `process/styles/*` → `assets/styles/*`（`process/styles` 保持为指向新目录的兼容入口）
- `input/article/*` → `content/sources/article/*`（`input/article` 保持为指向新目录的兼容入口）
- `input/podcast/transcript/*` → `content/transcripts/*`（`input/podcast/transcript` 保持为指向新目录的兼容入口）
- `output/*` → `legacy/output/*`（`output` 作为兼容入口指向 legacy）
- `process/script/*` → `legacy/process/script/*`（`process/script` 作为兼容入口指向 legacy）
- `narrio/*` → `src/narrio/*`（根目录 `narrio` 作为兼容入口指向 `src/narrio`）

**可运行验证：**
- `python -m narrio --help` 可用
- `python -m narrio run --markdown "<existing>.md" --dry-run` 可用
- `python -m unittest discover -s tests` 可用

## Open Questions

- `assets/` 是否作为顶层目录，还是内聚到 `src/narrio/assets/`（docs 示例两者都出现，需要在实现阶段选定一种并保持一致）
- podcast 的“音频文件”与“转录文本”在 `content/` 下的最终分区规则（是否引入 `content/sources/podcast/` 与 `content/transcripts/` 的组合）
