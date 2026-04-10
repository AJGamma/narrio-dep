## 1. 实验运行底座

- [x] 1.1 建立 `.narrio` gitignore 规则与基础 workbench 目录工具
- [x] 1.2 实现 `combo-id`、`run-id`、manifest 和事件日志的公共模型与读写逻辑
- [x] 1.3 定义 run 目录结构与阶段产物路径约定

## 2. Prompt 实验执行链路

- [x] 2.1 基于现有脚本封装 chunkify、stylify、render 的可复用步骤执行器
- [x] 2.2 实现 `from-source`、`from-chunk`、`from-editorial` 三种起始阶段的执行与校验
- [x] 2.3 实现实验任务级并发执行与批次结果汇总

## 3. 开发者 CLI

- [x] 3.1 实现命令式 CLI 入口，支持 run、resume、inspect、compare
- [x] 3.2 实现交互式 lab 入口，支持内容、style、prompt、阶段等参数选择
- [x] 3.3 为交互式选择集成 `fzf` 优先和普通终端回退逻辑

## 4. 验证与文档收口

- [x] 4.1 为新 CLI 和运行模型补充基础验证用例或可执行验证脚本
- [x] 4.2 更新任务状态并验证 workbench 输出路径与中间产物可见性
