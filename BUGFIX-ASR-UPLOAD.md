# Bug 修复：ASR 上传服务不可用

## 问题描述

运行 Lab 模式或使用 `--audio-file` 时，转录失败并报错：

```
RuntimeError: 音频上传失败：HTTP 503 uploads disabled because it's been almost nothing but AI botnet spam for the past few months.
```

## 错误原因

默认的临时文件上传服务 `0x0.st` 已经关闭上传功能（由于 AI botnet spam）。

在 `auto` 模式下，ASR 服务会尝试：
1. 先使用 inline（base64 编码）
2. 如果失败，回退到 upload（上传到 0x0.st）

但是在生成备选方案列表时就会立即执行 upload 操作，导致失败。

### 错误代码位置

`src/narrio/asr_service.py:319-322`

```python
return [
    (encode_file_to_base64(audio_path), "inline-data", True),
    (upload_audio_file(...), "upload-url", False),  # ← 这里立即执行，导致失败
]
```

## 修复方案

### 修改默认行为

将 `auto` 模式改为**只使用 inline（base64 编码）**，不再尝试 upload fallback。

```python
# Auto mode: only use inline (don't fallback to upload as many upload services are unreliable)
return [
    (encode_file_to_base64(audio_path), "inline-data", True),
]
```

### 改进错误提示

当转录失败时，根据文件大小提供有用的建议：

```python
# 如果文件 > 50MB，提示用户：
# 1. 使用 --audio-source-mode public-url
# 2. 压缩音频文件
# 3. 使用其他上传服务
```

## 文件大小限制

- **小于 20MB**：inline 模式通常工作良好
- **20-50MB**：inline 可能工作，但取决于网络和 API 限制
- **大于 50MB**：建议使用 public-url 模式

### Base64 编码大小

原始文件大小 × 1.33 = Base64 大小

例如：
- 18MB 音频 → 24MB Base64
- 50MB 音频 → 67MB Base64

## 使用建议

### 小文件（< 20MB）- 使用默认 auto 模式

```bash
# Lab 模式（默认使用 auto/inline）
narrio lab

# 命令行模式（默认使用 auto/inline）
narrio run \
  --content-type podcast \
  --audio-file your-small-file.mp3 \
  --style OpenAI
```

### 中等文件（20-50MB）- 显式指定 inline

```bash
narrio run \
  --content-type podcast \
  --audio-file your-medium-file.mp3 \
  --style OpenAI \
  --asr-audio-source-mode inline
```

如果 inline 失败，尝试压缩音频：

```bash
# 使用 ffmpeg 压缩音频
ffmpeg -i input.mp3 -b:a 96k -ar 22050 output.mp3

# 然后重新尝试
narrio run --content-type podcast --audio-file output.mp3 --style OpenAI
```

### 大文件（> 50MB）- 使用 public-url

**步骤 1：上传到 CDN 或文件服务器**

```bash
# 使用你自己的服务器/CDN
scp large-podcast.mp3 user@cdn.example.com:/var/www/audio/

# 或使用云存储（AWS S3, Google Cloud Storage, 阿里云 OSS 等）
```

**步骤 2：使用 public-url 模式**

```bash
narrio run \
  --content-type podcast \
  --audio-file large-podcast.mp3 \
  --style OpenAI \
  --asr-audio-source-mode public-url \
  --asr-public-base-url https://cdn.example.com/audio
```

## 受影响的命令

### ✅ 已修复
- `narrio lab` - 选择 from-audio
- `narrio run --audio-file`
- `narrio transcribe`

### ⚙️ 配置调整

如果你的 `.narrio.yaml` 中有 ASR 配置，无需修改。默认行为已更改。

## 验证修复

```bash
# 测试 auto 模式（现在只使用 inline）
python -c "
from pathlib import Path
from src.narrio.asr_service import resolve_audio_sources

audio_path = Path('content/audio/test.mp3')
sources = resolve_audio_sources(
    audio_path=audio_path,
    audio_source_mode='auto',
    public_base_url=None,
    upload_url='https://0x0.st',
    timeout=10
)

print(f'Number of sources: {len(sources)}')  # Should be 1
print(f'Source type: {sources[0][1]}')      # Should be 'inline-data'
print('✅ Auto mode now only uses inline')
"
```

## 替代上传服务

如果你需要使用 upload 模式，可以替换默认的上传服务：

```bash
# 使用其他临时文件服务
narrio run \
  --content-type podcast \
  --audio-file your-file.mp3 \
  --style OpenAI \
  --asr-audio-source-mode upload \
  --asr-upload-url https://your-upload-service.com
```

**可能的替代服务**：
- https://file.io
- https://transfer.sh
- 你自己的上传服务

⚠️ **注意**：这些服务的可用性无法保证，推荐使用 inline 或 public-url 模式。

## 相关文档

- ASR 工作流：[docs/ASR-WORKFLOW.md](docs/ASR-WORKFLOW.md)
- 端到端音频处理：[docs/END-TO-END-AUDIO.md](docs/END-TO-END-AUDIO.md)
- 快速开始：[QUICKSTART-AUDIO.md](QUICKSTART-AUDIO.md)

## 性能建议

### 压缩音频以加快上传

```bash
# 降低比特率（推荐用于语音）
ffmpeg -i input.mp3 -b:a 96k output.mp3

# 降低采样率
ffmpeg -i input.mp3 -ar 22050 output.mp3

# 同时降低比特率和采样率
ffmpeg -i input.mp3 -b:a 96k -ar 22050 output.mp3

# 转换为更高压缩率的格式
ffmpeg -i input.mp3 -codec:a libopus -b:a 96k output.opus
```

### 分段处理大文件

```bash
# 将大文件切分为多个小段
ffmpeg -i large-podcast.mp3 -f segment -segment_time 600 -c copy output%03d.mp3

# 分别转录每个片段
for file in output*.mp3; do
    narrio transcribe --audio-input "$file"
done

# 手动合并转录结果
```

## 总结

- ✅ 默认使用 inline 模式（无需外部上传服务）
- ✅ 适用于大多数音频文件（< 50MB）
- ✅ 大文件使用 public-url 模式
- ✅ 提供了更好的错误提示
