# Lab 模式交互式指南

Lab 模式是 Narrio 的交互式工作台，提供友好的 UI 来选择文件和配置实验。

## 启动 Lab 模式

```bash
narrio lab
```

或带 API key：

```bash
narrio lab --api-key "your-api-key"
```

## 交互流程

### 1. 选择内容类型

```
选择内容类型>
  article
  podcast
```

### 2. 选择起始阶段

根据内容类型不同，会显示不同的选项：

**Podcast（播客）**
```
选择起始阶段>
  from-audio (从音频文件开始)
  from-source (从 markdown 文件开始)
  from-chunk (从已有 chunk 恢复)
  from-editorial (从已有 editorial 恢复)
```

**Article（文章）**
```
选择起始阶段>
  from-source (从 markdown 文件开始)
  from-chunk (从已有 chunk 恢复)
  from-editorial (从已有 editorial 恢复)
```

### 3. 选择输入文件

根据起始阶段不同，会显示不同的选择界面：

#### 3a. 从音频文件开始（from-audio）

**使用 fzf（推荐）**

如果系统安装了 `fzf`，会显示交互式选择界面：

```
选择音频文件>
  episode-42.mp3                            [2026-04-08 18:30:45] (45.2 MB)
  interview-tech.wav                        [2026-04-08 17:15:20] (120.5 MB)
  podcast-daily.m4a                         [2026-04-07 09:00:00] (32.1 MB)
```

特性：
- ✅ 显示文件大小（MB）
- ✅ 显示最后修改时间
- ✅ 按时间排序（最新的在上面）
- ✅ 支持模糊搜索（输入关键词快速过滤）
- ✅ 使用方向键或 Ctrl+J/K 导航

**没有 fzf 时**

显示编号列表：

```
选择音频文件
1. episode-42.mp3                            [2026-04-08 18:30:45] (45.2 MB)
2. interview-tech.wav                        [2026-04-08 17:15:20] (120.5 MB)
3. podcast-daily.m4a                         [2026-04-07 09:00:00] (32.1 MB)
请输入编号:
```

#### 3b. 从 markdown 开始（from-source）

**使用 fzf**

```
选择输入文件>
  AI写作指南.md                              [2026-04-08 16:20:30]
  技术播客转录.md                            [2026-04-08 14:10:15]
  采访记录.md                                [2026-04-07 22:30:00]
```

特性：
- ✅ 显示最后修改时间
- ✅ 按时间排序（最新的在上面）
- ✅ 支持模糊搜索

**没有 fzf 时**

```
选择输入文件
1. AI写作指南.md                              [2026-04-08 16:20:30]
2. 技术播客转录.md                            [2026-04-08 14:10:15]
3. 采访记录.md                                [2026-04-07 22:30:00]
请输入编号:
```

### 4. 选择 Style（风格）

**使用 fzf**

```
选择 style>
  OpenAI                                     [2026-04-08 12:00:00]
  Anthropic                                  [2026-04-07 18:30:00]
  Google                                     [2026-04-06 09:15:00]
  MyCustomStyle                              [2026-03-20 14:45:00]
```

特性：
- ✅ 显示 style 目录的最后修改时间
- ✅ 按时间排序
- ✅ 支持模糊搜索

### 5. 高级选项

系统会依次询问：

```
chunk prompt 覆盖路径（留空表示默认）:
stylify prompt 覆盖路径（留空表示默认）:
redsoul prompt 覆盖路径（留空表示默认）:
image prompt 覆盖路径（留空表示默认）:
实验标签 [interactive]:
并行渲染 worker 数（留空表示自动，上限 5）:
```

### 6. Highlight 选项

```
是否提取高亮语句（auto=根据类型自动决定，yes=强制，no=跳过）>
  auto
  yes
  no
```

- **auto**: Podcast 自动提取 highlight，Article 跳过
- **yes**: 强制提取 highlight
- **no**: 跳过 highlight 提取

### 7. 图片数量限制

```
图片生成数量上限（留空表示全部生成）:
```

输入数字（如 `5`）或留空生成所有图片。

## 使用 fzf 的优势

### 安装 fzf

**macOS**
```bash
brew install fzf
```

**Linux (Ubuntu/Debian)**
```bash
sudo apt install fzf
```

**Linux (其他)**
```bash
# 通过 git 安装
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install
```

### fzf 快捷键

在交互式选择界面中：

- `↑/↓` 或 `Ctrl+K/J` - 上下移动
- `Enter` - 选择当前项
- `Ctrl+C` 或 `Esc` - 取消选择
- **输入文字** - 模糊搜索过滤
- `Tab` - 多选（如果支持）

### fzf 搜索示例

假设有这些文件：

```
episode-001-intro.mp3      [2026-04-08 18:30:45]
episode-002-golang.mp3     [2026-04-08 17:15:20]
episode-003-rust.mp3       [2026-04-08 16:00:00]
interview-python.mp3       [2026-04-07 22:00:00]
```

搜索示例：
- 输入 `epi` → 快速匹配所有 episode 文件
- 输入 `001` → 只显示 episode-001
- 输入 `rust` → 只显示 rust 相关文件
- 输入 `'inter` → 精确匹配 interview（单引号表示精确匹配）

## 完整示例

### 示例 1：从音频生成图片

```bash
$ narrio lab

# 1. 选择内容类型
选择内容类型> podcast

# 2. 选择起始阶段
选择起始阶段> from-audio (从音频文件开始)

# 3. 选择音频文件（fzf 界面）
选择音频文件>
> episode-042.mp3                            [2026-04-08 18:30:45] (45.2 MB)
  interview-tech.wav                        [2026-04-08 17:15:20] (120.5 MB)
  podcast-daily.m4a                         [2026-04-07 09:00:00] (32.1 MB)

# 4. 选择 style
选择 style> OpenAI

# 5. 跳过高级选项（直接按 Enter）
chunk prompt 覆盖路径（留空表示默认）:
stylify prompt 覆盖路径（留空表示默认）:
redsoul prompt 覆盖路径（留空表示默认）:
image prompt 覆盖路径（留空表示默认）:
实验标签 [interactive]:
并行渲染 worker 数（留空表示自动，上限 5）:

# 6. Highlight 选项
是否提取高亮语句> auto

# 7. 图片数量
图片生成数量上限（留空表示全部生成）: 5

# 开始运行...
run_id: run-20260408-183045
status: completed
combo_id: podcast-episode-042-OpenAI-abc12345
run_dir: /Users/mac/code/narrio/.narrio/workbench/podcast/podcast-episode-042-OpenAI-abc12345/runs/run-20260408-183045
```

### 示例 2：从 markdown 生成图片

```bash
$ narrio lab

# 1. 选择内容类型
选择内容类型> article

# 2. 选择起始阶段
选择起始阶段> from-source (从 markdown 文件开始)

# 3. 选择 markdown 文件（fzf 界面，输入 "AI" 搜索）
选择输入文件>
> AI写作指南.md                              [2026-04-08 16:20:30]

# 4. 选择 style
选择 style> Anthropic

# ... 其余步骤同上
```

### 示例 3：恢复已有运行

```bash
$ narrio lab

# 1. 选择内容类型
选择内容类型> podcast

# 2. 选择起始阶段
选择起始阶段> from-chunk (从已有 chunk 恢复)

# 3. 输入历史运行目录
输入历史运行目录: .narrio/workbench/podcast/podcast-episode-042-OpenAI-abc12345/runs/run-20260408-183045

# 4. 选择 style
选择 style> OpenAI

# ... 其余步骤同上
```

## 常见问题

### Q: 如何快速找到最新的文件？

A: 文件列表已按时间排序，最新的文件在最上面。使用 fzf 时，直接按 Enter 选择第一个（最新）文件。

### Q: 如何搜索特定文件？

A: 在 fzf 界面中直接输入关键词，例如：
- `episode` - 搜索所有包含 episode 的文件
- `2024` - 搜索 2024 年修改的文件
- `.mp3` - 只显示 mp3 文件

### Q: 没有 fzf 怎么办？

A: 系统会自动回退到编号列表模式，输入数字选择即可。但强烈推荐安装 fzf 以获得更好的体验。

### Q: 文件太多，列表太长怎么办？

A: 使用 fzf 的搜索功能快速过滤。fzf 支持模糊搜索，输入任意关键词都能快速定位。

### Q: 如何取消选择？

A: 在 fzf 界面按 `Ctrl+C` 或 `Esc`。在编号列表模式按 `Ctrl+C`。

### Q: 能否看到文件内容预览？

A: 当前版本暂不支持预览。如需查看文件内容，请在选择前使用 `cat` 或编辑器查看。

### Q: 修改时间是什么时区？

A: 显示的是本地时间（系统时区）。

## 提示和技巧

### 1. 快速重复上次实验

如果要重复上次的实验配置，只需：
1. 运行 `narrio lab`
2. 所有选项按 Enter 使用默认值
3. 系统会记住你的上次选择

### 2. 批量测试多个文件

虽然 lab 模式是单次运行，但可以快速重复：

```bash
# 运行第一个文件
narrio lab
# 按 Ctrl+C 快速取消，然后重新运行
narrio lab
# 选择下一个文件...
```

### 3. 使用别名简化命令

```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
alias nlab='narrio lab'
alias nrun='narrio run'
```

### 4. 组合使用 lab 和 tune

```bash
# 使用 lab 快速测试一个 style
narrio lab

# 如果效果好，使用 tune 生成多个 style
narrio tune --input your-file.md --styles "OpenAI,Anthropic,Google"
```

## 下一步

- 了解命令行模式：[how-to-run.md](../how-to-run.md)
- 端到端音频处理：[END-TO-END-AUDIO.md](./END-TO-END-AUDIO.md)
- Tune 批量模式：[TUNE.md](./TUNE.md)（如果存在）
