## Why

当前基于 CLI 的测试交互过于繁琐：每次只能运行一个变体，运行时中间过程不可见，导致调优效率低下。本改动引入一个基于 tmux/kitty 的多变体并行运行管线，实现“一次启动、多 pane 并行、实时可见、统一汇总”。

## What Changes

- **新增**：一个 CLI 脚本（`narrio tune` 或 `scripts/tune.sh`），支持交互式输入文件路径和多个风格
- **新增**：tmux 多 pane 布局，每个 pane 运行一个风格变体
- **新增**：独立汇总窗口，实时聚合各变体输出
- **新增**：运行结束后自动用 `kitten icat` 展示结果图，若无 kitten 则降级为 Python PIL 展示
- **新增**：支持通过 tmuxifier 预设布局快速恢复测试环境

## Capabilities

### New Capabilities
- `multi-variant-tuner`: 多变体并行运行管线，包括 tmux 窗口管理、pane 分发、输出汇总、结果展示
- `kitty-image-display`: kitty 终端图片展示能力，含 kitten icat 集成与 Python 降级方案

### Modified Capabilities
- `developer-interactive-cli`: 扩展 CLI 以支持多变体批处理模式（非交互式参数传递），保持现有单变体交互模式不变

## Impact

- **依赖项**：需要 `tmux`、可选 `tmuxifier`、可选 `kitty`（含 kittens）
- **代码影响**：新增 `src/narrio/tune.py` 或 `scripts/tune.sh`，可能扩展现有 CLI 入口
- **配置影响**：可能需要 `.tmuxinator/` 或 `.config/tmuxifier/` 配置文件
- **兼容性**：不影响现有单变体 CLI 命令，纯新增能力
