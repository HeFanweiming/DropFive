# 落五 DropFive

落五（DropFive）是一款基于 Python 与 tkinter 的智能五子棋桌面程序。项目采用清晰的领域模型、可替换的 AI 策略和独立的图形界面，目标是在保持规则正确、状态稳定的前提下提供双人对战、人机对战与可解释的搜索型 AI。

## 当前状态

`v0.1.0` 提供可运行的双人对战版本。人机对战、三档 AI 和提示功能将在后续版本加入。

## 已实现功能

- 15×15 无禁手五子棋。
- 双人对战和黑白回合切换。
- 横、竖及两条斜线方向的胜负判断。
- 满盘和棋判断。
- 重新开始与悔棋。
- 悬停预览、最后一手标记和状态提示。
- 独立于界面的核心规则与控制器测试。

## 后续计划

- 人机对战与简单、普通、困难三档 AI。
- Alpha-Beta 搜索、棋型评估和落子提示。
- AI 搜索指标与战术测试集。

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

启动游戏：

```powershell
python -m dropfive
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
