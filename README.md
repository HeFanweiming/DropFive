# 落五 DropFive

落五（DropFive）是一款基于 Python 与 tkinter 的智能五子棋桌面程序。项目采用清晰的领域模型、可替换的 AI 策略和独立的图形界面，目标是在保持规则正确、状态稳定的前提下提供双人对战、人机对战与可解释的搜索型 AI。

## 当前状态

仓库处于工程初始化阶段，目前没有可运行的游戏版本。首个可玩版本计划以 `v0.1.0` 发布。

## 计划功能

- 15×15 无禁手五子棋。
- 双人对战与人机对战。
- 简单、普通、困难三档 AI。
- Alpha-Beta 搜索与棋型评估。
- 悔棋、重新开始、落子提示和最后一手标记。
- 独立于界面的核心规则测试。

## 技术栈

- Python 3.11 或 3.12
- tkinter
- pytest
- Ruff

## 工程结构

```text
DropFive/
├─ .github/workflows/     # 持续集成
├─ docs/                  # 本项目专属设计与测试文档
├─ src/dropfive/          # 可安装的应用包
├─ tests/                 # 自动化测试
├─ CHANGELOG.md           # 版本变更记录
├─ CONTRIBUTING.md        # 开发与提交规范
└─ pyproject.toml         # 项目元数据与工具配置
```

## 本地开发

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

运行质量检查：

```powershell
ruff check .
ruff format --check .
pytest
```

## 版本规则

项目使用语义化版本 `MAJOR.MINOR.PATCH`：

- `MAJOR`：不兼容的规则、接口或存档格式变化。
- `MINOR`：新增一组完整功能，例如首个可玩版本。
- `PATCH`：向后兼容的错误修复。

每个可运行版本独立提交、更新 `CHANGELOG.md` 并创建 `vX.Y.Z` 标签。详细流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 仓库范围

本仓库只存放落五程序自身相关的源代码、测试、资源、设计和发布说明。课程计划表、报告模板、教学指导书及其他与程序无关的资料不纳入版本控制。

## 许可证

许可证尚未选定。在所有者明确选择许可证之前，本仓库内容不授予额外的复制或分发许可。
