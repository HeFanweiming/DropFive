# 落五 DropFive

落五（DropFive）是一款基于 Python 与 tkinter 的智能五子棋桌面程序。项目采用清晰的领域模型、可替换的 AI 策略和独立的图形界面，目标是在保持规则正确、状态稳定的前提下提供双人对战、人机对战与可解释的搜索型 AI。

## 当前状态

`v0.3.0` 已补齐双人对战、人机对战、四档 AI 和落子提示，并完成现代风格界面重构。

## 已实现功能

- 15×15 无禁手五子棋。
- 双人对战、人机对战和黑白回合切换。
- 简单、普通、困难、大师四档搜索型 AI。
- Alpha-Beta 搜索、棋型评分、立即获胜与立即封堵。
- 断点四、开放四、双威胁与 VCF 强制胜搜索。
- Zobrist 置换表、主变优先排序和更深迭代搜索。
- 防守型强制搜索与大师档五秒深度搜索。
- 后台 AI 计算、过期结果保护和 AI 回合输入锁定。
- 落子提示与人机模式双步悔棋。
- 横、竖及两条斜线方向的胜负判断。
- 满盘和棋判断。
- 重新开始与悔棋。
- 全窗口自适应的棋子、坐标和棋盘细节，悬停预览、最后一手标记和胜利棋线高亮。
- 现代浅色视觉系统、自绘操作按钮和响应式对局面板。
- 独立于界面的核心规则与控制器测试。

## 后续计划

- 可选 ONNX 模型增强，保持为离线、非必需能力。
- 更丰富的战术基准集和棋力对照测试。

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
