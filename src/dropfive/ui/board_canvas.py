"""Interactive Gomoku board rendered with tkinter Canvas."""

import math
import tkinter as tk
from collections.abc import Callable

from dropfive.model.history import Move
from dropfive.model.stone import Stone
from dropfive.ui import theme


class BoardCanvas(tk.Canvas):
    """Render board state and translate pointer events into cell coordinates."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        board_size: int,
        on_move: Callable[[int, int], None],
    ) -> None:
        super().__init__(
            master,
            background=theme.BOARD_AREA_BG,
            highlightthickness=0,
            cursor="hand2",
        )
        self._board_size = board_size
        self._on_move = on_move
        self._board = tuple(
            tuple(Stone.EMPTY for _ in range(board_size)) for _ in range(board_size)
        )
        self._current_stone = Stone.BLACK
        self._last_move: Move | None = None
        self._interactive = False
        self._hover: tuple[int, int] | None = None
        self._last_dimensions = (0, 0)

        self._board_left = 0.0
        self._board_top = 0.0
        self._grid_left = 0.0
        self._grid_top = 0.0
        self._grid_size = 0.0
        self._step = 0.0

        self.bind("<Configure>", self._handle_configure)
        self.bind("<Button-1>", self._handle_click)
        self.bind("<Motion>", self._handle_motion)
        self.bind("<Leave>", self._handle_leave)

    def set_state(
        self,
        board: tuple[tuple[Stone, ...], ...],
        last_move: Move | None,
        current_stone: Stone,
        *,
        interactive: bool,
    ) -> None:
        self._board = board
        self._last_move = last_move
        self._current_stone = current_stone
        self._interactive = interactive
        self.configure(cursor="hand2" if interactive else "arrow")
        if not interactive:
            self._hover = None
        self._render()

    def _handle_configure(self, event: tk.Event) -> None:
        dimensions = (event.width, event.height)
        if dimensions == self._last_dimensions:
            return
        self._last_dimensions = dimensions
        self._render()

    def _handle_click(self, event: tk.Event) -> None:
        if not self._interactive:
            return
        cell = self._nearest_cell(event.x, event.y)
        if cell is not None:
            self._on_move(*cell)

    def _handle_motion(self, event: tk.Event) -> None:
        if not self._interactive:
            self._set_hover(None)
            return

        cell = self._nearest_cell(event.x, event.y)
        if cell is not None:
            row, col = cell
            if self._board[row][col] is not Stone.EMPTY:
                cell = None
        self._set_hover(cell)

    def _handle_leave(self, _event: tk.Event) -> None:
        self._set_hover(None)

    def _set_hover(self, cell: tuple[int, int] | None) -> None:
        if cell == self._hover:
            return
        self._hover = cell
        self._draw_hover()

    def _nearest_cell(self, x: float, y: float) -> tuple[int, int] | None:
        if self._step <= 0:
            return None

        col = round((x - self._grid_left) / self._step)
        row = round((y - self._grid_top) / self._step)
        if not (0 <= row < self._board_size and 0 <= col < self._board_size):
            return None

        center_x = self._grid_left + col * self._step
        center_y = self._grid_top + row * self._step
        if math.hypot(x - center_x, y - center_y) <= self._step * 0.46:
            return row, col
        return None

    def _render(self) -> None:
        self.delete("all")
        if not self._update_geometry():
            return

        board_right = self._grid_left + self._grid_size + (self._grid_left - self._board_left)
        board_bottom = self._grid_top + self._grid_size + (self._grid_top - self._board_top)
        self.create_rectangle(
            self._board_left,
            self._board_top,
            board_right,
            board_bottom,
            fill=theme.BOARD_FILL,
            outline=theme.BOARD_EDGE,
            width=2,
        )

        inset = self._grid_left - self._board_left
        for index in range(self._board_size):
            position = index * self._step
            line_end = self._grid_left + self._grid_size
            line_bottom = self._grid_top + self._grid_size
            self.create_line(
                self._grid_left,
                self._grid_top + position,
                line_end,
                self._grid_top + position,
                fill=theme.GRID_COLOR,
            )
            self.create_line(
                self._grid_left + position,
                self._grid_top,
                self._grid_left + position,
                line_bottom,
                fill=theme.GRID_COLOR,
            )
            self.create_text(
                self._grid_left + position,
                self._board_top + inset / 2,
                text=chr(ord("A") + index),
                fill=theme.LABEL_COLOR,
                font=("Segoe UI", 8),
            )
            self.create_text(
                self._board_left + inset / 2,
                self._grid_top + position,
                text=str(index + 1),
                fill=theme.LABEL_COLOR,
                font=("Segoe UI", 8),
            )

        if self._board_size == 15:
            for row, col in ((3, 3), (3, 11), (7, 7), (11, 3), (11, 11)):
                x, y = self._cell_center(row, col)
                radius = max(2.5, self._step * 0.07)
                self.create_oval(
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                    fill=theme.GRID_COLOR,
                    outline="",
                )

        stone_radius = max(7.0, min(18.0, self._step * 0.43))
        for row in range(self._board_size):
            for col in range(self._board_size):
                stone = self._board[row][col]
                if stone is not Stone.EMPTY:
                    self._draw_stone(row, col, stone, stone_radius)

        if self._last_move is not None:
            x, y = self._cell_center(self._last_move.row, self._last_move.col)
            marker_radius = max(3.0, stone_radius * 0.24)
            self.create_oval(
                x - marker_radius,
                y - marker_radius,
                x + marker_radius,
                y + marker_radius,
                fill=theme.WARM_ACCENT,
                outline="",
            )

        self._draw_hover()

    def _update_geometry(self) -> bool:
        width = self.winfo_width()
        height = self.winfo_height()
        side = min(width, height)
        if side < 180:
            return False

        board_side = side - 24
        self._board_left = (width - board_side) / 2
        self._board_top = (height - board_side) / 2
        inset = min(48.0, max(34.0, board_side * 0.075))
        self._grid_left = self._board_left + inset
        self._grid_top = self._board_top + inset
        self._grid_size = board_side - inset * 2
        self._step = self._grid_size / (self._board_size - 1)
        return True

    def _cell_center(self, row: int, col: int) -> tuple[float, float]:
        return (
            self._grid_left + col * self._step,
            self._grid_top + row * self._step,
        )

    def _draw_stone(self, row: int, col: int, stone: Stone, radius: float) -> None:
        x, y = self._cell_center(row, col)
        shadow_offset = max(1.0, radius * 0.09)
        self.create_oval(
            x - radius + shadow_offset,
            y - radius + shadow_offset,
            x + radius + shadow_offset,
            y + radius + shadow_offset,
            fill="#70502F",
            outline="",
        )
        if stone is Stone.BLACK:
            fill = theme.BLACK_STONE
            outline = "#101213"
        else:
            fill = theme.WHITE_STONE
            outline = theme.WHITE_OUTLINE
        self.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=fill,
            outline=outline,
            width=1,
        )

    def _draw_hover(self) -> None:
        self.delete("hover")
        if not self._interactive or self._hover is None:
            return

        row, col = self._hover
        if self._board[row][col] is not Stone.EMPTY:
            return

        x, y = self._cell_center(row, col)
        radius = max(7.0, min(18.0, self._step * 0.40))
        fill = theme.BLACK_STONE if self._current_stone is Stone.BLACK else theme.WHITE_STONE
        self.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=fill,
            stipple="gray25",
            outline=theme.ACCENT,
            width=2,
            dash=(4, 3),
            tags=("hover",),
        )
