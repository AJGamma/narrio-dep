# 端到端：从音频到图片

本文档介绍如何使用 Narrio 的端到端功能，从音频文件直接生成图文内容，无需手动运行多个步骤。

## 工作流概览

```
音频文件 (mp3/wav/etc.)
    ↓
[narrio run --audio-file] ← 一个命令完成所有步骤
    ↓
ASR 转录 → Highlight 提取 → 图片生成
    ↓
最终图片输出
```

## 配置 ASR 凭证

### 方式一：使用 .narrio.yaml 文件（推荐）

编辑项目根目录的 `.narrio.yaml` 文件：

```yaml
# ASR API (Volcengine - for audio transcription)
asr_api:
  provider: "volcengine"
  app_id: "9759076940"
  app_key: "YkREQk1qa0xNbm1xZWx3WQ=="
  access_token: "NLeZrJOrqJ0BruA47WST-OD0uO8zw0mT"
  secret_key: "Y-S47__rekdacbQ_V1X8ucV8b2CTDhP7"
  resource_id: "auto"
  language: ""  # auto-detect
```

**注意**：`.narrio.yaml` 文件已经被 `.gitignore` 排除，不会被提交到 git 仓库。

### 方式二：使用环境变量

```bash
export VOLCENGINE_APP_ID="9759076940"
export VOLCENGINE_APP_KEY="YkREQk1qa0xNbm1xZWx3WQ=="
export VOLCENGINE_ACCESS_TOKEN="NLeZrJOrqJ0BruA47WST-OD0uO8zw0mT"
export VOLCENGINE_SECRET_KEY="Y-S47__rekdacbQ_V1X8ucV8b2CTDhP7"
```

### 方式三：命令行参数

```bash
narrio run \
  --audio-file your-podcast.mp3 \
  --asr-app-key "YkREQk1qa0xNbm1xZWx3WQ==" \
  --asr-access-token "NLeZrJOrqJ0BruA47WST-OD0uO8zw0mT"
```

## 基本用法

### 最简单的方式

```bash
# 1. 确保已配置好 .narrio.yaml（包含 LLM、图片和 ASR 配置）
# 2. 将音频文件放到 content/audio/
cp your-podcast.mp3 content/audio/

# 3. 一条命令完成从音频到图片的全流程
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI
```

这条命令会自动：
1. ✅ 使用 ASR 转录音频
2. ✅ 提取亮点语句（podcast 默认行为）
3. ✅ 跳过 chunkify（使用亮点作为内容）
4. ✅ 生成图片

### 指定音频文件路径

```bash
# 使用绝对路径
narrio run \
  --content-type podcast \
  --audio-file /path/to/your/podcast.mp3 \
  --style OpenAI

# 使用相对路径（相对于 content/audio/）
narrio run \
  --content-type podcast \
  --audio-file episode-42.mp3 \
  --style OpenAI
```

### 限制生成图片数量

```bash
# 只生成前 5 张图片
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI \
  --max-pages 5
```

### 指定 ASR 语言

```bash
# 明确指定中文
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI \
  --asr-language zh-CN

# 明确指定英文
narrio run \
  --content-type podcast \
  --audio-file english-podcast.mp3 \
  --style OpenAI \
  --asr-language en-US
```

## 高级选项

### 使用公网 URL（避免上传大文件）

```bash
# 如果你的音频文件已经在 CDN 上
narrio run \
  --content-type podcast \
  --audio-file podcast.mp3 \
  --style OpenAI \
  --asr-audio-source-mode public-url \
  --asr-public-base-url https://cdn.example.com/podcasts
```

### 控制 Highlight 行为

```bash
# 强制同时运行 highlight 和 chunkify（而不是只用 highlight）
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI \
  --extract-highlights true

# 跳过 highlight，只用 chunkify
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI \
  --extract-highlights false
```

### 使用不同的风格

```bash
# 使用 Anthropic 风格
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style Anthropic

# 使用自定义风格
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style MyCustomStyle
```

## 完整示例

### 示例 1：快速测试（5 张图片）

```bash
# 快速生成 5 张图片预览
narrio run \
  --content-type podcast \
  --audio-file content/audio/test-episode.mp3 \
  --style OpenAI \
  --max-pages 5 \
  --asr-language zh-CN
```

### 示例 2：完整流程（所有图片）

```bash
# 生成所有图片
narrio run \
  --content-type podcast \
  --audio-file /Users/mac/Podcasts/episode-42.mp3 \
  --style OpenAI \
  --asr-language zh-CN
```

### 示例 3：批量处理多个音频

```bash
# 使用 shell 循环批量处理
for audio in content/audio/*.mp3; do
  basename=$(basename "$audio" .mp3)
  echo "Processing: $basename"
  
  narrio run \
    --content-type podcast \
    --audio-file "$audio" \
    --style OpenAI \
    --max-pages 5
done
```

### 示例 4：使用 tune 生成多个风格

```bash
# 先转录音频
narrio transcribe --audio-input content/audio/episode.mp3

# 然后使用 tune 生成多个风格
narrio tune \
  --input content/transcripts/episode.md \
  --styles "OpenAI,Anthropic,Google"
```

## 输出目录结构

```
.narrio/workbench/podcast/<combo-id>/runs/<run-id>/
├── transcribe/              # ASR 转录结果
│   └── your-podcast.md
├── highlight/               # 提取的亮点
│   └── highlights.json
├── chunk/                   # Chunk 数据（如果运行了 chunkify）
│   └── chunk.json
├── editorial/               # Editorial JSON
│   └── editorial.json
├── render/                  # 生成的图片
│   ├── 1.png
│   ├── 2.png
│   └── ...
└── logs/                    # 日志文件
    └── events.jsonl
```

## 查看结果

```bash
# 查看最新运行的输出目录
ls -lah .narrio/workbench/podcast/*/latest/render/

# 使用 inspect 命令查看运行详情
narrio inspect .narrio/workbench/podcast/*/latest

# 导出到 exports/ 目录
narrio export .narrio/workbench/podcast/*/latest
```

## 配置优先级

ASR 凭证的加载顺序（从高到低）：

1. **命令行参数** - `--asr-api-key`, `--asr-app-key`, `--asr-access-token`
2. **.narrio.yaml 文件** - 项目根目录的配置文件
3. **环境变量** - `VOLCENGINE_API_KEY`, `VOLCENGINE_APP_KEY`, `VOLCENGINE_ACCESS_TOKEN`

建议：
- 开发环境：使用 `.narrio.yaml` 文件
- CI/CD 环境：使用环境变量
- 临时测试：使用命令行参数

## 故障排查

### 问题：ASR 认证失败

```bash
# 检查配置是否正确加载
python -c "
from src.narrio.config import load_config
config = load_config()
if config.asr_api:
    print('ASR configured:', config.asr_api.provider)
    print('App ID:', config.asr_api.app_id)
else:
    print('ASR not configured')
"
```

### 问题：找不到音频文件

```bash
# 检查音频文件路径
ls -lh content/audio/

# 或使用绝对路径
narrio run \
  --content-type podcast \
  --audio-file "$(pwd)/content/audio/your-file.mp3" \
  --style OpenAI
```

### 问题：转录很慢

尝试使用公网 URL 模式：

```bash
# 先手动上传音频到 CDN
# 然后使用 public-url 模式
narrio run \
  --content-type podcast \
  --audio-file your-file.mp3 \
  --style OpenAI \
  --asr-audio-source-mode public-url \
  --asr-public-base-url https://your-cdn.com/audio
```

### 问题：想要查看中间结果

```bash
# 分步运行，方便调试
# 第一步：只转录
narrio transcribe --audio-input your-file.mp3

# 第二步：查看转录结果
cat content/transcripts/your-file.md

# 第三步：生成图片
narrio run \
  --content-type podcast \
  --markdown your-file.md \
  --style OpenAI
```

## 性能优化

### 1. 使用 inline 模式（小文件）

```bash
# 对于 < 10MB 的音频文件
narrio run \
  --content-type podcast \
  --audio-file small-file.mp3 \
  --style OpenAI \
  --asr-audio-source-mode inline
```

### 2. 使用公网 URL（大文件）

```bash
# 对于 > 50MB 的音频文件
narrio run \
  --content-type podcast \
  --audio-file large-file.mp3 \
  --style OpenAI \
  --asr-audio-source-mode public-url \
  --asr-public-base-url https://your-cdn.com
```

### 3. 限制图片数量（快速迭代）

```bash
# 开发时只生成 3 张图片
narrio run \
  --content-type podcast \
  --audio-file test.mp3 \
  --style OpenAI \
  --max-pages 3
```

## 成本考虑

一次完整的运行涉及：
- **ASR 费用**：按音频时长计费（~¥0.x/小时）
- **LLM 费用**：Highlight 提取 + Editorial 生成
- **图片生成费用**：每张图片的生成成本

建议：
- 开发阶段使用 `--max-pages 3-5` 限制图片数量
- 使用免费或低成本的 LLM 模型（如 Gemini Flash）
- 批量处理时考虑并发限制

## 下一步

- 自定义风格：[docs/STYLES.md](./STYLES.md)
- 自定义提示词：[docs/PROMPTS.md](./PROMPTS.md)
- 完整 ASR 文档：[docs/ASR-WORKFLOW.md](./ASR-WORKFLOW.md)
- 命令速查表：[docs/TRANSCRIBE-QUICK-REFERENCE.md](./TRANSCRIBE-QUICK-REFERENCE.md)
