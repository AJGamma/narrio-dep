# Lab 模式界面演示

本文档展示 Lab 模式的交互界面外观。

## 1. 启动 Lab 模式

```bash
$ narrio lab
```

## 2. 内容类型选择

```
选择内容类型>
  article
  podcast
```

使用方向键或直接输入搜索关键词。

## 3. 起始阶段选择（Podcast）

```
选择起始阶段>
  from-audio (从音频文件开始)
  from-source (从 markdown 文件开始)
  from-chunk (从已有 chunk 恢复)
  from-editorial (从已有 editorial 恢复)
```

## 4. 音频文件选择（带文件大小和时间）

### 使用 fzf（推荐体验）

```
选择音频文件> epi
> episode-042-tech-trends.mp3                [2026-04-08 18:30:45] (45.2 MB)
  episode-041-ai-future.mp3                  [2026-04-08 17:15:20] (38.7 MB)
  episode-040-cloud-native.mp3               [2026-04-08 16:00:00] (52.3 MB)
  episode-039-devops.mp3                     [2026-04-07 22:00:00] (41.1 MB)
  4/15
```

**说明**：
- 顶部显示搜索框，输入 `epi` 自动过滤
- 每行显示：文件名（40字符宽）+ 修改时间 + 文件大小
- 底部显示：当前显示 4 个结果，共 15 个文件
- 使用 `↑↓` 或 `Ctrl+J/K` 导航

### 没有 fzf 时（编号列表）

```
选择音频文件
1. episode-042-tech-trends.mp3                [2026-04-08 18:30:45] (45.2 MB)
2. episode-041-ai-future.mp3                  [2026-04-08 17:15:20] (38.7 MB)
3. episode-040-cloud-native.mp3               [2026-04-08 16:00:00] (52.3 MB)
4. episode-039-devops.mp3                     [2026-04-07 22:00:00] (41.1 MB)
5. interview-python-creator.wav               [2026-04-07 14:30:00] (120.5 MB)
请输入编号: 1
```

## 5. Markdown 文件选择（带修改时间）

### 使用 fzf

```
选择输入文件> AI
> AI写作指南1.0：智力的容器大于智力本身.md      [2026-04-08 16:20:30]
  AI-Agent-Development-Guide.md            [2026-04-08 14:10:15]
  2/6
```

**说明**：
- 输入 `AI` 自动搜索包含 "AI" 的文件
- 显示 2 个匹配结果，总共 6 个文件
- 文件按修改时间排序（最新的在前）

### 没有 fzf 时

```
选择输入文件
1. AI写作指南1.0：智力的容器大于智力本身.md      [2026-04-08 16:20:30]
2. Effective context engineering for AI age.md [2026-04-08 14:10:15]
3. The Gut Decision Matrix_ When to Trust I.md [2026-04-08 03:33:11]
4. 技术播客转录-第42期.md                       [2026-04-07 22:30:00]
5. 采访记录-Python创始人.md                    [2026-04-06 15:45:00]
6. 深度学习入门指南.md                         [2026-04-05 10:20:00]
请输入编号: 1
```

## 6. Style 选择（带修改时间）

### 使用 fzf

```
选择 style> open
> OpenAI                                     [2026-04-08 12:00:00]
  1/4
```

**说明**：
- 输入 `open` 快速定位到 OpenAI
- 显示 style 目录的最后修改时间
- 帮助识别最近更新的 style

### 没有 fzf 时

```
选择 style
1. OpenAI                                     [2026-04-08 12:00:00]
2. Anthropic                                  [2026-04-07 18:30:00]
3. Google                                     [2026-04-06 09:15:00]
4. MyCustomStyle                              [2026-03-20 14:45:00]
请输入编号: 1
```

## 7. 高级选项（文本输入）

```
chunk prompt 覆盖路径（留空表示默认）: 
stylify prompt 覆盖路径（留空表示默认）: 
redsoul prompt 覆盖路径（留空表示默认）: 
image prompt 覆盖路径（留空表示默认）: 
实验标签 [interactive]: lab-test-001
并行渲染 worker 数（留空表示自动，上限 5）: 3
```

**提示**：留空表示使用默认值

## 8. Highlight 选项选择

```
是否提取高亮语句（auto=根据类型自动决定，yes=强制，no=跳过）>
  auto
  yes
  no
```

## 9. 图片数量限制

```
图片生成数量上限（留空表示全部生成）: 5
```

## 10. 运行开始

```
run created: run_id=run-20260408-183045 combo_id=podcast-episode-042-OpenAI-abc12345 run_dir=/Users/mac/code/narrio/.narrio/workbench/podcast/podcast-episode-042-OpenAI-abc12345/runs/run-20260408-183045
events log: /Users/mac/code/narrio/.narrio/workbench/podcast/podcast-episode-042-OpenAI-abc12345/runs/run-20260408-183045/logs/events.jsonl
pipeline start: start_stage=from-audio content_type=podcast extract_highlights=None
transcription started: audio=episode-042-tech-trends.mp3
提交任务：episode-042-tech-trends.mp3 [inline-data]
task submitted: task_id=abc123 resource_id=volc.seedasr.auc
waiting for result: status=20000001
...
```

## 界面对比

### fzf 模式的优势

| 特性 | fzf 模式 | 编号列表模式 |
|------|----------|--------------|
| 搜索/过滤 | ✅ 实时模糊搜索 | ❌ 不支持 |
| 显示匹配数 | ✅ 显示 "2/15" | ❌ 显示全部 |
| 快速定位 | ✅ 输入关键词 | ❌ 需要滚动查看 |
| 键盘导航 | ✅ 方向键/Vim键 | ❌ 只能输入数字 |
| 视觉体验 | ✅ 高亮当前项 | ⚠️  简单列表 |
| 文件预览 | ❌ 暂不支持 | ❌ 不支持 |

### 修改时间排序的好处

**问题**：传统按字母排序
```
ai-intro.md        [2026-03-01]
blog-post.md       [2026-04-08]  ← 最新
draft.md           [2026-02-15]
notes.md           [2026-04-07]
```

**解决**：按时间排序（最新在前）
```
blog-post.md       [2026-04-08]  ← 最新（第一个）
notes.md           [2026-04-07]
ai-intro.md        [2026-03-01]
draft.md           [2026-02-15]
```

**优势**：
- ✅ 最新文件总是在最上面，直接按 Enter 选择
- ✅ 不需要记住文件名，按时间查找
- ✅ 快速识别哪些文件最近修改过

## fzf 搜索示例

### 搜索文件名

```
# 搜索包含 "episode" 的文件
选择音频文件> episode
> episode-042.mp3     [2026-04-08 18:30:45]
  episode-041.mp3     [2026-04-08 17:15:20]
  episode-040.mp3     [2026-04-08 16:00:00]
  3/15
```

### 搜索日期

```
# 搜索 4 月 8 日修改的文件
选择音频文件> 04-08
> episode-042.mp3     [2026-04-08 18:30:45]
  tech-talk.mp3       [2026-04-08 17:15:20]
  interview.mp3       [2026-04-08 16:00:00]
  3/15
```

### 精确匹配

```
# 使用单引号精确匹配
选择音频文件> 'episode-042
> episode-042.mp3     [2026-04-08 18:30:45]
  1/15
```

### 反向搜索

```
# 使用 ! 排除关键词
选择音频文件> !episode
> interview.mp3       [2026-04-08 16:00:00]
  tech-talk.mp3       [2026-04-07 22:00:00]
  2/15
```

## 安装 fzf

### macOS
```bash
brew install fzf
```

### Linux (Ubuntu/Debian)
```bash
sudo apt install fzf
```

### 验证安装
```bash
$ fzf --version
0.48.0 (brew)
```

安装后，重新运行 `narrio lab` 即可享受 fzf 界面。

## 下一步

- 完整 Lab 模式指南：[LAB-MODE-GUIDE.md](./LAB-MODE-GUIDE.md)
- 端到端音频处理：[END-TO-END-AUDIO.md](./END-TO-END-AUDIO.md)
- fzf 官方文档：https://github.com/junegunn/fzf
