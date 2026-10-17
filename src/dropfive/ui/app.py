"""Main tkinter application window."""

import tkinter as tk

from dropfive import __version__
from dropfive.controller.game_controller import (
    ActionError,
    ActionResult,
    GameController,
    GameView,
)
from dropfive.model.game import GameResult
from dropfive.model.history import Move
from dropfive.model.stone import Stone
from dropfive.ui import theme
from dropfive.ui.board_canvas import BoardCanvas

_BOARD_SIZE = 15

_STONE_LABELS = {
    Stone.BLACK: "黑方",
    Stone.WHITE: "白方",
}

_ERROR_MESSAGES = {
    ActionError.OUT_OF_BOUNDS: "该位置不在棋盘内。",
    ActionError.OCCUPIED: "该位置已有棋子。",
    ActionError.GAME_OVER: "本局已经结束。",
    ActionError.NO_UNDO: "当前没有可悔的棋。",
}


def _position_label(move: Move | None) -> str:
    if move is None:
        return "尚无落子"
    return f"{chr(ord('A') + move.col)}{move.row + 1}"


class DropFiveWindow:
    """Coordinate game actions and render the controller's state."""

    def __init__(
        self,
        root: tk.Tk,
        controller: GameController | None = None,
    ) -> None:
        self.root = root
        self.controller = controller or GameController(_BOARD_SIZE)
        self._message_after: str | None = None

        self.root.title("落五 DropFive")
        self.root.geometry("1040x760")
        self.root.minsize(900, 680)
        self.root.configure(background=theme.APP_BG)

        self._build_layout()
        self.root.bind("<Control-z>", self._undo_from_keyboard)
        self.root.bind("<Control-n>", self._restart_from_keyboard)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self._refresh()

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        content = tk.Frame(
            self.root,
            background=theme.APP_BG,
            padx=28,
            pady=24,
        )
        content.grid(row=0, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1, minsize=520)
        content.columnconfigure(1, minsize=250)
        content.rowconfigure(1, weight=1)

        header = tk.Frame(content, background=theme.APP_BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        header.columnconfigure(1, weight=1)

        tk.Label(
            header,
            text="落五",
            background=theme.APP_BG,
            foreground=theme.INK,
            font=("Microsoft YaHei UI", 26, "bold"),
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            header,
            text="DROPFIVE",
            background=theme.APP_BG,
            foreground=theme.ACCENT,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(13, 0))
        tk.Label(
            header,
            text=f"v{__version__}",
            background=theme.APP_BG,
            foreground=theme.MUTED,
            font=("Segoe UI", 9),
        ).grid(row=0, column=2, sticky="e")

        self.board_canvas = BoardCanvas(
            content,
            board_size=_BOARD_SIZE,
            on_move=self._handle_move,
        )
        self.board_canvas.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=(0, 18),
        )

        self.sidebar = tk.Frame(
            content,
            background=theme.SURFACE,
            highlightbackground=theme.BORDER,
            highlightthickness=1,
            padx=22,
            pady=22,
        )
        self.sidebar.grid(row=1, column=1, sticky="nsew")
        self.sidebar.columnconfigure(0, weight=1)
        self.sidebar.rowconfigure(7, weight=1)

        tk.Label(
            self.sidebar,
            text="双人对战",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 10),
        ).grid(row=0, column=0, sticky="w")

        self.status_label = tk.Label(
            self.sidebar,
            text="",
            background=theme.SURFACE,
            foreground=theme.INK,
            font=("Microsoft YaHei UI", 20, "bold"),
            anchor="w",
            justify="left",
            wraplength=196,
        )
        self.status_label.grid(row=1, column=0, sticky="ew", pady=(14, 4))

        self.detail_label = tk.Label(
            self.sidebar,
            text="",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Microsoft YaHei UI", 10),
            anchor="w",
            justify="left",
            wraplength=196,
        )
        self.detail_label.grid(row=2, column=0, sticky="ew")

        tk.Frame(
            self.sidebar,
            background=theme.BORDER,
            height=1,
        ).grid(row=3, column=0, sticky="ew", pady=22)

        self.new_button = tk.Button(
            self.sidebar,
            text="重新开始",
            command=self._restart,
            background=theme.ACCENT,
            foreground="#FFFFFF",
            activebackground=theme.ACCENT_ACTIVE,
            activeforeground="#FFFFFF",
            disabledforeground="#C8D2CE",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 11, "bold"),
            padx=14,
            pady=10,
        )
        self.new_button.grid(row=4, column=0, sticky="ew")

        self.undo_button = tk.Button(
            self.sidebar,
            text="悔棋",
            command=self._undo,
            background=theme.ACCENT_SOFT,
            foreground=theme.ACCENT,
            activebackground="#CFE0D8",
            activeforeground=theme.ACCENT,
            disabledforeground="#A5B0AA",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            font=("Microsoft YaHei UI", 11),
            padx=14,
            pady=10,
        )
        self.undo_button.grid(row=5, column=0, sticky="ew", pady=(10, 0))

        self.message_label = tk.Label(
            self.sidebar,
            text="",
            background=theme.SURFACE,
            foreground=theme.WARM_ACCENT,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            justify="left",
            wraplength=196,
            height=2,
        )
        self.message_label.grid(row=6, column=0, sticky="ew", pady=(16, 0))

        tk.Label(
            self.sidebar,
            text="15 × 15  ·  无禁手",
            background=theme.SURFACE,
            foreground=theme.MUTED,
            font=("Segoe UI", 9),
        ).grid(row=8, column=0, sticky="w")

    def _handle_move(self, row: int, col: int) -> None:
        result = self.controller.play(row, col)
        self._handle_action_result(result)
        self._refresh()

    def _undo(self) -> None:
        result = self.controller.undo()
        self._handle_action_result(result)
        self._refresh()

    def _restart(self) -> None:
        result = self.controller.restart()
        self._handle_action_result(result)
        self._refresh()

    def _handle_action_result(self, result: ActionResult) -> None:
        if result.ok:
            self._clear_message()
            return
        if result.error is not None:
            self._show_message(_ERROR_MESSAGES[result.error])

    def _refresh(self) -> None:
        view = self.controller.view()
        self.board_canvas.set_state(
            view.board,
            view.last_move,
            view.current_stone,
            interactive=not view.result.is_finished,
        )
        self._update_sidebar(view)

    def _update_sidebar(self, view: GameView) -> None:
        if view.result is GameResult.BLACK_WIN:
            status = "黑方获胜"
        elif view.result is GameResult.WHITE_WIN:
            status = "白方获胜"
        elif view.result is GameResult.DRAW:
            status = "和棋"
        else:
            status = f"{_STONE_LABELS[view.current_stone]}回合"

        self.status_label.configure(text=status)
        self.detail_label.configure(
            text=f"第 {view.move_count} 手 · 最近 {_position_label(view.last_move)}"
        )
        self.undo_button.configure(
            state="normal" if view.move_count > 0 else "disabled",
            cursor="hand2" if view.move_count > 0 else "arrow",
        )

    def _show_message(self, message: str) -> None:
        if self._message_after is not None:
            self.root.after_cancel(self._message_after)
        self.message_label.configure(text=message)
        self._message_after = self.root.after(1800, self._expire_message)

    def _clear_message(self) -> None:
        if self._message_after is not None:
            self.root.after_cancel(self._message_after)
            self._message_after = None
        self.message_label.configure(text="")

    def _expire_message(self) -> None:
        self._message_after = None
        self.message_label.configure(text="")

    def _undo_from_keyboard(self, _event: tk.Event) -> str:
        self._undo()
        return "break"

    def _restart_from_keyboard(self, _event: tk.Event) -> str:
        self._restart()
        return "break"

    def _close(self) -> None:
        if self._message_after is not None:
            self.root.after_cancel(self._message_after)
            self._message_after = None
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    DropFiveWindow(root)
    root.mainloop()
