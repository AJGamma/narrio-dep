# Narrio 运行指南

## 初始化项目

### 1. 克隆项目后安装依赖

```bash
cd narrio
pip install -e .
```

### 2. 配置 API 提供商

项目支持使用不同的提供商（如 OpenRouter、Zeabur 等兼容 OpenAI 格式的接口），并且支持为**文字生成**和**图片生成**分别配置不同的 API。

有两种配置方式：

**方式一：使用 .env 文件（推荐）**

在项目根目录创建或编辑 `.env` / `.env.local` 文件：

```bash
# 默认配置（兼容旧版，如果未设置特定 API 则会回退使用此配置）
OPENROUTER_API_KEY="sk-or-v1-your-api-key-here"
# 可选：如果你使用其他兼容 OpenAI 格式的服务作为默认
# OPENROUTER_BASE_URL="https://hnd1.aihub.zeabur.ai/v1/chat/completions"

# 文本生成专属配置（优先级高于 OPENROUTER 配置）
TEXT_API_KEY="sk-your-text-api-key"
TEXT_API_BASE_URL="https://hnd1.aihub.zeabur.ai/v1/chat/completions"

# 图片生成专属配置（优先级高于 OPENROUTER 配置）
IMAGE_API_KEY="sk-your-image-api-key"
IMAGE_API_BASE_URL="https://api.example.com/v1/chat/completions"
```

**方式二：命令行临时指定**

每次运行时通过参数传入：
- `--api-key`
- `--text-base-url`
- `--image-base-url`

### 3. 准备输入内容

有三种方式准备输入内容：

**方式一：直接使用 markdown 文件**

将你的 markdown 文件放到对应目录：
- 文章内容：`content/sources/article/`
- 播客转录：`content/transcripts/`

**方式二：从音频文件转录（分步）**

如果你有播客音频文件（mp3、wav 等），可以使用 ASR 转录功能：

```bash
# 1. 配置火山引擎 API 密钥（在 .narrio.yaml 或环境变量）
# 2. 将音频文件放到 content/audio/ 目录
cp your-podcast.mp3 content/audio/

# 3. 运行转录
narrio transcribe

# 4. 转录结果会保存到 content/transcripts/
```

**方式三：端到端（音频 → 图片）- 推荐**

直接从音频文件生成图片，一条命令完成：

```bash
# 确保已配置 .narrio.yaml（包含 ASR 凭证）
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI
```

详细说明请参考：
- ASR 分步流程：`content/audio/README.md`
- 端到端流程：`docs/END-TO-END-AUDIO.md`

### 4. 准备风格资产（可选）

在 `assets/styles/` 目录下创建风格目录，每个风格目录包含：

```
assets/styles/your-style/
├── style.json      # 风格定义
└── ref.png         # 参考图
```

---

## 命令详解

### run - 运行实验

执行一次完整的内容生成实验。

**用法：**

```bash
python -m narrio run --markdown <文件名> [选项]
```

**常用选项：**

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--content-type` | 内容类型：article/podcast | article |
| `--style` | 风格名称 | OpenAI |
| `--start-stage` | 起始阶段：from-source/from-chunk/from-editorial | from-source |
| `--chunk-model` | 覆盖 chunk 模型 | - |
| `--editorial-model` | 覆盖 editorial 模型 | - |
| `--image-model` | 覆盖图像模型 | - |
| `--api-key` | 覆盖默认 API Key | 环境变量 |
| `--text-base-url` | 覆盖文本 API 接口 | 环境变量 |
| `--image-base-url` | 覆盖图片 API 接口 | 环境变量 |
| `--dry-run` | 空跑不调用 API | false |
| `--batch-file` | JSON 批量任务文件 | - |
| `--max-workers` | 并发 worker 数 | 1 |
| `--extract-highlights` | 提取亮点句子（在 chunkify 之前） | false |
| `--highlight-model` | 亮点提取使用的模型 | 同 chunk-model |
| `--continue-on-error` | 亮点提取失败时继续流程 | false |

**示例：**

```bash
# 运行文章生成实验
python -m narrio run --markdown "请停下「计数器」思维.md"

# 指定风格和模型
python -m narrio run --markdown "AI 写作指南.md" --style "OpenAI" --chunk-model "google/gemini-3-flash-preview"

# 从 chunk 阶段恢复（复用已有 chunk）
python -m narrio run --markdown "文章.md" --start-stage from-chunk --reuse-from-run ".narrio/workbench/article/xxx/runs/run-xxx"

# 批量运行
python -m narrio run --batch-file tasks.json --max-workers 3

# 启用亮点提取（在 chunkify 之前提取 3-5 个亮点句子）
python -m narrio run --markdown "文章.md" --extract-highlights

# 指定亮点提取的模型
python -m narrio run --markdown "文章.md" --extract-highlights --highlight-model "anthropic/claude-3-sonnet"

# 亮点提取失败时不中断流程
python -m narrio run --markdown "文章.md" --extract-highlights --continue-on-error
```

---

### resume - 恢复运行

从历史运行的中间阶段继续执行。

**用法：**

```bash
python -m narrio resume --markdown <文件名> --reuse-from-run <历史运行目录> --start-stage <阶段>
```

**选项：**

| 选项 | 说明 |
|------|------|
| `--reuse-from-run` | 历史运行目录（必填） |
| `--start-stage` | 恢复阶段：from-chunk/from-editorial |

**示例：**

```bash
# 从 chunk 阶段恢复
python -m narrio resume --markdown "文章.md" --reuse-from-run ".narrio/workbench/article/combo-123/runs/run-456" --start-stage from-chunk

# 从 editorial 阶段恢复（只重新生成图片）
python -m narrio resume --markdown "文章.md" --reuse-from-run ".narrio/workbench/article/combo-123/runs/run-456" --start-stage from-editorial
```

---

### inspect - 检查运行状态

查看某次运行的详细状态和元数据。

**用法：**

```bash
python -m narrio inspect <运行目录>
```

**示例：**

```bash
# 查看运行状态
python -m narrio inspect ".narrio/workbench/article/combo-123/runs/run-456"

# 输出示例
{
  "combo_id": "article-openai-3b2f4a91",
  "run_id": "run-20260408-001",
  "status": "completed",
  "steps": {
    "highlight": {"status": "completed"},
    "chunkify": {"status": "completed"},
    "stylify": {"status": "completed"},
    "render": {"status": "completed"}
  },
  "assets": {
    "chunk_prompt": "assets/prompts/ArticleChunkify.md",
    "style": "OpenAI"
  }
}
```

---

### export - 导出结果

将运行结果导出到 exports 目录。

**用法：**

```bash
python -m narrio export <运行目录> [--export-root <导出根目录>]
```

**示例：**

```bash
# 导出到默认 exports/目录
python -m narrio export ".narrio/workbench/article/combo-123/runs/run-456"

# 导出到指定目录
python -m narrio export ".narrio/workbench/article/combo-123/runs/run-456" --export-root "./my-exports"
```

---

### extract-highlights - 提取亮点句子

从长文本中提取 3-5 个最引人注目的句子，用于预览或封面展示。

**用法：**

```bash
python -m narrio extract-highlights --markdown <文件名> [选项]
```

**选项：**

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `--content-type` | 内容类型：article/podcast | article |
| `--input-path` | 输入文件或目录路径 | 根据 content-type 自动选择 |
| `--markdown` | 指定单个 markdown 文件 | - |
| `--prompt-file` | 提示词文件路径 | assets/prompts/HighlightExtract.md |
| `--output-root` | 输出根目录 | 根据 content-type 自动选择 |
| `--model` | 使用的模型 | google/gemini-3.1-flash-image-preview |
| `--api-key` | API Key | 环境变量 |
| `--base-url` | API Base URL | 环境变量 |
| `--timeout` | 请求超时时间（秒） | 180 |
| `--min-word-count` | 最低字数要求 | 1000 |
| `--max-highlights` | 最多返回的亮点数量 | 5 |
| `--continue-on-error` | 错误时继续，不中断流程 | false |

**示例：**

```bash
# 提取文章的亮点句子
python -m narrio extract-highlights --markdown "深度长文.md"

# 提取播客转录稿的亮点
python -m narrio extract-highlights --content-type podcast --markdown "播客对话.md"

# 指定输出目录和模型
python -m narrio extract-highlights --markdown "文章.md" --output-root "./highlights-output" --model "anthropic/claude-3-sonnet"

# 只提取 3 个亮点
python -m narrio extract-highlights --markdown "文章.md" --max-highlights 3
```

**输出格式：**

```json
{
  "highlights": [
    {
      "text": "提取的句子原文",
      "score": 0.95,
      "rationale": "为什么这个句子吸引人",
      "position": {
        "sentence_index": 12,
        "total_sentences": 150
      }
    }
  ],
  "word_count": 5000,
  "skipped": false
}
```

---

### compare - 比较实验

比较同一组合下不同实验运行的结果。

**用法：**

```bash
python -m narrio compare --content-type <类型> --combo-id <组合 ID>
```

**示例：**

```bash
# 比较文章组合下的所有运行
python -m narrio compare --content-type article --combo-id "article-openai-3b2f4a91"

# 输出示例
[
  {
    "run_id": "run-20260408-001",
    "status": "completed",
    "prompt_label": "ArticleChunkify-stylify-v1",
    "run_dir": ".narrio/workbench/article/combo-123/runs/run-001"
  },
  {
    "run_id": "run-20260408-002",
    "status": "completed",
    "prompt_label": "ArticleChunkify-v2",
    "run_dir": ".narrio/workbench/article/combo-123/runs/run-002"
  }
]
```

---

### lab - 交互式实验室

进入交互式终端，通过问答方式选择实验参数。

**用法：**

```bash
python -m narrio lab [--api-key <key>] [--text-base-url <url>] [--image-base-url <url>] [--dry-run]
```

**示例：**

```bash
# 进入交互模式
python -m narrio lab

# 空跑模式（不调用 API）
python -m narrio lab --dry-run
```

**交互流程：**

1. 选择内容类型（article/podcast）
2. 选择输入文件
3. 选择风格
4. 选择起始阶段
5. 如非 from-source，输入历史运行目录
6. 可选：覆盖各阶段的 prompt 文件路径
7. 输入实验标签
8. 提交运行

---

## 常见问题

### Q: 如何查看可用的风格？

查看 `assets/styles/` 目录下的子目录名。

### Q: 如何查看可用的输入文件？

- 文章：`content/sources/article/`
- 播客：`content/transcripts/`

### Q: 运行失败后如何调试？

1. 使用 `inspect` 查看运行状态和错误信息
2. 检查运行目录下的 `events.jsonl` 日志
3. 查看各阶段的 `request.json` 和 `response.json`

### Q: 如何节省 API 成本？

- 使用 `--start-stage from-chunk` 或 `from-editorial` 跳过已完成阶段
- 使用 `--dry-run` 先验证流程
- 调整 `--max-workers` 控制并发数

### Q: 亮点提取功能如何使用？

亮点提取是可选功能，默认关闭。启用方式：
-  standalone 模式：`python -m narrio extract-highlights --markdown "文章.md"`
- 集成模式：`python -m narrio run --markdown "文章.md" --extract-highlights`

内容少于 1000 字时会自动跳过，提取失败不会中断流程（使用`--continue-on-error` 时）。

### Q: 亮点提取的输出在哪里？

提取的亮点保存在运行目录下的 `highlights-*.json` 文件中，包含：
- 亮点原文
- 参与度评分（0-1）
- 选择理由
- 在原文中的位置
