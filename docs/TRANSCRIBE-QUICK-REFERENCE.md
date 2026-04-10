# ASR 转录命令速查表

## 基本命令

```bash
# 转录所有音频（默认 content/audio/）
narrio transcribe

# 转录单个文件
narrio transcribe --audio-input file.mp3

# 转录目录
narrio transcribe --audio-input /path/to/audio/
```

## 认证方式

```bash
# 方式1: 环境变量
export VOLCENGINE_API_KEY="your-key"
narrio transcribe

# 方式2: 命令行参数
narrio transcribe --api-key "your-key"

# 方式3: 旧版认证
narrio transcribe \
  --app-key "your-app-key" \
  --access-token "your-token"
```

## 语言设置

```bash
# 中文
narrio transcribe --language zh-CN

# 英文
narrio transcribe --language en-US

# 自动检测（默认）
narrio transcribe
```

## 音频来源模式

```bash
# 自动（先 inline 后 upload）
narrio transcribe --audio-source-mode auto

# Base64 内联
narrio transcribe --audio-source-mode inline

# 上传到临时服务
narrio transcribe --audio-source-mode upload

# 使用公网 URL
narrio transcribe \
  --audio-source-mode public-url \
  --public-base-url https://cdn.example.com/audio
```

## 自定义选项

```bash
# 指定输出目录
narrio transcribe --output-dir /custom/output/

# 自定义超时（秒）
narrio transcribe --timeout 900

# 自定义轮询间隔（秒）
narrio transcribe --query-interval 5.0

# 自定义资源 ID
narrio transcribe --resource-id volc.bigasr.auc

# 自定义上传服务
narrio transcribe \
  --audio-source-mode upload \
  --upload-url https://transfer.sh
```

## 完整工作流

```bash
# 1. 转录
narrio transcribe --language zh-CN

# 2. 生成图文（默认模式 - 自动提取亮点）
narrio run \
  --content-type podcast \
  --markdown transcript.md \
  --style OpenAI

# 3. 查看结果
ls .narrio/workbench/podcast/*/runs/*/render/
```

## 常用组合

### 快速转录 + 生成

```bash
# 设置密钥
export VOLCENGINE_API_KEY="asr-key"
export OPENROUTER_API_KEY="llm-key"

# 转录并生成 5 张图
narrio transcribe && \
narrio run \
  --content-type podcast \
  --markdown your-file.md \
  --style OpenAI \
  --max-pages 5
```

### 批量处理

```bash
# 转录多个文件
narrio transcribe --audio-input podcasts/season-1/

# 使用 tune 生成多个风格
for file in content/transcripts/*.md; do
  basename="${file##*/}"
  basename="${basename%.md}"
  narrio tune --input "$file" --styles "OpenAI,Anthropic,Google"
done
```

### 公网 URL 模式（大文件推荐）

```bash
# 假设音频已在 CDN
narrio transcribe \
  --audio-source-mode public-url \
  --public-base-url https://cdn.example.com/podcasts \
  --audio-input content/audio/
```

## 环境变量

```bash
# ASR 认证
VOLCENGINE_API_KEY          # 新版 API Key（推荐）
VOLCENGINE_APP_KEY          # 旧版 App Key
VOLCENGINE_ACCESS_TOKEN     # 旧版 Access Token

# LLM/图片生成
OPENROUTER_API_KEY          # OpenRouter Key
TEXT_API_KEY                # 文本生成专用
IMAGE_API_KEY               # 图片生成专用
TEXT_API_BASE_URL           # 文本 API 地址
IMAGE_API_BASE_URL          # 图片 API 地址

# 日志
NARRIO_LOG_LEVEL            # DEBUG, INFO, WARNING, ERROR
```

## 支持的音频格式

- `.mp3` - MP3 音频
- `.wav` - WAV 音频
- `.m4a` - M4A 音频
- `.ogg` - OGG 音频
- `.flac` - FLAC 音频

## 转录输出格式

```markdown
# 文件名

- 源文件：filename.mp3
- 音频来源：inline-data / upload-url / public-url
- 生成时间：2024-01-01 12:00:00
- 接口：Volcengine AUC HTTP
- Resource ID：volc.bigasr.auc
- 语言：zh-CN / auto
- 状态码：20000000

## 全文

完整的转录文本...

## 分段

- [00:00:00-00:00:05] 第一句话
- [00:00:05-00:00:10] 第二句话
...

## 原始返回

```json
{
  "result": { ... }
}
```
```

## 错误处理

```bash
# 查看详细日志
export NARRIO_LOG_LEVEL=DEBUG
narrio transcribe

# 忽略错误继续（batch 模式需要）
# （当前不支持，需要手动处理失败的文件）
```

## 帮助信息

```bash
# 查看所有选项
narrio transcribe --help

# 查看主命令帮助
narrio --help

# 查看 run 命令帮助
narrio run --help
```
