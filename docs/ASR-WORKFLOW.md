# ASR 转录工作流完整指南

本文档介绍如何使用 Narrio 的 ASR 功能，将播客音频文件转录为 markdown，并生成图文内容。

## 工作流概览

```
音频文件 (mp3) 
    ↓ [ASR 转录]
转录文本 (markdown)
    ↓ [highlight 提取]
亮点语句
    ↓ [图文生成]
最终图片
```

## 步骤 1：准备音频文件

将你的播客音频文件放到 `content/audio/` 目录：

```bash
# 创建目录（如果不存在）
mkdir -p content/audio

# 复制音频文件
cp ~/Downloads/my-podcast.mp3 content/audio/
```

支持的格式：
- `.mp3` - MP3 音频
- `.wav` - WAV 音频  
- `.m4a` - M4A 音频
- `.ogg` - OGG 音频
- `.flac` - FLAC 音频

## 步骤 2：配置火山引擎 API

### 获取 API 密钥

1. 访问 [火山引擎语音服务控制台](https://console.volcengine.com/speech/app)
2. 创建应用或使用现有应用
3. 获取 **API Key**（新版）或 **App Key + Access Token**（旧版）

### 设置环境变量

**方式一：使用 .env 文件（推荐）**

编辑项目根目录的 `.env` 文件：

```bash
# 新版 API Key（推荐）
VOLCENGINE_API_KEY="your-api-key-here"

# 或使用旧版认证
# VOLCENGINE_APP_KEY="your-app-key"
# VOLCENGINE_ACCESS_TOKEN="your-access-token"
```

**方式二：临时设置环境变量**

```bash
export VOLCENGINE_API_KEY="your-api-key-here"
```

**方式三：命令行参数**

```bash
narrio transcribe --api-key "your-api-key-here"
```

## 步骤 3：运行 ASR 转录

### 基本用法

```bash
# 转录 content/audio/ 目录下的所有音频文件
narrio transcribe

# 转录单个文件
narrio transcribe --audio-input content/audio/episode-1.mp3

# 转录指定目录
narrio transcribe --audio-input /path/to/audio/folder
```

### 指定语言

```bash
# 中文
narrio transcribe --language zh-CN

# 英文
narrio transcribe --language en-US

# 自动检测（默认）
narrio transcribe
```

### 高级选项

```bash
# 使用公网 URL（避免上传）
narrio transcribe \
  --audio-source-mode public-url \
  --public-base-url https://your-cdn.com/audio

# 自定义超时和轮询间隔
narrio transcribe \
  --timeout 600 \
  --query-interval 3.0

# 指定输出目录
narrio transcribe \
  --output-dir /path/to/output
```

## 步骤 4：查看转录结果

转录完成后，markdown 文件会保存在 `content/transcripts/` 目录：

```bash
ls content/transcripts/
# my-podcast.md

cat content/transcripts/my-podcast.md
```

转录结果包含：
- 音频元信息
- **全文** - 完整的转录文本
- **分段** - 带时间戳的分段文本
- 原始 API 返回数据

## 步骤 5：生成图文内容

### 默认模式（推荐 - 自动使用 highlight）

对于 podcast 类型，默认会自动提取亮点并跳过 chunkify：

```bash
narrio run \
  --content-type podcast \
  --markdown my-podcast.md \
  --style OpenAI
```

这个模式会：
1. ✅ 提取转录文本中的亮点语句
2. ❌ 跳过 chunkify（不需要分段）
3. ✅ 使用亮点直接生成图片

### 手动控制 highlight

如果需要同时运行 highlight 和 chunkify：

```bash
narrio run \
  --content-type podcast \
  --markdown my-podcast.md \
  --style OpenAI \
  --extract-highlights true
```

如果只想使用 chunkify（不提取亮点）：

```bash
narrio run \
  --content-type podcast \
  --markdown my-podcast.md \
  --style OpenAI \
  --extract-highlights false
```

### 限制生成图片数量

```bash
# 只生成前 5 张图片
narrio run \
  --content-type podcast \
  --markdown my-podcast.md \
  --style OpenAI \
  --max-pages 5
```

## 完整工作流示例

```bash
# 1. 准备音频
cp ~/Downloads/tech-podcast-ep42.mp3 content/audio/

# 2. 设置 API 密钥
export VOLCENGINE_API_KEY="your-volcengine-key"
export OPENROUTER_API_KEY="your-openrouter-key"

# 3. 转录音频
narrio transcribe --language zh-CN

# 4. 查看转录结果
cat content/transcripts/tech-podcast-ep42.md

# 5. 生成图文（自动提取亮点）
narrio run \
  --content-type podcast \
  --markdown tech-podcast-ep42.md \
  --style OpenAI \
  --max-pages 5

# 6. 查看结果
# 图片生成在 .narrio/workbench/podcast/<combo-id>/runs/<run-id>/render/
```

## 批量处理多个音频

```bash
# 将所有音频放到一个目录
mkdir -p content/audio/season-1
cp ~/podcast/*.mp3 content/audio/season-1/

# 批量转录
narrio transcribe --audio-input content/audio/season-1

# 查看所有转录结果
ls content/transcripts/

# 可以使用 tune 命令批量生成多个风格
narrio tune --input content/transcripts/episode-1.md --styles "OpenAI,Anthropic,Google"
```

## 音频来源模式详解

### 1. `auto` 模式（默认）

自动选择最佳方式：
1. 首先尝试 **inline**（base64 编码）
2. 如果失败，回退到 **upload**（上传到临时服务）

适合大多数场景。

### 2. `inline` 模式

将音频 base64 编码后直接发送给 API：
- ✅ 优点：不需要上传，速度快
- ❌ 缺点：不适合大文件（>10MB）

```bash
narrio transcribe --audio-source-mode inline
```

### 3. `upload` 模式

上传到临时文件托管服务（默认 https://0x0.st）：
- ✅ 优点：支持大文件
- ❌ 缺点：需要上传时间，文件会暂时公开

```bash
narrio transcribe --audio-source-mode upload
```

自定义上传服务：

```bash
narrio transcribe \
  --audio-source-mode upload \
  --upload-url https://your-upload-service.com
```

### 4. `public-url` 模式

使用已有的公网 URL：
- ✅ 优点：不需要上传，支持大文件
- ⚠️ 前提：音频文件必须已经可以通过公网访问

```bash
# 假设你的音频已经在 CDN 上
narrio transcribe \
  --audio-source-mode public-url \
  --public-base-url https://cdn.example.com/podcasts
```

## 常见问题

### Q1: 转录失败，提示认证错误？

检查 API 密钥是否正确：

```bash
# 查看当前环境变量
echo $VOLCENGINE_API_KEY

# 重新设置
export VOLCENGINE_API_KEY="your-correct-key"
```

### Q2: 转录速度很慢？

可能的原因：
1. 音频文件较大 - 尝试使用 `--audio-source-mode upload`
2. 网络较慢 - 使用 `--public-base-url` 如果音频已在公网
3. API 负载较高 - 调整 `--query-interval` 到更大的值

### Q3: 转录结果不准确？

尝试：
1. 明确指定语言：`--language zh-CN`
2. 使用更高质量的音频文件
3. 确保音频清晰，无过多背景噪音

### Q4: 如何只转录音频的一部分？

目前不支持指定时间范围。建议使用音频编辑工具（如 ffmpeg）先裁剪音频：

```bash
# 使用 ffmpeg 裁剪音频（0:30 开始，持续 5 分钟）
ffmpeg -i input.mp3 -ss 00:00:30 -t 00:05:00 output.mp3

# 然后转录裁剪后的音频
narrio transcribe --audio-input output.mp3
```

### Q5: 可以离线转录吗？

不可以，ASR 功能需要调用火山引擎的在线 API。如果需要离线转录，可以考虑使用 Whisper 等本地模型。

### Q6: 转录后的 markdown 格式可以自定义吗？

转录生成的 markdown 格式是固定的，但你可以在生成图文之前手动编辑转录文件：

```bash
# 转录
narrio transcribe

# 编辑转录结果
vim content/transcripts/my-podcast.md

# 生成图文
narrio run --content-type podcast --markdown my-podcast.md
```

## 成本估算

火山引擎 ASR 按音频时长计费，具体价格请参考 [火山引擎定价页面](https://www.volcengine.com/pricing)。

示例：
- 1 小时音频 ≈ ¥0.x 元（具体价格以官网为准）
- 支持新用户免费额度

## 下一步

- 了解如何自定义提示词：[docs/PROMPTS.md](./PROMPTS.md)
- 了解如何创建自定义风格：[docs/STYLES.md](./STYLES.md)
- 了解完整的实验系统：[how-to-run.md](../how-to-run.md)
