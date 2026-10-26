"""开局、设置和关于我们三个模态窗口。"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from typing import Generic, TypeVar

from dropfive import __version__
from dropfive.ai.difficulty import Difficulty
from dropfive.controller.game_controller import GameMode
from dropfive.model.stone import Stone
from dropfive.settings import AiEngine, AppSettings
from dropfive.ui import theme
from dropfive.ui.options import (
    AI_ENGINE_OPTIONS,
    DIFFICULTY_OPTIONS,
    MODE_OPTIONS,
    SIDE_OPTIONS,
)
from dropfive.ui.widgets import ActionButton, SegmentedControl

_ResultT = TypeVar("_ResultT")
_PROJECT_URL = "https://github.com/HeFanweiming/DropFive"


class _Dialog(tk.Toplevel, Generic[_ResultT]):
    """统一处理居中、模态抓取、Esc 关闭和返回值。"""

    def __init__(
        self,
        parent: tk.Tk,
        *,
        title: str,
        size: tuple[int, int],
        transient: bool,
    ) -> None:
        """初始化隐藏窗口，等布局完成后再定位显示。"""
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        self.configure(background=theme.APP_BG)
        self.resizable(False, False)
        self.result: _ResultT | None = None
        self._size = size
        if transient:
            self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Escape>", lambda _event: self._cancel())

    def show(self) -> _ResultT | None:
        """居中显示窗口并阻塞调用方，直到用户确认或取消。"""
        self.update_idletasks()
        width, height = self._size
        x = max(0, (self.winfo_screenwidth() - width) // 2)
        y = max(0, (self.winfo_screenheight() - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.deiconify()
        self.grab_set()
        self.focus_force()
        self.wait_window(self)
        return self.result

    def _cancel(self) -> None:
        """关闭窗口并返回空结果。"""
        self.result = None
        self.destroy()


class GameSetupDialog(_Dialog[AppSettings]):
    """正式进入棋盘前的对局配置页。"""

    def __init__(self, parent: tk.Tk, settings: AppSettings) -> None:
        """用上次保存的设置作为开局默认值。"""
        super().__init__(
            parent,
            title="落五 · 开始对局",
            size=(560, 600),
            transient=False,
        )
        self._base_settings = settings
        self._mode = settings.mode
        self._difficulty = settings.difficulty
        self._human_stone = settings.human_stone
        self._build()

    def _build(self) -> None:
        """构建模式、难度、先后手和开始按钮。"""
        panel = tk.Frame(
            self,
            background=theme.SURFACE,
            highlightbackground=theme.BORDER,
            highlightthickness=1,
            padx=28,
            pady=26,
        )
        panel.pack(fill="both", expand=True, padx=24, pady=24)
        panel.columnconfigure(0, weight=1)

        tk.Label(
            panel,
            text="开始对局",
            background=theme.SURFACE,
            foreground=theme.INK,
            font=("Microsoft YaHei UI", 24, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            panel,
            text=f"落五 DropFive · v{__version__}",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Segoe UI", 9),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 22))

        row = 2
        row = self._add_control(
            panel,
            row,
            "模式",
            MODE_OPTIONS,
            self._mode.value,
            self._mode_changed,
        )
        row = self._add_control(
            panel,
            row,
            "难度",
            DIFFICULTY_OPTIONS,
            self._difficulty.value,
            self._difficulty_changed,
        )
        row = self._add_control(
            panel,
            row,
            "先后手",
            SIDE_OPTIONS,
            str(int(self._human_stone.value)),
            self._side_changed,
        )
        self.side_control = self._controls["先后手"]
        self.side_hint = tk.Label(
            panel,
            text="",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        )
        self.side_hint.grid(row=row, column=0, sticky="w", pady=(2, 18))
        row += 1

        self.start_button = ActionButton(
            panel,
            text="开始对局",
            icon="▶",
            command=self._start,
            background=theme.SURFACE,
            height=46,
        )
        self.start_button.grid(row=row, column=0, sticky="ew")
        row += 1
        ActionButton(
            panel,
            text="取消",
            icon="×",
            command=self._cancel,
            background=theme.SURFACE,
            variant="secondary",
            height=40,
        ).grid(row=row, column=0, sticky="ew", pady=(8, 0))

        self._refresh_side_state()

    def _add_control(
        self,
        parent: tk.Misc,
        row: int,
        label: str,
        options: list[tuple[str, str]],
        selected: str,
        command,
    ) -> int:
        """添加“标题 + 分段控件”表单行，并返回下一可用行号。"""
        tk.Label(
            parent,
            text=label,
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=row, column=0, sticky="w")
        control = SegmentedControl(
            parent,
            options=options,
            selected=selected,
            command=command,
            background=theme.SURFACE,
            height=38,
        )
        control.grid(row=row + 1, column=0, sticky="ew", pady=(5, 14))
        if not hasattr(self, "_controls"):
            self._controls: dict[str, SegmentedControl] = {}
        self._controls[label] = control
        return row + 2

    def _mode_changed(self, value: str) -> None:
        """切换模式并决定先后手控件是否可用。"""
        self._mode = GameMode(value)
        self._refresh_side_state()

    def _difficulty_changed(self, value: str) -> None:
        """更新本局难度。"""
        self._difficulty = Difficulty(value)

    def _side_changed(self, value: str) -> None:
        """更新玩家执黑或执白。"""
        self._human_stone = Stone(int(value))
        self._refresh_side_state()

    def _refresh_side_state(self) -> None:
        """双人模式隐藏先手选择；人机模式显示 AI 先后手说明。"""
        human_vs_ai = self._mode is GameMode.HUMAN_VS_AI
        self.side_control.set_enabled(human_vs_ai)
        self.side_hint.configure(
            text="你执黑先行"
            if human_vs_ai and self._human_stone is Stone.BLACK
            else "你执白后行，AI 先落子"
            if human_vs_ai
            else "双人模式黑方先手"
        )

    def _start(self) -> None:
        """生成不可变设置并关闭开局页。"""
        self.result = AppSettings(
            mode=self._mode,
            difficulty=self._difficulty,
            human_stone=self._human_stone,
            ai_engine=self._base_settings.ai_engine,
            deepseek_api_key=self._base_settings.deepseek_api_key,
        )
        self.destroy()


class SettingsDialog(_Dialog[AppSettings]):
    """编辑下次启动默认值的设置窗口。"""

    def __init__(
        self,
        parent: tk.Tk,
        settings: AppSettings,
        *,
        model_available: bool,
    ) -> None:
        """接收当前设置和 ONNX 可用状态。"""
        super().__init__(
            parent,
            title="落五 · 设置",
            size=(560, 720),
            transient=True,
        )
        self._settings = settings
        self._mode = settings.mode
        self._difficulty = settings.difficulty
        self._human_stone = settings.human_stone
        self._ai_engine = settings.ai_engine
        self._deepseek_api_key = settings.deepseek_api_key
        self._model_available = model_available
        self._build()

    def _build(self) -> None:
        """构建默认模式、难度、先后手和 AI 引擎表单。"""
        panel = tk.Frame(
            self,
            background=theme.SURFACE,
            highlightbackground=theme.BORDER,
            highlightthickness=1,
            padx=28,
            pady=26,
        )
        panel.pack(fill="both", expand=True, padx=24, pady=24)
        panel.columnconfigure(0, weight=1)

        tk.Label(
            panel,
            text="设置",
            background=theme.SURFACE,
            foreground=theme.INK,
            font=("Microsoft YaHei UI", 24, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            panel,
            text="保存后用于下次启动和开局",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 20))

        row = 2
        row = self._add_control(
            panel,
            row,
            "默认模式",
            MODE_OPTIONS,
            self._mode.value,
            self._mode_changed,
        )
        row = self._add_control(
            panel,
            row,
            "默认难度",
            DIFFICULTY_OPTIONS,
            self._difficulty.value,
            self._difficulty_changed,
        )
        row = self._add_control(
            panel,
            row,
            "默认先后手",
            SIDE_OPTIONS,
            str(int(self._human_stone.value)),
            self._side_changed,
        )
        self.side_control = self._controls["默认先后手"]
        row = self._add_control(
            panel,
            row,
            "AI 引擎",
            AI_ENGINE_OPTIONS,
            self._ai_engine.value,
            self._engine_changed,
        )
        self._api_key_frame = tk.Frame(panel, background=theme.SURFACE)
        self._api_key_frame.grid(row=row, column=0, sticky="ew", pady=(0, 8))
        self._api_key_frame.columnconfigure(0, weight=1)
        tk.Label(
            self._api_key_frame,
            text="DeepSeek API Key",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self._api_key_var = tk.StringVar(self, value=self._deepseek_api_key)
        tk.Entry(
            self._api_key_frame,
            textvariable=self._api_key_var,
            show="•",
            background=theme.SURFACE_ALT,
            foreground=theme.INK,
            insertbackground=theme.INK,
            relief="flat",
            highlightbackground=theme.BORDER,
            highlightcolor=theme.ACCENT,
            highlightthickness=1,
            font=("Consolas", 10),
        ).grid(row=1, column=0, sticky="ew", pady=(5, 0), ipady=7)
        tk.Label(
            self._api_key_frame,
            text="仅保存在本机；也可使用 DEEPSEEK_API_KEY 环境变量",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        row += 1

        self.engine_hint = tk.Label(
            panel,
            text="",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 8),
            anchor="w",
            wraplength=430,
        )
        self.engine_hint.grid(row=row, column=0, sticky="w", pady=(0, 16))
        row += 1

        ActionButton(
            panel,
            text="保存设置",
            icon="✓",
            command=self._save,
            background=theme.SURFACE,
            height=46,
        ).grid(row=row, column=0, sticky="ew")
        row += 1
        ActionButton(
            panel,
            text="取消",
            icon="×",
            command=self._cancel,
            background=theme.SURFACE,
            variant="secondary",
            height=40,
        ).grid(row=row, column=0, sticky="ew", pady=(8, 0))
        self._refresh_side_state()
        self._refresh_engine_state()

    def _add_control(
        self,
        parent: tk.Misc,
        row: int,
        label: str,
        options: list[tuple[str, str]],
        selected: str,
        command,
    ) -> int:
        """添加设置表单行。"""
        tk.Label(
            parent,
            text=label,
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=row, column=0, sticky="w")
        control = SegmentedControl(
            parent,
            options=options,
            selected=selected,
            command=command,
            background=theme.SURFACE,
            height=36,
        )
        control.grid(row=row + 1, column=0, sticky="ew", pady=(4, 10))
        if not hasattr(self, "_controls"):
            self._controls: dict[str, SegmentedControl] = {}
        self._controls[label] = control
        return row + 2

    def _mode_changed(self, value: str) -> None:
        self._mode = GameMode(value)
        self._refresh_side_state()

    def _difficulty_changed(self, value: str) -> None:
        self._difficulty = Difficulty(value)

    def _side_changed(self, value: str) -> None:
        self._human_stone = Stone(int(value))

    def _engine_changed(self, value: str) -> None:
        """切换本地 ONNX、本地 CPU 或 DeepSeek API。"""
        self._ai_engine = AiEngine(value)
        self._refresh_engine_state()

    def _refresh_engine_state(self) -> None:
        """根据引擎显示 API Key 字段并更新说明文字。"""
        if self._ai_engine is AiEngine.DEEPSEEK_API:
            self._api_key_frame.grid()
            hint = "当前棋盘会发送至 DeepSeek V4.1F；失败时回退本地 AI"
        else:
            self._api_key_frame.grid_remove()
            if self._ai_engine is AiEngine.LOCAL_ONNX:
                hint = (
                    "ONNX 模型已就绪，自动选择 GPU/CPU Provider"
                    if self._model_available
                    else "未检测到可用 ONNX 模型，将自动使用 CPU 搜索"
                )
            else:
                hint = "仅使用本地搜索，不发起网络请求"
        self.engine_hint.configure(text=hint)

    def _refresh_side_state(self) -> None:
        self.side_control.set_enabled(self._mode is GameMode.HUMAN_VS_AI)

    def _save(self) -> None:
        """生成新设置并由主窗口负责持久化。"""
        self.result = AppSettings(
            mode=self._mode,
            difficulty=self._difficulty,
            human_stone=self._human_stone,
            ai_engine=self._ai_engine,
            deepseek_api_key=self._api_key_var.get().strip(),
        )
        self.destroy()


class AboutDialog(_Dialog[None]):
    """展示版本、作者、项目地址和第三方模型信息。"""

    def __init__(self, parent: tk.Tk) -> None:
        """创建关于窗口。"""
        super().__init__(
            parent,
            title="落五 · 关于我们",
            size=(560, 500),
            transient=True,
        )
        self._build()

    def _build(self) -> None:
        """构建品牌介绍、技术信息和项目链接。"""
        panel = tk.Frame(
            self,
            background=theme.SURFACE,
            highlightbackground=theme.BORDER,
            highlightthickness=1,
            padx=30,
            pady=28,
        )
        panel.pack(fill="both", expand=True, padx=24, pady=24)
        panel.columnconfigure(0, weight=1)

        tk.Label(
            panel,
            text="落五 DropFive",
            background=theme.SURFACE,
            foreground=theme.INK,
            font=("Microsoft YaHei UI", 24, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            panel,
            text=f"Version {__version__}",
            background=theme.SURFACE,
            foreground=theme.ACCENT,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(4, 18))
        tk.Label(
            panel,
            text="一个面向年轻玩家的智能五子棋桌面程序。",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 10),
            anchor="w",
        ).grid(row=2, column=0, sticky="w")

        info = (
            "作者  HeFanweiming\n"
            "AI  Alpha-Beta · VCF · ONNX / DeepSeek V4.1F 可选增强\n"
            "模型  whyb/Gomoku-AI · BSD-3-Clause\n"
            "界面  Python + tkinter"
        )
        tk.Label(
            panel,
            text=info,
            background=theme.SURFACE_ALT,
            foreground=theme.INK,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
            padx=16,
            pady=14,
        ).grid(row=3, column=0, sticky="ew", pady=(22, 16))

        link = tk.Label(
            panel,
            text=_PROJECT_URL,
            background=theme.SURFACE,
            foreground=theme.ACCENT,
            font=("Segoe UI", 9, "underline"),
            cursor="hand2",
            anchor="w",
        )
        link.grid(row=4, column=0, sticky="w")
        link.bind("<Button-1>", lambda _event: webbrowser.open(_PROJECT_URL))

        ActionButton(
            panel,
            text="关闭",
            icon="×",
            command=self._cancel,
            background=theme.SURFACE,
            variant="secondary",
            height=42,
        ).grid(row=5, column=0, sticky="ew", pady=(28, 0))
