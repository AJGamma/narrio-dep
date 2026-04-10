## Why

当前 Narrio 工作流中所有大模型调用（chunkify、stylify、render）都是串行执行，导致总耗时等于各步骤耗时之和。特别是 render 阶段生成多张图片时，每张图都需要等待前一张完成才能开始，造成显著的时间浪费。通过并行化改造，可以将总延迟从"所有图片时间累加"降低到"封面图 + 一批图片并行时间"。

## What Changes

- **render 阶段并行化**：封面图生成后，其余页面图片并发执行（每页以封面图为参考）
- **chunkify 与 stylify 保持串行**：这两个阶段存在数据依赖，无法并行
- **新增并发配置选项**：`--render-workers` 参数控制并行生图 worker 数
- **错误处理优化**：支持部分页面失败后继续生成其他页面
- **进度显示增强**：实时显示并发任务的执行状态

## Capabilities

### New Capabilities

- `parallel-render`: 并行渲染能力，支持多页图片并发生成
- `concurrent-config`: 并发配置能力，支持通过 CLI 参数控制 worker 数量

### Modified Capabilities

无（现有 capability 的行为要求没有变化，只是实现细节优化）

## Impact

- **修改文件**：`src/narrio/render_service.py`、`src/narrio/experiment.py`
- **新增依赖**：需要 `concurrent.futures`（Python 标准库，无需额外安装）
- **CLI 变更**：新增 `--render-workers` 参数
- **兼容性**：完全向后兼容，默认行为与现有行为一致
