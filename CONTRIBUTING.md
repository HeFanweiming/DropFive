# 开发与提交规范

## 分支与提交

- `main` 分支始终保持可运行并通过全部质量检查。
- 功能开发使用短生命周期分支，例如 `feat/core-rules`。
- 提交信息采用 Conventional Commits，例如：
  - `feat: add board and win-checking rules`
  - `fix: reject moves after game completion`
  - `docs: describe AI search boundaries`
  - `chore: configure package metadata`
- 一个提交只解决一个内聚问题，不混入无关格式化或课程资料。

## 版本与发布

1. 使用语义化版本 `MAJOR.MINOR.PATCH`。
2. 每个可运行版本更新 `CHANGELOG.md`。
3. 完成 Ruff 检查、自动化测试和手工冒烟测试。
4. 独立提交版本变更，例如 `chore(release): prepare v0.1.0`。
5. 创建带说明的 Git 标签 `vX.Y.Z` 并推送到 GitHub。
6. 重要版本可在 GitHub Releases 中补充运行说明和已知限制。

## 质量门槛

- 核心规则和 AI 逻辑必须有自动化测试。
- 非法操作必须验证游戏状态完全不变。
- UI 不直接修改领域模型内部数组。
- AI 搜索不得污染正在进行的棋局。
- 新依赖必须说明用途、许可证和回退方案。
