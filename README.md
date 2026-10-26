# 落五 DropFive

落五（DropFive）是一款基于 Python 与 tkinter 的智能五子棋桌面程序。项目采用清晰的领域模型、可替换的 AI 策略和独立的图形界面，目标是在保持规则正确、状态稳定的前提下提供双人对战、人机对战与可解释的搜索型 AI。

## 当前状态

`v0.6.0` 已补齐开局设置、可选 ONNX 增强，并支持通过 DeepSeek API 进行人机对弈。

## 已实现功能

- 15×15 无禁手五子棋。
- 双人对战、人机对战和黑白回合切换。
- 开局前选择先手执黑或后手执白，AI 先手时自动落子。
- 保存默认模式、难度、先后手和本地/DeepSeek API 引擎设置。
- 设置窗口与关于我们页面。
- 简单、普通、困难、大师四档搜索型 AI。
- Alpha-Beta 搜索、棋型评分、立即获胜与立即封堵。
- 断点四、开放四、双威胁与 VCF 强制胜搜索。
- Zobrist 置换表、主变优先排序和更深迭代搜索。
- 防守型强制搜索与大师档五秒深度搜索。
- 后台 AI 计算、过期结果保护和 AI 回合输入锁定。
- 可选 ONNX 策略先验、GPU Provider 自动检测和 CPU 回退。
- DeepSeek Chat Completions API 人机对弈与 API Key 设置。
- API 失败时自动使用本地 AI 完成当前回合。
- 落子提示与人机模式双步悔棋。
- 横、竖及两条斜线方向的胜负判断。
- 满盘和棋判断。
- 重新开始与悔棋。
- 全窗口自适应的棋子、坐标和棋盘细节，悬停预览、最后一手标记和胜利棋线高亮。
- 现代浅色视觉系统、自绘操作按钮和响应式对局面板。
- 独立于界面的核心规则与控制器测试。

## 后续计划

- 更丰富的战术基准集和棋力对照测试。
- ONNX 模型与纯搜索棋力的长期对照评估。

## 技术栈

- Python 3.11 或 3.12
- tkinter
- onnxruntime（可选）
- DeepSeek API（可选，需网络和 API Key）
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

可选 ONNX 增强：

```powershell
python -m pip install -e ".[onnx]"
```

使用该命令时需要特殊的网络环境，或者向AI询问替换命令为国内镜像版本

将兼容模型放入 `models/` 即可自动启用。模型文件不会提交到 Git；Provider、输入输出格式和 GPU 安装方式见 [models/README.md](models/README.md)。

## DeepSeek API

在设置窗口选择 `V4.1F`（DeepSeek-V4.1-Flash），填写 API Key 后即可进行人机对弈。也可以不保存 Key，改用环境变量：

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."
```

默认使用官方 `https://api.deepseek.com/chat/completions` 和 `deepseek-flash` 模型（DeepSeek-V4.1-Flash），并关闭思考模式以快速返回落子 JSON。选择 API 引擎时，当前棋盘局面和执子方会发送给 DeepSeek。API Key 只保存在本机设置文件中，不进入源码、日志或 Git 提交；API 不可用时会自动回退到本地 AI。

设置页还提供 DeepSeek 失败处理选项：

- `本地回退`：API 失败时自动用本地 AI 完成当前回合。
- `仅报错`：不运行任何本地备用落子，直接显示完整 API 错误，适合单独测试 API。
DeepSeek 请求使用棋盘上的 A–O/1–15 坐标，并通过严格工具调用把可返回坐标限制为动态生成的合法落点枚举。若仍返回越界或已占用位置，会携带错误原因自动纠错重试一次。

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
<img width="18" height="18" alt="download" src="https://github.com/user-attachments/assets/5cadfa55-1dec-4159-9b69-3cd3845b73bd" />


## 许可证

本项目源代码采用 [MIT License](LICENSE)。

可选的 ONNX 模型来自 `whyb/Gomoku-AI`，其模型和上游内容继续遵守 BSD-3-Clause 许可证。相关声明保存在 [models/LICENSE-whyb-Gomoku-AI.txt](models/LICENSE-whyb-Gomoku-AI.txt)。
