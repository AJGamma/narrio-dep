# Lab 模式错误诊断

## 当前错误

```
FileNotFoundError: 缺少可复用运行目录
```

发生在 `copy_resume_artifacts` 函数中。

## 可能的原因

1. **start_stage 设置错误** - 用户选择了某个需要 resume 的阶段（from-chunk 或 from-editorial），但没有提供有效的 reuse_from_run 路径

2. **audio_file 参数未正确传递** - Lab 模式中选择了音频文件，但 audio_file 参数没有正确设置

## 诊断步骤

### 1. 重新运行 Lab 模式并注意选择

```bash
python -m narrio lab

# 注意观察每一步的选择：
# - 选择内容类型: podcast
# - 选择起始阶段: from-audio (从音频文件开始)  ← 确保选择这个
# - 选择音频文件: [选择你的音频]
# - 选择 style: [选择你的 style]
```

### 2. 如果问题持续，使用命令行模式

```bash
# 直接使用命令行指定参数
narrio run \
  --content-type podcast \
  --audio-file content/audio/Dopamine_Serotonin_Decisions.mp3 \
  --style Sspai \
  --max-pages 2
```

### 3. 检查日志

运行后，查看详细日志：

```bash
# 查看最新运行目录
ls -lth .narrio/workbench/podcast/*/runs/ | head -5

# 查看事件日志
tail -20 .narrio/workbench/podcast/*/latest/logs/events.jsonl
```

## 临时解决方案

如果 Lab 模式持续出错，使用命令行模式：

### 方式一：端到端（音频 → 图片）

```bash
narrio run \
  --content-type podcast \
  --audio-file Dopamine_Serotonin_Decisions.mp3 \
  --style Sspai \
  --max-pages 2
```

### 方式二：分步执行

```bash
# 步骤 1: 转录音频
narrio transcribe --audio-input content/audio/Dopamine_Serotonin_Decisions.mp3

# 步骤 2: 生成图片
narrio run \
  --content-type podcast \
  --markdown Dopamine_Serotonin_Decisions.md \
  --style Sspai \
  --max-pages 2
```

## 已知问题

1. **fzf 选择被取消** - 如果在 fzf 选择时按 Esc 或 Ctrl+C，会导致程序退出
   - 解决方案：重新运行，使用方向键选择而不是取消

2. **resume 模式需要输入路径** - 选择 from-chunk 或 from-editorial 必须提供有效的历史运行目录
   - 解决方案：
     - 如果不想 resume，选择 from-source 或 from-audio
     - 如果要 resume，使用 `ls -lth .narrio/workbench/podcast/*/runs/` 查找路径

## 获取帮助

如果以上方法都无法解决，请提供以下信息：

1. 完整的错误堆栈
2. 你在 Lab 模式中的选择（每一步）
3. 运行 `ls -lh content/audio/` 的输出
4. 运行 `python -c "from src.narrio.config import load_config; config = load_config(); print('ASR:', config.asr_api is not None)"` 的输出
