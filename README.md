# Narrio

Narrio 是一个 AI 驱动的内容生成引擎，能够将文章或播客转录内容转换为结构化的图文内容。

## 项目概述

Narrio 的核心工作流分为三个阶段：

1. **Chunkify** - 将原始内容切分成结构化的 chunk
2. **Stylify** - 结合风格定义生成 Editorial JSON
3. **Render** - 逐页生成图片

## 功能特性

- **Lab 交互式模式** - 友好的 fzf 风格界面，显示文件修改时间，支持模糊搜索
- **ASR 转录** - 使用火山引擎将音频文件（mp3、wav等）自动转录为 markdown
- **端到端处理** - 一条命令从音频直接生成图片
- 支持文章和播客两种内容类型
- 基于 OpenRouter 接入多种大模型
- 支持风格化排版
- 支持从任意阶段恢复运行
- 支持批量并发实验
- 完整的运行追踪和中间产物保留

## 快速开始

详细运行指南请参考 [how-to-run.md](how-to-run.md)

```bash
# 安装依赖
pip install -e .

# 方式一：从 markdown 开始
python -m narrio run --markdown "你的文章.md"

# 方式二：从音频文件开始（播客）- 分步执行
export VOLCENGINE_API_KEY="your-api-key"
python -m narrio transcribe                    # 转录音频
python -m narrio run --content-type podcast --markdown "转录文件.md"

# 方式三：端到端（音频 → 图片）- 一条命令完成
python -m narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI
```

## 目录结构

```
narrio/
├── src/narrio/          # 核心代码
├── assets/              # 提示词和风格资产
├── content/             # 输入内容
│   ├── audio/          # 待转录的音频文件 (mp3, wav, etc.)
│   ├── sources/article/
│   └── transcripts/    # 转录后的 markdown
├── .narrio/workbench/   # 实验产物 (gitignored)
├── exports/             # 导出结果
└── docs/                # 设计文档
```
