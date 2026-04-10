# 音频文件目录

此目录用于存放待转录的音频文件（mp3、wav、m4a、ogg、flac 等格式）。

## 使用方法

### 1. 放置音频文件

将你的播客音频文件放到这个目录：

```
content/audio/
├── podcast-episode-1.mp3
├── podcast-episode-2.mp3
└── interview.wav
```

### 2. 配置火山引擎 API 密钥

设置环境变量（三选一）：

**方式一：使用新版 API Key**
```bash
export VOLCENGINE_API_KEY="your-api-key"
```

**方式二：使用旧版认证**
```bash
export VOLCENGINE_APP_KEY="your-app-key"
export VOLCENGINE_ACCESS_TOKEN="your-access-token"
```

**方式三：在命令行中传入**
```bash
narrio transcribe --api-key "your-api-key"
```

### 3. 运行转录

```bash
# 转录所有音频文件（默认读取 content/audio/）
narrio transcribe

# 转录单个文件
narrio transcribe --audio-input content/audio/episode-1.mp3

# 转录指定目录的所有音频
narrio transcribe --audio-input /path/to/your/audio/folder

# 指定输出目录
narrio transcribe --output-dir /path/to/output

# 指定语言
narrio transcribe --language zh-CN
```

### 4. 查看转录结果

转录完成后，markdown 文件会生成在 `content/transcripts/` 目录：

```
content/transcripts/
├── podcast-episode-1.md
├── podcast-episode-2.md
└── interview.md
```

## 高级选项

### 音频来源模式

```bash
# auto: 自动选择（使用 inline base64 编码，适合 < 50MB 的文件）
narrio transcribe --audio-source-mode auto

# inline: 将音频 base64 编码后直接发送（推荐，适合大多数文件）
narrio transcribe --audio-source-mode inline

# public-url: 使用已有的公网 URL（推荐用于大文件 > 50MB）
narrio transcribe --audio-source-mode public-url --public-base-url https://your-cdn.com/audio

# upload: 上传到临时服务（不推荐，许多服务已不可用）
narrio transcribe --audio-source-mode upload --upload-url https://your-service.com
```

**⚠️ 重要提示**：
- 默认的 `auto` 模式现在只使用 `inline`（base64 编码）
- 临时上传服务（如 0x0.st）已不可用
- 对于大文件（> 50MB），建议使用 `public-url` 模式

### 自定义火山引擎资源 ID

```bash
# 使用特定资源 ID
narrio transcribe --resource-id volc.bigasr.auc

# 自动尝试多个资源 ID（默认）
narrio transcribe --resource-id auto
```

### 调整超时和轮询间隔

```bash
# 设置请求超时为 10 分钟，轮询间隔为 3 秒
narrio transcribe --timeout 600 --query-interval 3.0
```

## 支持的音频格式

- `.mp3` - MP3 音频
- `.wav` - WAV 音频
- `.m4a` - M4A 音频
- `.ogg` - OGG 音频
- `.flac` - FLAC 音频

## 转录后的工作流

转录完成后，你可以继续使用 narrio 进行图文生成：

```bash
# 方式一：默认模式（podcast 自动使用 highlight，跳过 chunkify）
narrio run --content-type podcast --markdown podcast-episode-1.md --style OpenAI

# 方式二：同时运行 highlight 和 chunkify
narrio run --content-type podcast --markdown podcast-episode-1.md --style OpenAI --extract-highlights true

# 方式三：只运行 chunkify
narrio run --content-type podcast --markdown podcast-episode-1.md --style OpenAI --extract-highlights false
```

## 常见问题

### Q: 如何获取火山引擎 API 密钥？

访问 [火山引擎控制台](https://console.volcengine.com/speech/app) 创建应用并获取 API Key。

### Q: 转录失败怎么办？

1. 检查 API 密钥是否正确
2. 检查音频文件格式是否支持
3. 检查网络连接
4. 查看错误日志获取详细信息

### Q: 音频文件太大怎么办？

建议使用 `--audio-source-mode upload` 或 `--audio-source-mode public-url` 模式，避免使用 inline 模式。

### Q: 可以批量转录吗？

可以！只需将所有音频文件放到同一个目录，然后运行：

```bash
narrio transcribe --audio-input /path/to/audio/folder
```
