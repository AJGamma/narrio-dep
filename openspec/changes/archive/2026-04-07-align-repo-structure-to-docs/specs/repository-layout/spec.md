## ADDED Requirements

### Requirement: Canonical repository layout
仓库 MUST 按 [technical-design.md](file:///Users/mac/code/narrio/docs/technical-design.md) 的推荐目录结构组织，并在根目录提供以下职责边界清晰的目录：

- `docs/`：设计与说明文档
- `src/`：Python 源码根目录（包含 `narrio` 包）
- `assets/`：静态资产（prompts、styles、schemas、reference images）
- `content/`：原始输入内容（sources/transcripts 等）
- `exports/`：人工确认后需要保留或分享的结果
- `legacy/`：迁移期遗留内容与兼容入口
- `.narrio/`：本地工作台（运行产物与缓存），并且 MUST 保持 gitignored

#### Scenario: Repository contains canonical top-level directories
- **WHEN** 开发者克隆仓库并按规范初始化
- **THEN** 以上目录在仓库根目录可见且含义一致

### Requirement: Canonical input discovery
系统 MUST 以 `content/` 为唯一“规范输入来源”，并将输入按内容类型分区：

- article：`content/sources/article/*.md`
- podcast transcript：`content/transcripts/*.md`

#### Scenario: List article sources from canonical content directory
- **WHEN** CLI 列举 `article` 可选输入
- **THEN** 返回的列表来自 `content/sources/article` 下的 markdown 文件

#### Scenario: List podcast transcripts from canonical content directory
- **WHEN** CLI 列举 `podcast` 可选输入
- **THEN** 返回的列表来自 `content/transcripts` 下的 markdown 文件

### Requirement: Canonical asset discovery
系统 MUST 以 `assets/` 为唯一“规范资产来源”，并至少支持：

- `assets/prompts/`：chunkify/stylify/redsoul/imagegen 等提示词
- `assets/styles/<style>/style.json`：style 包
- `assets/styles/<style>/ref.*`：reference image（可选）

#### Scenario: Resolve a style package from canonical assets directory
- **WHEN** 用户指定 `--style OpenAI`
- **THEN** 系统从 `assets/styles/OpenAI/style.json` 解析 style 文件

### Requirement: Migration compatibility for legacy paths
在迁移期内（直到移除 legacy 支持），系统 MUST 允许从 legacy 路径读取输入与资产，优先级低于 canonical 路径：

- legacy input：`input/`
- legacy assets：`process/prompt/`、`process/styles/`

#### Scenario: Legacy input is used when canonical content is missing
- **WHEN** `content/` 不存在或缺少目标文件，且 legacy `input/` 存在
- **THEN** 系统仍可解析输入并完成运行

#### Scenario: Canonical content takes precedence over legacy input
- **WHEN** canonical `content/` 与 legacy `input/` 同时存在且包含同名输入
- **THEN** 系统使用 canonical `content/` 中的文件
