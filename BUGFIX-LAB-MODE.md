# Bug 修复：Lab 模式 from-audio 阶段错误

## 问题描述

当在 Lab 模式中选择 `from-audio` (从音频文件开始) 时，系统报错：

```
ValueError: 从中间阶段重跑时必须显式提供 --reuse-from-run
```

## 错误原因

`resolve_resume_paths()` 函数只检查了 `from-source` 阶段，没有考虑新增的 `from-audio` 阶段。导致系统误判 `from-audio` 需要提供 `reuse_from_run` 参数。

### 错误代码

```python
def resolve_resume_paths(request: ExperimentRequest) -> Path | None:
    if request.start_stage == "from-source":
        return None
    if request.reuse_from_run:
        return Path(request.reuse_from_run).expanduser().resolve()
    raise ValueError("从中间阶段重跑时必须显式提供 --reuse-from-run")
```

## 修复方案

### 1. 主要修复：更新 `resolve_resume_paths()` 函数

```python
def resolve_resume_paths(request: ExperimentRequest) -> Path | None:
    # Stages that start from the beginning don't need resume paths
    if request.start_stage in ("from-audio", "from-source"):
        return None
    # For resume stages (from-chunk, from-editorial), require reuse_from_run
    if request.reuse_from_run:
        return Path(request.reuse_from_run).expanduser().resolve()
    raise ValueError("从中间阶段重跑时必须显式提供 --reuse-from-run")
```

**改动**：
- 将 `from-source` 单独检查改为检查 `("from-audio", "from-source")` 元组
- 添加注释说明哪些阶段不需要 resume paths

### 2. 次要优化：简化提示文本

**修复前**：
```python
render_workers_str = ask_optional_text("并行渲染 worker 数（留空表示自动，上限 5）")
max_pages_str = ask_optional_text("图片生成数量上限（留空表示全部生成）")
```

显示效果：
```
并行渲染 worker 数（留空表示自动，上限 5）（留空表示默认）: 
图片生成数量上限（留空表示全部生成）（留空表示默认）: 
```

**修复后**：
```python
render_workers_str = ask_optional_text("并行渲染 worker 数 (上限 5)")
max_pages_str = ask_optional_text("图片生成数量上限")
```

显示效果：
```
并行渲染 worker 数 (上限 5)（留空表示默认）: 
图片生成数量上限（留空表示默认）: 
```

## 测试验证

```bash
# 测试 from-audio (应该返回 None，不报错)
$ python -c "
from src.narrio.experiment import resolve_resume_paths, ExperimentRequest
req = ExperimentRequest(
    content_type='podcast',
    markdown='test.md',
    start_stage='from-audio',
    audio_file='test.mp3'
)
print('Result:', resolve_resume_paths(req))
"
# 输出: Result: None

# 测试完整流程
$ narrio lab
选择内容类型> podcast
选择起始阶段> from-audio (从音频文件开始)
选择音频文件> your-podcast.mp3
...
# 应该正常运行，不再报错
```

## 涉及文件

- `src/narrio/experiment.py` - 修复 `resolve_resume_paths()` 函数
- `src/narrio/cli.py` - 优化提示文本

## 影响范围

### 受影响功能
- ✅ Lab 模式 - 从音频开始
- ✅ 命令行模式 - `narrio run --audio-file`

### 不受影响功能
- ✅ 从 markdown 开始 (from-source)
- ✅ 从 chunk 恢复 (from-chunk)
- ✅ 从 editorial 恢复 (from-editorial)

## 相关 Issue

此修复解决了在实现端到端音频处理功能时引入的回归问题。

## 部署说明

此修复已合并到主分支，无需额外部署步骤。

## 验证清单

- [x] `from-audio` 阶段不再报错
- [x] `from-source` 阶段正常工作
- [x] `from-chunk` 需要 `reuse_from_run` (预期行为)
- [x] `from-editorial` 需要 `reuse_from_run` (预期行为)
- [x] 提示文本不再重复语义
- [x] 单元测试通过

## 后续优化建议

1. 添加单元测试覆盖所有 `start_stage` 值
2. 考虑将 `start_stage` 定义为枚举类型，避免字符串硬编码
3. 统一所有提示文本的格式和风格
