# 快速开始：从音频到图片

5 分钟内从播客音频生成精美图文内容。

## 1. 安装

```bash
cd narrio
pip install -e .
```

## 2. 配置 API 密钥

编辑 `.narrio.yaml`（已配置好的示例）：

```yaml
# Text API - 用于文本处理
text_api:
  provider: "hnd1-aihub"
  api_key: "sk-e0UauopbN6t5yPWYJRNbOQ"
  base_url: "https://hnd1.aihub.zeabur.ai/v1/chat/completions"
  model: "gemini-3-flash-preview"

# Image API - 用于图片生成
image_api:
  provider: "openrouter"
  api_key: "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"
  base_url: "https://openrouter.ai/api/v1/chat/completions"
  model: "google/gemini-3.1-flash-image-preview"

# ASR API - 用于音频转录
asr_api:
  provider: "volcengine"
  app_id: "9759076940"
  app_key: "YkREQk1qa0xNbm1xZWx3WQ=="
  access_token: "NLeZrJOrqJ0BruA47WST-OD0uO8zw0mT"
  secret_key: "Y-S47__rekdacbQ_V1X8ucV8b2CTDhP7"
```

**注意**：这些是已配置好的示例凭证，可以直接使用。

## 3. 准备音频文件

```bash
# 将你的播客音频放到 content/audio/ 目录
cp your-podcast.mp3 content/audio/
```

支持格式：mp3, wav, m4a, ogg, flac

## 4. 一键生成

```bash
# 生成 5 张图片预览（快速测试）
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI \
  --max-pages 5
```

或者生成所有图片：

```bash
narrio run \
  --content-type podcast \
  --audio-file your-podcast.mp3 \
  --style OpenAI
```

## 5. 查看结果

```bash
# 查看生成的图片
ls -lh .narrio/workbench/podcast/*/latest/render/

# 或使用系统预览
open .narrio/workbench/podcast/*/latest/render/
```

## 工作流程

```
your-podcast.mp3
    ↓ [ASR 转录]
转录文本
    ↓ [提取亮点]
精选语句
    ↓ [图片生成]
1.png, 2.png, 3.png, ...
```

## 完整输出

```
.narrio/workbench/podcast/<combo-id>/latest/
├── transcribe/          # ASR 转录结果
├── highlight/           # 提取的亮点
├── editorial/           # Editorial JSON
└── render/              # 生成的图片 ✨
    ├── 1.png
    ├── 2.png
    ├── 3.png
    └── ...
```

## 常用选项

```bash
# 指定语言（中文）
narrio run \
  --content-type podcast \
  --audio-file podcast.mp3 \
  --style OpenAI \
  --asr-language zh-CN

# 指定语言（英文）
narrio run \
  --content-type podcast \
  --audio-file podcast.mp3 \
  --style OpenAI \
  --asr-language en-US

# 使用不同风格
narrio run \
  --content-type podcast \
  --audio-file podcast.mp3 \
  --style Anthropic

# 批量生成多个风格
narrio transcribe --audio-input podcast.mp3
narrio tune \
  --input content/transcripts/podcast.md \
  --styles "OpenAI,Anthropic,Google"
```

## 下一步

- 完整文档：[docs/END-TO-END-AUDIO.md](docs/END-TO-END-AUDIO.md)
- ASR 详解：[docs/ASR-WORKFLOW.md](docs/ASR-WORKFLOW.md)
- 命令速查：[docs/TRANSCRIBE-QUICK-REFERENCE.md](docs/TRANSCRIBE-QUICK-REFERENCE.md)
- 自定义风格：[docs/STYLES.md](docs/STYLES.md) （如果存在）

## 故障排查

### 问题：找不到音频文件

```bash
# 使用绝对路径
narrio run \
  --content-type podcast \
  --audio-file "$(pwd)/content/audio/podcast.mp3" \
  --style OpenAI
```

### 问题：ASR 认证失败

检查 `.narrio.yaml` 中的 ASR 配置是否正确。

### 问题：生成太慢

```bash
# 先只生成 3 张图片测试
narrio run \
  --content-type podcast \
  --audio-file podcast.mp3 \
  --style OpenAI \
  --max-pages 3
```

## 需要帮助？

- 查看完整文档：`docs/`
- 运行指南：[how-to-run.md](how-to-run.md)
- 提交问题：[GitHub Issues](https://github.com/yourrepo/narrio/issues)
