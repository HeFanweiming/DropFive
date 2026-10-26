"""落五主窗口：组合棋盘、控制栏、设置和后台 AI 搜索。"""

import contextlib
import ctypes
import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox

from dropfive import __version__
from dropfive.ai.deepseek import DeepSeekError, DeepSeekStrategy
from dropfive.ai.difficulty import Difficulty
from dropfive.ai.onnx_policy import load_optional_model
from dropfive.ai.search import SearchResult
from dropfive.ai.strategy import GomokuAI
from dropfive.controller.game_controller import (
    ActionError,
    ActionResult,
    GameController,
    GameMode,
    GameView,
    SearchPurpose,
    SearchRequest,
)
from dropfive.model.game import GameResult
from dropfive.model.history import Move
from dropfive.model.stone import Stone
from dropfive.settings import AiEngine, AppSettings, load_settings, save_settings
from dropfive.ui import theme
from dropfive.ui.board_canvas import BoardCanvas
from dropfive.ui.dialogs import AboutDialog, GameSetupDialog, SettingsDialog
from dropfive.ui.options import (
    DIFFICULTY_LABELS,
    DIFFICULTY_OPTIONS,
    MODE_LABELS,
    MODE_OPTIONS,
)
from dropfive.ui.widgets import ActionButton, SegmentedControl

_BOARD_SIZE = 15
_BOARD_GAP = 22
_MIN_BOARD_SIZE = 420
_SIDEBAR_WIDTH = 296

_STONE_LABELS = {
    Stone.BLACK: "黑方",
    Stone.WHITE: "白方",
}

_ERROR_MESSAGES = {
    ActionError.OUT_OF_BOUNDS: "该位置不在棋盘内。",
    ActionError.OCCUPIED: "该位置已有棋子。",
    ActionError.GAME_OVER: "本局已经结束。",
    ActionError.NO_UNDO: "当前没有可悔的棋。",
    ActionError.NOT_YOUR_TURN: "请等待当前回合结束。",
    ActionError.STALE_REQUEST: "上一项计算已经失效。",
}


def _position_label(move: Move | None) -> str:
    """把落子坐标格式化为 ``H8`` 这类人类可读标签。"""
    if move is None:
        return "—"
    return _cell_label(move.row, move.col)


def _cell_label(row: int, col: int) -> str:
    """把零基行列转换为字母列 + 一基行号。"""
    return f"{chr(ord('A') + col)}{row + 1}"


@dataclass(frozen=True, slots=True)
class _SearchCompletion:
    """后台线程投递回主线程的搜索结果。

    完成对象携带启动时 token，主线程只有在 token 仍匹配当前搜索时才应用，
    从而丢弃重开或切换模式前产生的旧结果。
    """

    token: int
    request: SearchRequest
    result: SearchResult | None
    error: str | None


class DropFiveWindow:
    """tkinter 视图与用户交互协调器。

    UI 只读取 ``GameView`` 和搜索完成事件，不直接修改棋盘数组；AI 计算在
    短生命周期线程中执行，搜索结果通过队列回到 Tk 主线程应用。
    """

    def __init__(
        self,
        root: tk.Tk,
        controller: GameController | None = None,
        settings: AppSettings | None = None,
    ) -> None:
        """创建主窗口，并加载可选 ONNX 模型与用户设置。"""
        self.root = root
        self.controller = controller or GameController(_BOARD_SIZE)
        self.settings = settings or AppSettings()
        self._message_after: str | None = None
        self._last_board_side = 0

        # 一次只允许一个 AI/提示任务；token 用于识别已过期的后台结果。
        self._active_search: SearchRequest | None = None
        self._search_token = 0
        self._search_queue: queue.Queue[_SearchCompletion] = queue.Queue()
        self._poll_after: str | None = None
        self._hint_cell: tuple[int, int] | None = None
        self._closed = False
        # ONNX 是可选项，加载失败不影响本地搜索和 UI 启动。
        self.policy_model, self._model_error = (
            load_optional_model() if self.settings.ai_engine.use_onnx else (None, None)
        )

        self.root.title("落五 DropFive")
        self.root.geometry("1180x820")
        self.root.minsize(1000, 740)
        self.root.configure(background=theme.APP_BG)

        self._build_layout()
        self.root.bind("<Control-z>", self._undo_from_keyboard)
        self.root.bind("<Control-n>", self._restart_from_keyboard)
        self.root.bind("<Control-h>", self._hint_from_keyboard)
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh()
        # 队列轮询固定在 Tk 主线程运行，后台线程只负责 put，不触碰控件。
        self._poll_after = self.root.after(50, self._poll_search_results)
        # 玩家选择执白时，AI 执黑并需要在开局后自动先走。
        self.root.after(120, self._start_ai_if_needed)

    def _build_layout(self) -> None:
        """搭建顶部品牌区、居中的棋盘和右侧对局面板。"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        content = tk.Frame(
            self.root,
            background=theme.APP_BG,
            padx=32,
            pady=24,
        )
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(1, weight=1)

        self._build_header(content)

        body = tk.Frame(content, background=theme.APP_BG)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.columnconfigure(2, weight=0)
        body.columnconfigure(3, weight=1)
        body.rowconfigure(0, weight=1)

        self.board_canvas = BoardCanvas(
            body,
            board_size=_BOARD_SIZE,
            on_move=self._handle_move,
        )
        self.board_canvas.configure(width=680, height=680)
        self.board_canvas.grid(
            row=0,
            column=1,
            sticky="ns",
            padx=(0, _BOARD_GAP),
        )

        self.sidebar = tk.Frame(
            body,
            background=theme.SURFACE,
            highlightbackground=theme.BORDER,
            highlightthickness=1,
            padx=24,
            pady=22,
        )
        self.sidebar.grid(row=0, column=2, sticky="ns")
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(9, weight=1)
        body.bind("<Configure>", self._handle_body_resize)

        self._build_sidebar()

    def _build_header(self, parent: tk.Misc) -> None:
        """创建品牌标题、模式标签和版本号。"""
        header = tk.Frame(parent, background=theme.APP_BG)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.columnconfigure(2, weight=1)

        tk.Label(
            header,
            text="落五",
            background=theme.APP_BG,
            foreground=theme.HEADER_TEXT,
            font=("Microsoft YaHei UI", 30, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="●  GOMOKU",
            background=theme.APP_BG,
            foreground=theme.HEADER_MUTED,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=1, sticky="w", padx=(14, 0), pady=(17, 0))

        self.mode_chip = tk.Label(
            header,
            text=MODE_LABELS[self.controller.view().mode],
            background=theme.HEADER_CHIP,
            foreground=theme.HEADER_CHIP_TEXT,
            font=("Microsoft YaHei UI", 9),
            padx=13,
            pady=7,
            highlightbackground=theme.BORDER,
            highlightthickness=1,
        )
        self.mode_chip.grid(row=0, column=3, sticky="e", padx=(0, 12))
        tk.Label(
            header,
            text=f"v{__version__}",
            background=theme.APP_BG,
            foreground=theme.HEADER_MUTED,
            font=("Segoe UI", 9),
        ).grid(row=0, column=4, sticky="e")

    def _build_sidebar(self) -> None:
        """创建模式、难度、状态、统计、操作按钮和辅助入口。"""
        view = self.controller.view()

        controls = tk.Frame(self.sidebar, background=theme.SURFACE)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        tk.Label(
            controls,
            text="模式",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=(0, 6))

        self.mode_control = SegmentedControl(
            controls,
            options=MODE_OPTIONS,
            selected=view.mode.value,
            command=self._handle_mode_change,
            background=theme.SURFACE,
            width=190,
        )
        self.mode_control.grid(row=0, column=1, sticky="ew", pady=(0, 6))

        tk.Label(
            controls,
            text="难度",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=(0, 4))

        self.difficulty_control = SegmentedControl(
            controls,
            options=DIFFICULTY_OPTIONS,
            selected=view.difficulty.value,
            command=self._handle_difficulty_change,
            background=theme.SURFACE,
            width=220,
        )
        self.difficulty_control.grid(row=1, column=1, sticky="ew", pady=(0, 4))

        tk.Frame(
            self.sidebar,
            background=theme.BORDER,
            height=1,
        ).grid(row=1, column=0, sticky="ew", pady=10)

        status_frame = tk.Frame(self.sidebar, background=theme.SURFACE)
        status_frame.grid(row=2, column=0, sticky="ew")
        status_frame.columnconfigure(1, weight=1)

        self.turn_badge = tk.Canvas(
            status_frame,
            width=42,
            height=42,
            background=theme.SURFACE,
            highlightthickness=0,
        )
        self.turn_badge.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))

        self.status_label = tk.Label(
            status_frame,
            text="",
            background=theme.SURFACE,
            foreground=theme.INK,
            font=("Microsoft YaHei UI", 19, "bold"),
            anchor="w",
            justify="left",
        )
        self.status_label.grid(row=0, column=1, sticky="ew")

        self.status_note = tk.Label(
            status_frame,
            text="",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        )
        self.status_note.grid(row=1, column=1, sticky="ew", pady=(2, 0))

        stats_frame = tk.Frame(self.sidebar, background=theme.SURFACE)
        stats_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)

        tk.Label(
            stats_frame,
            text="手数",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            stats_frame,
            text="最近落子",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(18, 0))

        self.move_count_label = tk.Label(
            stats_frame,
            text="0",
            background=theme.SURFACE,
            foreground=theme.INK,
            font=("Segoe UI", 15, "bold"),
            anchor="w",
        )
        self.move_count_label.grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.last_move_label = tk.Label(
            stats_frame,
            text="—",
            background=theme.SURFACE,
            foreground=theme.INK,
            font=("Segoe UI", 15, "bold"),
            anchor="w",
        )
        self.last_move_label.grid(row=1, column=1, sticky="w", padx=(18, 0), pady=(3, 0))

        tk.Frame(
            self.sidebar,
            background=theme.BORDER,
            height=1,
        ).grid(row=4, column=0, sticky="ew", pady=10)

        self.new_button = ActionButton(
            self.sidebar,
            text="重新开始",
            icon="↻",
            command=self._restart,
            background=theme.SURFACE,
            height=44,
        )
        self.new_button.grid(row=5, column=0, sticky="ew")

        action_row = tk.Frame(self.sidebar, background=theme.SURFACE)
        action_row.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)

        self.undo_button = ActionButton(
            action_row,
            text="悔棋",
            icon="↶",
            command=self._undo,
            background=theme.SURFACE,
            variant="secondary",
            width=110,
            height=44,
        )
        self.undo_button.grid(row=0, column=0, sticky="ew")

        self.hint_button = ActionButton(
            action_row,
            text="提示落子",
            icon="✦",
            command=self._request_hint,
            background=theme.SURFACE,
            variant="secondary",
            width=110,
            height=44,
        )
        self.hint_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.message_label = tk.Label(
            self.sidebar,
            text="",
            background=theme.SURFACE,
            foreground=theme.MESSAGE,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
            wraplength=218,
            height=1,
        )
        self.message_label.grid(row=7, column=0, sticky="ew", pady=(6, 0))

        footer = tk.Frame(self.sidebar, background=theme.SURFACE)
        footer.grid(row=10, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        tk.Label(
            footer,
            text="15 × 15",
            background=theme.SURFACE_ALT,
            foreground=theme.MUTED,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=4,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            footer,
            text="无禁手",
            background=theme.SURFACE_ALT,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 8),
            padx=8,
            pady=4,
        ).grid(row=0, column=1, sticky="e")
        self.engine_label = tk.Label(
            footer,
            text=self._engine_label_text(),
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.engine_label.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(4, 0),
        )
        utility = tk.Frame(footer, background=theme.SURFACE)
        utility.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 0))
        utility.columnconfigure(0, weight=1)
        utility.columnconfigure(1, weight=1)
        ActionButton(
            utility,
            text="设置",
            icon="⚙",
            command=self._open_settings,
            background=theme.SURFACE,
            variant="secondary",
            width=105,
            height=34,
        ).grid(row=0, column=0, sticky="ew")
        ActionButton(
            utility,
            text="关于",
            icon="ⓘ",
            command=self._open_about,
            background=theme.SURFACE,
            variant="secondary",
            width=105,
            height=34,
        ).grid(row=0, column=1, sticky="ew", padx=(8, 0))

    def _handle_body_resize(self, event: tk.Event) -> None:
        """保持棋盘为正方形，并让“棋盘 + 侧栏”整体居中。"""
        available_width = event.width - _SIDEBAR_WIDTH - _BOARD_GAP
        side = max(_MIN_BOARD_SIZE, min(event.height, available_width))
        if side == self._last_board_side:
            return
        self._last_board_side = side
        self.board_canvas.configure(width=side, height=side)

    def _handle_move(self, row: int, col: int) -> None:
        """接收棋盘点击，执行人类落子并根据回合启动 AI。"""
        if self._active_search is not None:
            return
        self._hint_cell = None
        result = self.controller.play(row, col)
        self._handle_action_result(result)
        self._refresh()
        if result.ok and self.controller.view().is_ai_turn:
            self._begin_search(SearchPurpose.AI_MOVE)

    def _undo(self) -> None:
        """处理悔棋；AI 搜索中禁止操作以避免状态竞争。"""
        if self._active_search is not None:
            self._show_message("请等待当前计算结束。")
            return
        self._hint_cell = None
        result = self.controller.undo()
        self._handle_action_result(result)
        self._refresh()
        if result.ok:
            self._start_ai_if_needed()

    def _restart(self) -> None:
        """取消旧搜索、清空棋局，并在 AI 先手时自动开始新回合。"""
        self._cancel_search()
        self._hint_cell = None
        result = self.controller.restart()
        self._handle_action_result(result)
        self._refresh()
        self._start_ai_if_needed()

    def _request_hint(self) -> None:
        """启动提示搜索；提示只高亮位置，不自动落子。"""
        if self._active_search is not None:
            return
        self._hint_cell = None
        self._begin_search(SearchPurpose.HINT)

    def _handle_mode_change(self, value: str) -> None:
        """切换双人/人机模式；进行中的棋局需要用户确认后重置。"""
        mode = GameMode(value)
        current = self.controller.view()
        if mode is current.mode:
            return
        if current.move_count > 0 and not messagebox.askyesno(
            "切换模式",
            "切换模式将开始新对局，是否继续？",
            parent=self.root,
        ):
            self.mode_control.set_selected(current.mode.value)
            return

        self._cancel_search()
        self._hint_cell = None
        self.controller.set_mode(mode)
        self._clear_message()
        self._refresh()
        self._start_ai_if_needed()

    def _handle_difficulty_change(self, value: str) -> None:
        """更新当前会话难度，并使已失效的提示结果不再适用。"""
        self._cancel_search()
        self._hint_cell = None
        self.controller.set_difficulty(Difficulty(value))
        self._clear_message()
        self._refresh()

    def _begin_search(self, purpose: SearchPurpose) -> None:
        """创建搜索请求、锁定界面并安排后台任务启动。"""
        request = self.controller.make_search_request(purpose)
        if request is None or self._active_search is not None:
            return

        self._search_token += 1
        self._active_search = request
        self._refresh()
        self.root.after(30, self._launch_search, self._search_token, request)

    def _start_ai_if_needed(self) -> None:
        """在 AI 回合且无任务运行时自动发起落子搜索。"""
        if self._active_search is None and self.controller.view().is_ai_turn:
            self._begin_search(SearchPurpose.AI_MOVE)

    def _launch_search(self, token: int, request: SearchRequest) -> None:
        """在 token 仍有效时启动守护线程。"""
        if token != self._search_token or self._closed:
            return
        worker = threading.Thread(
            target=self._run_search,
            args=(token, request),
            daemon=True,
        )
        worker.start()

    def _run_search(self, token: int, request: SearchRequest) -> None:
        """后台线程入口：只计算并投递结果，绝不访问 tkinter。"""
        try:
            notice = None
            if self.settings.ai_engine is AiEngine.DEEPSEEK_API:
                api_key = self.settings.deepseek_api_key.strip() or os.environ.get(
                    "DEEPSEEK_API_KEY",
                    "",
                )
                try:
                    result = DeepSeekStrategy(api_key).choose_move(
                        request.board,
                        request.stone,
                    )
                except DeepSeekError as exc:
                    if not self.settings.allow_local_fallback:
                        raise
                    # API 失败时继续完成本回合，避免人机棋局永久停在 AI 回合。
                    result = GomokuAI(Difficulty.MEDIUM).choose_move(
                        request.board,
                        request.stone,
                    )
                    notice = f"DeepSeek V4.1F 调用失败，已使用本地 AI：{exc}"
            else:
                result = GomokuAI(
                    request.difficulty,
                    policy_model=self.policy_model,
                ).choose_move(request.board, request.stone)
        except Exception as exc:  # The worker boundary must report failures to the UI.
            completion = _SearchCompletion(
                token=token,
                request=request,
                result=None,
                error=str(exc),
            )
        else:
            completion = _SearchCompletion(
                token=token,
                request=request,
                result=result,
                error=notice,
            )
        self._search_queue.put(completion)

    def _poll_search_results(self) -> None:
        """在 Tk 主线程消费搜索结果，并定期继续轮询。"""
        self._poll_after = None
        if self._closed:
            return

        while True:
            try:
                completion = self._search_queue.get_nowait()
            except queue.Empty:
                break
            if (
                completion.token != self._search_token
                or self._active_search is None
                or completion.request.purpose is not self._active_search.purpose
                or completion.request.game_id != self._active_search.game_id
            ):
                continue
            self._active_search = None
            self._handle_search_completion(completion)
            self._refresh()

        self._poll_after = self.root.after(50, self._poll_search_results)

    def _handle_search_completion(self, completion: _SearchCompletion) -> None:
        """应用 AI 落子或提示结果；异常时回退到备用合法点。"""
        request = completion.request
        result = completion.result
        notice = completion.error
        if result is None or result.move is None:
            if request.purpose is SearchPurpose.AI_MOVE:
                if (
                    self.settings.ai_engine is AiEngine.DEEPSEEK_API
                    and not self.settings.allow_local_fallback
                ):
                    message = notice or "DeepSeek V4.1F 调用失败。"
                    self._show_message(message)
                    messagebox.showerror(
                        "DeepSeek V4.1F",
                        message,
                        parent=self.root,
                    )
                    return
                fallback = self.controller.apply_ai_fallback(request.game_id)
                message = "AI 搜索异常，已使用备用落点。" if fallback.ok else "AI 无法完成本回合。"
                self._show_message(message)
            else:
                message = notice or "暂时无法生成提示。"
                self._show_message(message)
                if (
                    self.settings.ai_engine is AiEngine.DEEPSEEK_API
                    and not self.settings.allow_local_fallback
                ):
                    messagebox.showerror(
                        "DeepSeek V4.1F",
                        message,
                        parent=self.root,
                    )
            return

        row, col = result.move
        if request.purpose is SearchPurpose.AI_MOVE:
            action = self.controller.play_ai_move(row, col, request.game_id)
            if not action.ok and action.error is not ActionError.STALE_REQUEST:
                fallback = self.controller.apply_ai_fallback(request.game_id)
                if not fallback.ok:
                    self._show_message("AI 无法完成本回合。")
            elif action.ok and notice:
                self._show_message(notice)
            return

        self._hint_cell = (row, col)
        self._show_message(
            f"{notice}；推荐落点 {_cell_label(row, col)}"
            if notice
            else f"推荐落点 {_cell_label(row, col)}"
        )

    def _cancel_search(self) -> None:
        """推进 token，使任何仍在运行的后台结果自动失效。"""
        self._search_token += 1
        self._active_search = None

    def _handle_action_result(self, result: ActionResult) -> None:
        """把控制器错误码转换为用户提示。"""
        if result.ok:
            self._clear_message()
            return
        if result.error is not None:
            self._show_message(_ERROR_MESSAGES[result.error])

    def _refresh(self) -> None:
        """生成棋局快照并同步棋盘、搜索锁定和侧栏状态。"""
        view = self.controller.view()
        self.board_canvas.set_state(
            view.board,
            view.last_move,
            view.current_stone,
            interactive=view.can_human_play and self._active_search is None,
            winning_cells=view.winning_cells,
            hint_cell=self._hint_cell,
        )
        self._update_sidebar(view)

    def _update_sidebar(self, view: GameView) -> None:
        """按当前模式、搜索阶段和结果更新侧栏信息和按钮可用性。"""
        busy = self._active_search is not None
        purpose = self._active_search.purpose if self._active_search else None
        self.mode_chip.configure(text=MODE_LABELS[view.mode])

        if purpose is SearchPurpose.AI_MOVE:
            status = "AI 思考中"
            note = (
                "V4.1F · 等待响应"
                if self.settings.ai_engine is AiEngine.DEEPSEEK_API
                else f"{DIFFICULTY_LABELS[view.difficulty]} · 正在计算"
            )
            status_color = theme.ACCENT
        elif view.result is GameResult.BLACK_WIN:
            status = "黑方获胜"
            note = "五子连珠"
            status_color = theme.WARM_ACCENT
        elif view.result is GameResult.WHITE_WIN:
            status = "白方获胜"
            note = "五子连珠"
            status_color = theme.WARM_ACCENT
        elif view.result is GameResult.DRAW:
            status = "和棋"
            note = "棋盘已满"
            status_color = theme.MUTED
        else:
            status = f"{_STONE_LABELS[view.current_stone]}回合"
            note = "黑方先行" if view.move_count == 0 else "对局进行中"
            if purpose is SearchPurpose.HINT:
                note = (
                    "V4.1F · 分析提示"
                    if self.settings.ai_engine is AiEngine.DEEPSEEK_API
                    else "正在分析提示"
                )
            status_color = theme.INK

        self.status_label.configure(text=status, foreground=status_color)
        self.status_note.configure(text=note)
        self.move_count_label.configure(text=str(view.move_count))
        self.last_move_label.configure(text=_position_label(view.last_move))

        self.mode_control.set_selected(view.mode.value)
        self.mode_control.set_enabled(not busy)
        self.difficulty_control.set_selected(view.difficulty.value)
        self.difficulty_control.set_enabled(not busy)
        self.undo_button.set_enabled(view.move_count > 0 and not busy)
        self.hint_button.set_enabled(view.can_request_hint and not busy)
        self._draw_turn_badge(view)

    def _draw_turn_badge(self, view: GameView) -> None:
        """绘制当前回合或获胜方的小棋子徽标。"""
        self.turn_badge.delete("all")
        center = 21

        if view.result is GameResult.DRAW:
            self._draw_badge_stone(center - 5, center, 8.5, Stone.BLACK)
            self._draw_badge_stone(center + 5, center, 8.5, Stone.WHITE)
            return

        if view.result is GameResult.BLACK_WIN:
            stone = Stone.BLACK
            finished = True
        elif view.result is GameResult.WHITE_WIN:
            stone = Stone.WHITE
            finished = True
        else:
            stone = view.current_stone
            finished = False

        self._draw_badge_stone(center, center, 11, stone)
        if finished:
            radius = 15
            self.turn_badge.create_oval(
                center - radius,
                center - radius,
                center + radius,
                center + radius,
                outline=theme.WIN_LINE,
                width=2,
            )

    def _draw_badge_stone(self, x: float, y: float, radius: float, stone: Stone) -> None:
        """绘制侧栏中的简化棋子。"""
        if stone is Stone.BLACK:
            fill = theme.BLACK_STONE
            outline = "#090C0D"
        else:
            fill = theme.WHITE_STONE
            outline = theme.WHITE_OUTLINE
        self.turn_badge.create_oval(
            x - radius + 1,
            y - radius + 2,
            x + radius + 1,
            y + radius + 2,
            fill="#D9D1C4",
            outline="",
        )
        self.turn_badge.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=fill,
            outline=outline,
            width=1,
        )

    def _show_message(self, message: str) -> None:
        """显示短暂错误或操作提示，并重置自动清除计时器。"""
        if self._message_after is not None:
            self.root.after_cancel(self._message_after)
        self.message_label.configure(text=message)
        self._message_after = self.root.after(1800, self._expire_message)

    def _clear_message(self) -> None:
        """立即清除提示并取消等待中的清除回调。"""
        if self._message_after is not None:
            self.root.after_cancel(self._message_after)
            self._message_after = None
        self.message_label.configure(text="")

    def _expire_message(self) -> None:
        """由 after 计时器触发的提示自动清除。"""
        self._message_after = None
        self.message_label.configure(text="")

    def _open_settings(self) -> None:
        """打开设置窗口，保存设置并按需重新加载 ONNX 引擎。"""
        updated = SettingsDialog(
            self.root,
            self.settings,
            model_available=self.policy_model is not None,
        ).show()
        if updated is None:
            return
        try:
            save_settings(updated)
        except OSError as exc:
            self._show_message(f"设置保存失败：{exc}")
            return

        if updated.ai_engine is AiEngine.LOCAL_ONNX:
            if self.policy_model is None or not self.settings.ai_engine.use_onnx:
                self.policy_model, self._model_error = load_optional_model()
        else:
            self.policy_model, self._model_error = (None, None)
        self.settings = updated
        self._refresh_engine_label()
        self._show_message("设置已保存")

    def _open_about(self) -> None:
        """打开关于我们窗口。"""
        AboutDialog(self.root).show()

    def _refresh_engine_label(self) -> None:
        """更新侧栏当前 AI 后端标签。"""
        self.engine_label.configure(text=self._engine_label_text())

    def _engine_label_text(self) -> str:
        """返回当前设置和模型状态对应的引擎标签。"""
        if self.settings.ai_engine is AiEngine.DEEPSEEK_API:
            return "AI 引擎 · DeepSeek V4.1 Flash"
        if self.policy_model is not None:
            return f"AI 引擎 · {self.policy_model.backend_label}"
        return "AI 引擎 · 本地搜索 CPU"

    def _undo_from_keyboard(self, _event: tk.Event) -> str:
        """Ctrl+Z 快捷悔棋。"""
        self._undo()
        return "break"

    def _restart_from_keyboard(self, _event: tk.Event) -> str:
        """Ctrl+N 快捷重开。"""
        self._restart()
        return "break"

    def _hint_from_keyboard(self, _event: tk.Event) -> str:
        """Ctrl+H 快捷请求提示。"""
        self._request_hint()
        return "break"

    def _toggle_fullscreen(self, _event: tk.Event) -> str:
        """F11 切换全屏。"""
        fullscreen = bool(self.root.attributes("-fullscreen"))
        self.root.attributes("-fullscreen", not fullscreen)
        return "break"

    def _exit_fullscreen(self, _event: tk.Event) -> str:
        """Esc 退出全屏。"""
        self.root.attributes("-fullscreen", False)
        return "break"

    def _close(self) -> None:
        """关闭窗口，停止轮询并让后台搜索结果失效。"""
        self._closed = True
        self._cancel_search()
        if self._poll_after is not None:
            self.root.after_cancel(self._poll_after)
            self._poll_after = None
        if self._message_after is not None:
            self.root.after_cancel(self._message_after)
            self._message_after = None
        self.root.destroy()


def _enable_high_dpi() -> None:
    """在 Windows 上启用进程级高 DPI，避免字体和棋盘发虚。"""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        return


def main() -> None:
    """加载设置，先展示开局页，用户确认后再创建主窗口。"""
    _enable_high_dpi()
    root = tk.Tk()
    root.withdraw()
    saved_settings = load_settings()
    selected = GameSetupDialog(root, saved_settings).show()
    if selected is None:
        root.destroy()
        return

    with contextlib.suppress(OSError):
        save_settings(selected)
    controller = GameController(
        _BOARD_SIZE,
        mode=selected.mode,
        difficulty=selected.difficulty,
        human_stone=selected.human_stone,
    )
    DropFiveWindow(root, controller, selected)
    root.deiconify()
    root.mainloop()
