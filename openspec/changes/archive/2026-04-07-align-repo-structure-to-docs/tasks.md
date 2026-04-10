## 1. 目录结构对齐（不破坏可运行）

- [x] 1.1 新增 canonical 顶层目录：assets/ content/ exports/ legacy/ src/（先落地空目录与最小占位文件，确保可提交与可扫描）
- [x] 1.2 将现有 `process/prompt` 与 `process/styles` 迁移到 `assets/`（保留 legacy 只读兼容入口）
- [x] 1.3 将现有 `input/` 迁移到 `content/`（article → content/sources/article，podcast transcript → content/transcripts）
- [x] 1.4 将“可分享结果”的落点定义为 `exports/` 并建立最小写入流程（保留 `.narrio/workbench` 作为运行产物根目录）

## 2. 路径解析与资源发现统一

- [x] 2.1 增加统一路径解析模块（canonical 优先 + legacy 兜底）：sources/prompts/styles/reference image
- [x] 2.2 更新 `list_sources/list_styles` 与 markdown 解析逻辑，改为以 `content/` 与 `assets/` 为主
- [x] 2.3 为 legacy 路径添加低优先级候选与显式兼容策略（仅用于迁移期）
- [x] 2.4 为路径解析与资源发现增加单元测试覆盖（含 canonical/legacy 优先级场景）

## 3. 清理原型残留与迁移边界

- [x] 3.1 将遗留脚本与历史原型目录收敛到 `legacy/`（仅保留必要兼容入口）
- [x] 3.2 移除仓库根目录下的历史临时文件与不再使用的原型外壳目录
- [x] 3.3 在代码中集中替换硬编码路径（例如 legacy 常量、默认路径、脚本相对路径）

## 4. `src/` 布局迁移与打包入口稳定

- [x] 4.1 将现有 `narrio/` 包迁移到 `src/narrio/` 并更新 `pyproject.toml` 的 setuptools 配置（package_dir、packages 发现等）
- [x] 4.2 确保 `python -m narrio` 与 `narrio` console script 入口保持不变
- [x] 4.3 更新测试发现与导入路径，确保 `pytest` 可运行

## 5. 验证与回归保护

- [x] 5.1 运行 `python -m narrio --help`、dry-run、`python -m compileall` 验证最小可运行性
- [x] 5.2 运行测试套件并补齐结构对齐相关的回归用例
- [x] 5.3 补充一份迁移前后路径映射的验收清单（以代码/测试可验证为准）
