# Narrio 原型结构优化技术设计

## 1. 背景

当前 `Narrio-workflow` 已经具备可运行的原型能力：能够把文章或播客内容切分成结构化 chunk，再结合 style 生成 Editorial JSON，最后逐页生成图片。这个方向是成立的，说明产品价值和核心工作流都已经被初步验证。

但从工程结构上看，它仍然属于“脚本串联 + 文件系统驱动”的原型阶段：

- 输入、提示词、风格、脚本、输出全部混放在一个目录体系中
- 核心流程以 3 个脚本顺序执行，缺少统一编排层
- OpenRouter 调用、环境变量加载、路径解析、时间戳处理等逻辑存在重复
- 产物以文件名约定关联，缺少显式的数据契约和运行元数据
- 目前更适合单人调试，不适合多人协作、批量运行、回溯和演进

因此，这份设计文档的目标不是“重写成一个复杂平台”，而是在保留原型敏捷性的前提下，把 Narrio 演进为一个可持续扩展的内容生产引擎。

## 2. 设计目标

本次结构优化聚焦以下目标：

1. 保留当前原型能快速试错、方便调 prompt 的优点
2. 把“内容处理逻辑”和“文件组织方式”解耦
3. 把“流程步骤”升级为可编排、可追踪、可恢复的 pipeline
4. 支持开发者高频、并发地进行 prompt 迭代实验
5. 支持未来新增内容类型、风格体系、模型供应商和输出渠道
6. 为当前开发者 CLI 与后续 PWA 前端接入留下统一边界

非目标：

- 不在当前阶段直接建设复杂微服务
- 不在当前阶段引入数据库作为唯一事实来源
- 不强行把所有 prompt 和 style 变成动态后台配置

## 3. 当前原型的主要结构问题

### 3.1 目录按“操作习惯”组织，而不是按“职责边界”组织

当前目录能反映使用流程，但不能很好反映系统职责：

- `input/`、`output/` 是运行数据
- `process/prompt/`、`process/styles/` 是静态资产
- `process/script/` 是执行逻辑

这三类内容生命周期完全不同，却被放在一个平级工作区里。随着内容量、style 数量和脚本数量增长，会出现以下问题：

- 代码改动和内容产物耦合在一起
- 很难区分“可提交资产”和“运行时中间产物”
- 后续一旦引入测试、配置、SDK、服务接口，目录会迅速失控

### 3.2 流程耦合在文件命名约定上

当前流程依赖文件名和目录名完成上下游关联，例如：

- chunk 输出目录依赖 markdown 文件名
- editorial 输出依赖最近的 chunk 文件
- 图片生成依赖 `Editorial-<style>-<timestamp>.json` 里的 style

这种方式在原型期很高效，但一旦出现以下场景就容易失控：

- 同一篇内容并行跑多个实验
- 中途改 style 命名或输出路径
- 需要追踪某一轮生成到底使用了哪个 prompt、哪个模型、哪个 reference image

### 3.3 编排层缺失

目前三个脚本分别负责：

- 内容切块
- 风格化排版
- 图片生成

但系统里缺少统一的 workflow abstraction，因此缺少：

- 统一的 run id
- 步骤状态管理
- 失败重试策略的一致入口
- 批量任务的选择与过滤能力
- 单次运行的完整上下文记录

结果是：流程虽然存在，但系统并不知道“这是一条完整流程”。

### 3.4 领域逻辑与基础设施逻辑混杂

例如下面几类逻辑散落在多个脚本中：

- `.env` / `.env.local` 加载
- OpenRouter HTTP 调用
- JSON 提取与解析
- 路径标准化与命名清洗
- 时间戳解析

这会带来几个问题：

- 修改公共行为时需要多点同步
- 不同脚本容易出现不一致行为
- 难以替换模型供应商或抽离公共库

### 3.5 资产与数据契约没有版本化

Narrio 依赖多种关键资产：

- chunkify prompt
- stylify prompt
- image prompt
- RedSoul
- style.json
- reference image

这些资产本质上是“生产逻辑的一部分”，但当前缺少显式版本和兼容性声明。未来如果 prompt 或 style 结构变化，旧产物与新产物之间会缺少一致的解释方式。

### 3.6 缺少可观测性和回放能力

当前能看到 debug markdown 和结果文件，这是很好的原型能力，但仍不够：

- 看不到每一步耗时
- 看不到每一步实际模型参数
- 看不到失败原因的结构化记录
- 看不到某个输出究竟来自哪一版输入、哪一版 prompt、哪一版 style

这会直接限制后续质量调优和批量运营能力。

### 3.7 缺少面向 prompt 迭代的开发者工作台

当前系统能跑通主流程，但不适合高频 prompt 试验，尤其不适合下面这些真实开发动作：

- 快速选择输入内容、prompt 版本、style、模型组合
- 并发运行多个实验做横向比较
- 从 chunk 或 editorial 阶段开始重跑，而不是每次全链路重来
- 保留每一轮实验的中间 JSON、request、response 和日志
- 用开发者友好的交互式终端而不是一长串手写参数

这意味着当前结构更像“脚本执行器”，还不是“prompt 实验工作台”。

## 4. 设计原则

为了避免“过度工程化”，结构优化遵循以下原则：

### 4.1 先模块化，再平台化

先把脚本拆成稳定模块和明确边界，再考虑 API 服务、任务队列和控制台。不要在领域模型还未稳定之前直接做重平台。

### 4.2 先保留文件系统，再补充运行元数据

文件系统在当前阶段非常适合 Narrio，因为内容和图像天然就是文件资产。短期内不需要抛弃文件系统，而是要在文件系统之上增加 manifest 和 run metadata。

### 4.3 资产显式化

prompt、style、reference image 不是辅助材料，而是核心输入。它们应当有稳定目录、明确命名和版本语义。

### 4.4 Workflow 与 Step 分层

用户关心的是“生成一套图文内容”，系统内部才关心 chunk、editorial、render 等步骤。结构设计要同时支持：

- 业务视角的 workflow
- 工程视角的 step

### 4.5 让原型继续可手动操作

即使未来引入更强的编排层，也必须允许开发者：

- 单独执行某一步
- 复用旧的中间产物
- 手工替换某个 JSON 再继续后续流程

这对 Prompt Engineering 场景尤其重要。

### 4.6 开发者交互优先，但不锁死在终端

当前最急迫的使用者是开发者，因此第一阶段应优先建设开发者友好的 CLI，尤其是交互式终端体验，例如通过 `fzf` 做内容、prompt、style、阶段和历史 run 选择。

但这层交互只应存在于接口层，不能把业务逻辑写死在终端流程里。未来 PWA 接入时，应复用同一套 domain、services 和 workflows，只替换交互入口。

## 5. 目标架构

建议把 Narrio 演进为四层结构：

1. 资产层 Assets
2. 领域层 Domain
3. 编排层 Workflow
4. 接口层 Interfaces

### 5.1 资产层

负责存放静态输入资产：

- prompts
- styles
- reference images
- schema 定义
- 默认配置

这层的特点是：

- 可版本管理
- 可审查
- 不依赖具体运行实例

### 5.2 领域层

负责表达 Narrio 的核心概念：

- Source Content
- Chunk Set
- Editorial Plan
- Rendered Pages
- Style Package
- Workflow Run

这层不关心 CLI 和具体目录结构，而是定义：

- 数据对象
- 校验规则
- 状态转换
- 核心业务操作

### 5.3 编排层

负责把多个 step 串成完整 workflow：

- ingest
- chunkify
- stylify
- render
- publish

这层需要记录：

- run id
- step status
- step inputs
- step outputs
- retry 与 resume 信息

### 5.4 接口层

用于承接不同使用方式：

- 开发者交互式 CLI
- 批处理脚本
- 后续 Web API
- 后续 PWA / 管理后台

接口层只负责编排入口，不承载核心业务逻辑。

这里需要显式区分两类入口：

- 开发者入口
  - 面向 prompt 迭代
  - 强调交互效率、阶段重跑、实验可见性
  - 推荐通过 `fzf`、终端预览、快捷键和历史 run 选择实现
- 产品入口
  - 面向最终 PWA
  - 强调稳定性、任务状态、结果浏览和审核流
  - 未来通过 API 或应用层 facade 对接

## 6. 推荐目录结构

建议把仓库逐步演进为如下结构：

```text
narrio/
├── .narrio/
│   ├── workbench/
│   │   ├── article/
│   │   └── podcast/
│   └── cache/
├── docs/
│   └── technical-design.md
├── pyproject.toml
├── README.md
├── src/
│   └── narrio/
│       ├── cli/
│       │   ├── main.py
│       │   ├── interactive.py
│       │   └── prompt_lab.py
│       ├── domain/
│       │   ├── content.py
│       │   ├── chunk.py
│       │   ├── editorial.py
│       │   ├── render.py
│       │   └── run.py
│       ├── workflows/
│       │   ├── article_pipeline.py
│       │   ├── podcast_pipeline.py
│       │   ├── prompt_experiment_pipeline.py
│       │   └── steps/
│       │       ├── chunkify.py
│       │       ├── stylify.py
│       │       └── render_pages.py
│       ├── services/
│       │   ├── chunk_service.py
│       │   ├── editorial_service.py
│       │   ├── render_service.py
│       │   └── experiment_service.py
│       ├── adapters/
│       │   ├── llm/
│       │   │   ├── openrouter_text.py
│       │   │   └── openrouter_image.py
│       │   ├── asr/
│       │   │   └── volcengine_asr.py
│       │   └── storage/
│       │       ├── file_store.py
│       │       └── run_manifest_store.py
│       ├── assets/
│       │   ├── prompts/
│       │   ├── styles/
│       │   └── schemas/
│       ├── config/
│       │   ├── models.py
│       │   └── settings.py
│       └── utils/
│           ├── env.py
│           ├── paths.py
│           ├── json_io.py
│           ├── ids.py
│           └── time.py
├── content/
│   ├── sources/
│   │   ├── article/
│   │   └── podcast/
│   └── transcripts/
├── exports/
│   ├── article/
│   └── podcast/
├── tests/
│   ├── domain/
│   ├── workflows/
│   └── fixtures/
```

这个结构的核心变化是：

- `.narrio/` 是本地开发者工作台目录，必须加入 `.gitignore`
- `src/narrio` 存放代码
- `content/` 存放原始输入
- `.narrio/workbench/` 存放每次实验及其中间产物
- `exports/` 存放人工确认后需要保留或分享的结果
- `assets/` 存放 prompt、style、schema

如果暂时不想引入 `src/` 布局，也可以先做一个轻量版本：

```text
Narrio-workflow/
├── .narrio/
├── docs/
├── narrio/
├── assets/
├── content/
├── exports/
└── tests/
```

两种方案都成立，但建议最终过渡到标准 Python package 结构。

## 7. 核心模块拆分

### 7.1 domain

负责定义核心对象和约束，建议至少抽出以下实体：

- `SourceContent`
  - `id`
  - `content_type`
  - `title`
  - `source_path`
  - `normalized_text_path`
- `ChunkArtifact`
  - `source_id`
  - `schema_version`
  - `model`
  - `prompt_version`
  - `output_path`
- `EditorialArtifact`
  - `source_id`
  - `style_id`
  - `chunk_artifact_id`
  - `schema_version`
  - `output_path`
- `RenderArtifact`
  - `editorial_artifact_id`
  - `page`
  - `image_path`
- `WorkflowRun`
  - `run_id`
  - `workflow_type`
  - `status`
  - `created_at`
  - `inputs`
  - `artifacts`

这层的关键价值是让后续逻辑不必通过“猜文件名”理解系统状态。

### 7.2 services

负责单一步骤的核心业务行为：

- `ChunkService`
  - 读取内容
  - 选择 prompt
  - 请求文本模型
  - 校验 chunk schema
  - 产出 chunk artifact
- `EditorialService`
  - 读取 chunk
  - 合并 style、RedSoul、stylify prompt
  - 请求文本模型
  - 校验 editorial schema
  - 产出 editorial artifact
- `RenderService`
  - 读取 editorial pages
  - 解析参考图策略
  - 请求图像模型
  - 产出 page images

`services` 应该只关心业务输入输出，不直接绑定 CLI 参数。

### 7.3 adapters

负责对接外部系统：

- LLM 适配器
  - OpenRouter 文本
  - OpenRouter 图像
- ASR 适配器
  - 火山引擎语音转写
- 存储适配器
  - 文件系统读写
  - run manifest 读写

这样改造后，未来接入别的供应商时，不需要动 workflow 主体。

### 7.4 workflows

负责流程编排，建议至少定义两种 workflow：

- `ArticlePipeline`
- `PodcastPipeline`
- `PromptExperimentPipeline`

它们共享 step，但输入预处理不同：

- article 直接读 markdown
- podcast 可能包含音频转写步骤
- prompt experiment 关注组合实验、并发执行和阶段重跑

每个 workflow 只编排，不实现底层细节。

## 8. 数据组织方案

### 8.1 用 gitignored workbench 承载实验运行

当前 prompt 迭代的核心诉求不是“沉淀最终产物”，而是“快速做实验并保留完整过程”。因此开发期不建议把所有实验结果直接写入可提交目录，而是应该进入一个本地 gitignored 工作台目录，例如：

```text
.narrio/workbench/article/<combo-id>/
├── manifest.json
├── meta/
│   ├── selection.json
│   └── params.json
├── source/
│   └── normalized.md
├── runs/
│   ├── run-001/
│   ├── run-002/
│   └── run-003/
└── latest -> runs/run-003
```

其中：

- `combo-id` 表示一次输入组合的唯一标识
- 一个组合下可以有多次 run
- 每个 run 可以对应不同 prompt 改动、模型参数或重跑策略
- 所有目录必须加入 `.gitignore`

推荐 `combo-id` 由以下信息生成：

- source content
- content type
- style
- prompt 套件版本集合
- 可选模型配置摘要

如果 prompt 内容是开发者本地临时修改版，也可以直接基于内容 hash 生成组合标识。

### 8.2 单次 run 目录结构

对于每一次实际执行，建议目录结构为：

```text
.narrio/workbench/article/<combo-id>/runs/<run-id>/
├── manifest.json
├── source/
│   └── normalized.md
├── chunk/
│   ├── request.json
│   ├── response.json
│   └── chunk.json
├── editorial/
│   ├── request.md
│   ├── response.json
│   └── editorial.json
├── render/
│   ├── 0.png
│   ├── 1.png
│   └── 2.png
├── snapshots/
│   ├── chunk-input.txt
│   ├── editorial-input.md
│   └── render-input-page-0.json
└── logs/
    └── events.jsonl
```

这样做的价值：

- 每一个输入组合都有稳定的归档位置
- 同一组合下可以有多次 run
- 每次 run 都有完整上下文
- debug 文件和正式产物被收纳到统一实例中
- 后续 resume、diff、A/B test 都更容易

### 8.3 引入 manifest.json

每个 run 建议生成一个 `manifest.json`，至少包含：

```json
{
  "combo_id": "article-openai-3b2f4a91",
  "run_id": "run-20260408-001",
  "workflow_type": "article",
  "source": {
    "path": "content/sources/article/AI写作指南1.0：智力的容器大于智力本身.md",
    "content_hash": "..."
  },
  "resume": {
    "start_stage": "stylify",
    "reused_artifacts": [
      "chunk/chunk.json"
    ]
  },
  "assets": {
    "chunk_prompt": "assets/prompts/article_chunkify/v1.md",
    "stylify_prompt": "assets/prompts/stylify/v1.md",
    "redsoul_prompt": "assets/prompts/redsoul/v1.md",
    "style": "assets/styles/openai/v1/style.json",
    "reference_image": "assets/styles/openai/v1/ref.png"
  },
  "models": {
    "chunk_model": "google/gemini-3-flash-preview",
    "editorial_model": "google/gemini-3-flash-preview",
    "image_model": "google/gemini-3.1-flash-image-preview"
  },
  "steps": {
    "chunkify": { "status": "completed" },
    "stylify": { "status": "completed" },
    "render": { "status": "completed" }
  }
}
```

这个文件是结构优化中最值得优先落地的部分，因为它能在不引入数据库的前提下显著提升可追踪性。

### 8.4 中间产物全部保留，但职责明确

建议明确区分三类文件：

- 正式产物
  - `chunk.json`
  - `editorial.json`
  - `*.png`
- 过程快照
  - `request.json`
  - `response.json`
  - `request.md`
- 运行元数据
  - `manifest.json`
  - `events.jsonl`

这样既保留 prompt 调优能力，也让目录更可理解。

### 8.5 支持从指定阶段开始重跑

每次 run 都应该显式记录开始阶段和复用来源，至少支持：

- `from-source`
- `from-chunk`
- `from-editorial`

行为约定建议如下：

- 从 `from-source` 开始时，全链路执行
- 从 `from-chunk` 开始时，复用已有 `chunk.json`，重跑 stylify 和 render
- 从 `from-editorial` 开始时，复用已有 `editorial.json`，仅重跑 render
- 如果所需中间产物缺失或 schema 不兼容，应直接失败，不隐式回退

这项能力对 prompt 迭代非常关键，因为开发者通常会只改 stylify prompt 或 image prompt，不希望重复支付上游步骤的成本。

## 9. 资产管理方案

### 9.1 prompts 版本化

建议把 prompt 从“零散 markdown 文件”升级为“有语义版本的资产”：

```text
assets/prompts/
├── article_chunkify/
│   ├── v1.md
│   └── v2.md
├── podcast_chunkify/
│   └── v1.md
├── stylify/
│   └── v1.md
├── imagegen/
│   └── v1.md
└── redsoul/
    └── v1.md
```

优点：

- 某次运行明确依赖哪一版 prompt
- prompt 升级不会污染历史结果
- 后续可以做 prompt 对比实验

除了正式版本化 prompt 外，还应支持开发者实验态 prompt：

- 正式 prompt 存放在 `assets/prompts/...`
- 临时实验 prompt 可以从工作区文件读取
- run manifest 必须记录实验 prompt 的路径、内容 hash 和基线版本

这样既支持稳定资产管理，也不牺牲 prompt 微调效率。

### 9.2 styles 变成 style package

当前一个 style 目录里只有 `style.json` 和 `ref.*`。建议把 style 提升为完整资产包：

```text
assets/styles/openai/v1/
├── style.json
├── ref.png
├── tokens.json
├── notes.md
└── compatibility.json
```

推荐新增几个概念：

- `style.json`
  - 给模型看的版式规范
- `tokens.json`
  - 给工程系统用的可解析设计 token
- `compatibility.json`
  - 声明兼容的 schema version、内容类型、输出渠道
- `notes.md`
  - 记录人工风格说明

这样 style 就不只是 prompt 附件，而是明确的“设计系统单元”。

## 10. 配置设计

建议把配置分成三层：

### 10.1 全局配置

例如：

- 默认模型
- 默认超时
- 默认重试次数
- 默认路径

### 10.2 工作流配置

例如：

- article workflow 使用哪个 chunk prompt
- podcast workflow 是否先执行转录
- render 是否允许跳过已存在页面

### 10.3 运行时覆盖参数

例如：

- 本次运行指定另一个 style
- 本次运行覆盖 model
- 本次运行只生成部分页面
- 本次运行指定起始阶段
- 本次运行启用并发实验数
- 本次运行加载临时 prompt 文件

推荐原则：

- 代码里只保留最少默认值
- 业务默认值进入配置文件
- 实验性参数通过 CLI 显式覆盖

### 10.4 开发者实验配置

建议单独提供一组实验配置，描述 prompt 迭代时的运行策略，例如：

- 默认 workbench 根目录
- 并发 worker 数
- 是否保留全部 request/response
- 是否默认打开中间产物预览
- `fzf` 是否为首选交互器

如果本机缺少 `fzf`，CLI 可以回退到普通文本选择，但 `fzf` 应作为推荐开发依赖。

## 11. 开发者交互式 CLI 设计

为了满足 prompt 快速迭代，建议把 CLI 设计为“命令模式 + 交互模式”双轨并存。

### 11.1 命令模式

适合脚本化、自动化、CI 或批量调用，例如：

- `narrio run`
- `narrio resume`
- `narrio inspect`
- `narrio diff`
- `narrio export`

### 11.2 交互模式

适合开发者本地高频实验，推荐入口：

- `narrio lab`
- `narrio rerun`
- `narrio compare`

交互流程建议：

1. 通过 `fzf` 选择 content type
2. 通过 `fzf` 选择输入内容
3. 通过 `fzf` 选择 style
4. 通过 `fzf` 选择 prompt 基线或临时 prompt 文件
5. 选择起始阶段
6. 选择并发策略
7. 提交后显示 workbench 目录和最新中间产物路径

### 11.3 交互模式的核心原则

- 所有交互都只负责“收集参数”
- 参数收集后统一交给 application/workflow 层执行
- 终端中的友好体验不能污染核心业务代码
- 同一套执行逻辑应可被未来 PWA 直接复用

## 12. Prompt 实验 Pipeline 设计

建议把 prompt 迭代提升为一等能力，而不是零散命令组合。

### 12.1 PromptExperimentPipeline 的职责

它应负责：

- 生成 `combo-id` 和 `run-id`
- 建立 gitignored workbench 目录
- 记录输入选择和 prompt 快照
- 并发执行多个实验任务
- 保留全部中间产物
- 支持从某个阶段开始重跑
- 汇总结果供开发者比较

### 12.2 并发实验模型

建议支持两种并发模式：

- 同一输入，多 prompt 并发
- 同一 prompt，多输入并发

但单个 run 内部的 step 仍然保持顺序，以确保中间产物清晰可追踪。并发粒度应落在“实验任务级”，而不是“步骤内随机并发”。

### 12.3 对比与审查

每轮实验结束后，CLI 应至少能输出：

- workbench 目录路径
- 各 run 的状态
- 各 run 的 prompt 标识
- chunk / editorial / render 产物路径

后续可以扩展：

- editorial JSON diff
- 关键字段 diff
- 图片结果对照浏览

## 13. 可观测性设计

对于 Narrio 这种“生成式内容工作流”，可观测性不是附属品，而是核心能力。建议最少建设以下能力：

### 13.1 结构化事件日志

每一步写入 `events.jsonl`：

- step started
- request sent
- response received
- validation passed
- retry happened
- artifact persisted
- step failed

### 13.2 运行摘要

每个 run 输出摘要信息：

- 总耗时
- 每步耗时
- 输入 token 近似量
- 输出页数
- 失败页码

### 13.3 可回放输入

保留：

- 实际发给模型的 request
- 实际收到的原始 response
- 解析后 artifact

这能极大提高 prompt 调试效率。

对于 prompt 实验场景，还应额外记录：

- prompt 原文快照
- 选择来源
  - 交互式选择
  - 命令行参数
  - 批量配置
- 重跑起始阶段
- 复用的中间产物路径

## 14. 校验与 Schema 策略

建议给关键产物定义 schema version：

- chunk schema
- editorial schema
- run manifest schema

至少要保证：

1. 每次模型输出都经过结构校验
2. schema 不兼容升级时能明确报错
3. style package 能声明自己兼容哪些 editorial schema

如果当前不想引入额外库，也至少应在 domain 层写显式字段校验；后续可以再引入 Pydantic 或 JSON Schema。

## 15. 推荐的迁移路径

为了避免一次性重构风险，建议按 4 个阶段推进。

### 阶段 1：轻量收口

目标：不改变行为，只整理结构。

动作：

- 新增 `docs/`
- 新增 `assets/`，迁移 prompt 和 style
- 新增 `.narrio/workbench/`，作为本地实验输出根目录
- 抽出公共工具函数
  - env
  - path
  - openrouter client
  - json extraction

收益：

- 降低重复代码
- 让仓库结构开始可维护

### 阶段 2：模块化脚本

目标：把“脚本”变成“模块 + 薄 CLI”。

动作：

- 保留 CLI 入口
- 把 chunkify、stylify、render 提炼成 service
- 引入 `WorkflowRun` 和 `manifest.json`
- 所有输出按 `combo-id + run-id` 收口
- 初步支持 `from-chunk`、`from-editorial` 重跑

收益：

- 支持恢复运行
- 支持批量任务管理
- 支持更清晰的测试

### 阶段 3：工作流编排

目标：让系统显式理解 pipeline。

动作：

- 引入 workflow 层
- 定义 article/podcast pipeline
- 定义 `PromptExperimentPipeline`
- 支持 `run`, `resume`, `rerender`, `restylify`, `compare`
- 引入结构化事件日志
- 支持实验任务级并发

收益：

- 从脚本集合升级为工作流系统
- 后续接 Web/API 时复用能力更强

### 阶段 4：接口扩展

目标：为运营或产品化使用铺路。

动作：

- 增加 API 或 Web 控制台入口
- 增加批量任务页面
- 增加结果浏览和人工审核流
- 让 PWA 复用 workflow 与 experiment 查询能力

收益：

- Narrio 从个人原型进化到团队工具

## 16. 优先级建议

如果只做最值得投入的结构优化，我建议优先落地下面 6 件事：

1. 建立 `.narrio / docs / assets / exports / tests` 五类顶层目录
2. 抽出公共 OpenRouter client 与 env/path/json 工具
3. 引入 `combo-id + run-id + manifest.json` 作为实验事实记录
4. 用交互式 CLI 承接开发者 prompt 试验，优先集成 `fzf`
5. 支持 `from-chunk` 和 `from-editorial` 两类阶段重跑
6. 给 prompts 和 styles 增加正式版本与实验态快照语义

这是投入产出比最高的一组优化，既不会过重，也能明显提升系统可维护性。

## 17. 风险与权衡

### 17.1 不宜过早数据库化

当前阶段数据天然是文件型资产，如果太早引入数据库作为主存储，会增加大量维护成本，而且对图像和 prompt 调试帮助有限。

### 17.2 不宜过早拆成多个服务

Narrio 的核心瓶颈不在服务间调用，而在工作流建模、资产管理和运行可追踪性。因此应先把单体 workflow 做对。

### 17.3 不宜把 prompt 完全抽象成后台配置

在产品方向和 style 方法论尚未稳定前，prompt 仍然更适合跟随代码和资产一起版本管理。

### 17.4 不宜只保留最终结果而删除中间产物

对于 prompt 迭代场景，中间 JSON、request、response 和日志本身就是实验资产。如果只保留最终图片，会极大削弱调试和对比能力。

### 17.5 不宜把交互式终端直接等同于产品形态

`fzf` 交互终端非常适合开发者，但它只是开发者入口，不应主导领域模型和系统边界。最终产品仍应以 PWA 为主，终端与前端共享同一后端能力。

## 18. 结论

Narrio 当前已经不是“想法验证”阶段，而是“工作流成立，但工程结构还停留在原型”的阶段。最合适的下一步不是大规模平台化，而是把现有能力收敛成一个清晰的内容生成引擎：

- 代码进入 package 化结构
- 资产进入版本化管理
- 开发实验进入 gitignored workbench 化组织
- 步骤进入 workflow 编排
- 中间产物进入可追踪和可回放体系
- 开发者通过交互式 CLI 高效做 prompt 实验
- 最终产品通过 PWA 复用同一套执行与查询能力

如果按这个方向推进，Narrio 会保持现在的试验效率，同时获得后续扩展到多内容类型、多 style、多模型、多入口形态的能力。
