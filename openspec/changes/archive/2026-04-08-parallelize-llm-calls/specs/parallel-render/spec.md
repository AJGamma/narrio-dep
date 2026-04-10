## ADDED Requirements

### Requirement: 并行渲染执行

系统应当在封面图生成后，并发生成其余页面图片，并发度为「剩余页数」和「上限 5」中的较小值。

#### Scenario: 默认最大并发执行
- **WHEN** 用户执行 render 阶段且未指定并发数
- **THEN** 系统使用 min(剩余页数，5) 个 worker 并发生成非封面页

#### Scenario: 自定义并发数上限
- **WHEN** 用户指定 `--render-workers 3`
- **THEN** 系统使用 min(剩余页数，3) 个 worker 并发生成非封面页

#### Scenario: 单页内容渲染
- **WHEN** Editorial 只包含 1 页（封面）
- **THEN** 系统串发生成该页，不启动并发

### Requirement: 错误隔离

单个页面生成失败不应阻塞其他页面的生成。

#### Scenario: 部分页面失败
- **WHEN** 某个页面生成失败（如 API 错误）
- **THEN** 其他页面继续执行，失败页记录错误信息

#### Scenario: 全部页面完成统计
- **WHEN** 所有页面生成完成（含失败）
- **THEN** 输出成功页数和失败页数统计

### Requirement: 并发进度显示

系统应当实时显示并发任务的执行进度。

#### Scenario: 任务开始显示
- **WHEN** 并行阶段开始
- **THEN** 显示"开始并行生成 X 页，worker 数=Y"

#### Scenario: 单页完成显示
- **WHEN** 单个页面生成完成
- **THEN** 显示"[X/N] 页 Y 完成，耗时 Zs"
