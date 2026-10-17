"""Interactive Gomoku board rendered with tkinter Canvas."""

import math
import tkinter as tk
from collections.abc import Callable

from dropfive.model.history import Move
from dropfive.model.stone import Stone
from dropfive.ui import theme
from dropfive.ui.metrics import BoardVisualScale, board_visual_scale


class BoardCanvas(tk.Canvas):
    """Render a tactile board surface and translate pointer events into cells."""

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
            borderwidth=0,
            cursor="hand2",
        )
        self._board_size = board_size
        self._on_move = on_move
        self._board = tuple(
            tuple(Stone.EMPTY for _ in range(board_size)) for _ in range(board_size)
        )
        self._current_stone = Stone.BLACK
        self._last_move: Move | None = None
        self._winning_cells: tuple[tuple[int, int], ...] = ()
        self._interactive = False
        self._hover: tuple[int, int] | None = None
        self._last_dimensions = (0, 0)

        self._board_left = 0.0
        self._board_top = 0.0
        self._board_side = 0.0
        self._grid_left = 0.0
        self._grid_top = 0.0
        self._grid_size = 0.0
        self._step = 0.0
        self._visual_scale: BoardVisualScale = board_visual_scale(40.0)

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
        winning_cells: tuple[tuple[int, int], ...] = (),
    ) -> None:
        self._board = board
        self._last_move = last_move
        self._current_stone = current_stone
        self._winning_cells = winning_cells
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
        if cell is not None and self._board[cell[0]][cell[1]] is not Stone.EMPTY:
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

        self._draw_board_surface()
        self._draw_grid()
        self._draw_winning_line()
        self._draw_stones()
        self._draw_winning_rings()
        self._draw_last_move()
        self._draw_hover()

    def _update_geometry(self) -> bool:
        width = self.winfo_width()
        height = self.winfo_height()
        side = min(width, height)
        if side < 180:
            return False

        self._board_side = side - 44
        self._board_left = (width - self._board_side) / 2
        self._board_top = (height - self._board_side) / 2
        inset = min(78.0, max(38.0, self._board_side * 0.078))
        self._grid_left = self._board_left + inset
        self._grid_top = self._board_top + inset
        self._grid_size = self._board_side - inset * 2
        self._step = self._grid_size / (self._board_size - 1)
        self._visual_scale = board_visual_scale(self._step)
        return True

    def _draw_board_surface(self) -> None:
        corner_radius = max(10.0, min(16.0, self._board_side * 0.018))
        shadow_offset = max(8.0, min(14.0, self._board_side * 0.012))
        shadow_points = self._rounded_points(
            self._board_left + 5,
            self._board_top + shadow_offset,
            self._board_left + self._board_side + 5,
            self._board_top + self._board_side + shadow_offset,
            corner_radius,
        )
        self.create_polygon(
            shadow_points,
            smooth=True,
            splinesteps=28,
            fill=theme.BOARD_SHADOW,
            outline="",
        )

        outer_points = self._rounded_points(
            self._board_left,
            self._board_top,
            self._board_left + self._board_side,
            self._board_top + self._board_side,
            corner_radius,
        )
        self.create_polygon(
            outer_points,
            smooth=True,
            splinesteps=28,
            fill=theme.BOARD_BORDER,
            outline="",
        )

        inset = 3.0
        inner_points = self._rounded_points(
            self._board_left + inset,
            self._board_top + inset,
            self._board_left + self._board_side - inset,
            self._board_top + self._board_side - inset,
            max(8.0, corner_radius - 2),
        )
        self.create_polygon(
            inner_points,
            smooth=True,
            splinesteps=28,
            fill=theme.BOARD_FILL,
            outline=theme.BOARD_EDGE,
            width=1,
        )

        grain_left = self._board_left + 18
        grain_right = self._board_left + self._board_side - 18
        for index, fraction in enumerate((0.09, 0.24, 0.73, 0.9)):
            points: list[float] = []
            for segment in range(8):
                ratio = segment / 7
                x = grain_left + (grain_right - grain_left) * ratio
                y = (
                    self._board_top
                    + self._board_side * fraction
                    + math.sin(ratio * math.tau + index) * 2.2
                )
                points.extend((x, y))
            self.create_line(
                points,
                smooth=True,
                splinesteps=24,
                fill=theme.BOARD_GRAIN,
                width=max(1.0, self._visual_scale.grid_line_width * 0.8),
            )

    def _draw_grid(self) -> None:
        inset = self._grid_left - self._board_left
        line_end = self._grid_left + self._grid_size
        line_bottom = self._grid_top + self._grid_size

        for index in range(self._board_size):
            position = index * self._step
            base_width = self._visual_scale.grid_line_width
            width = base_width * 1.4 if index in (0, self._board_size - 1) else base_width
            self.create_line(
                self._grid_left,
                self._grid_top + position,
                line_end,
                self._grid_top + position,
                fill=theme.GRID_COLOR,
                width=width,
            )
            self.create_line(
                self._grid_left + position,
                self._grid_top,
                self._grid_left + position,
                line_bottom,
                fill=theme.GRID_COLOR,
                width=width,
            )
            self.create_text(
                self._grid_left + position,
                self._board_top + inset / 2,
                text=chr(ord("A") + index),
                fill=theme.LABEL_COLOR,
                font=("Segoe UI", self._visual_scale.coordinate_font_size, "bold"),
            )
            self.create_text(
                self._board_left + inset / 2,
                self._grid_top + position,
                text=str(index + 1),
                fill=theme.LABEL_COLOR,
                font=("Segoe UI", self._visual_scale.coordinate_font_size),
            )

        if self._board_size == 15:
            for row, col in ((3, 3), (3, 11), (7, 7), (11, 3), (11, 11)):
                x, y = self._cell_center(row, col)
                radius = max(2.8, self._step * 0.072)
                self.create_oval(
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                    fill=theme.GRID_COLOR,
                    outline="",
                )

    def _draw_stones(self) -> None:
        radius = self._visual_scale.stone_radius
        for row in range(self._board_size):
            for col in range(self._board_size):
                stone = self._board[row][col]
                if stone is not Stone.EMPTY:
                    self._draw_stone(row, col, stone, radius)

    def _draw_winning_line(self) -> None:
        if len(self._winning_cells) < 2:
            return
        start = self._cell_center(*self._winning_cells[0])
        end = self._cell_center(*self._winning_cells[-1])
        self.create_line(
            *start,
            *end,
            fill=theme.WIN_LINE,
            width=self._visual_scale.winning_line_width,
            capstyle=tk.ROUND,
        )

    def _draw_winning_rings(self) -> None:
        if not self._winning_cells:
            return
        radius = self._visual_scale.stone_radius + max(2.5, self._step * 0.08)
        for row, col in self._winning_cells:
            x, y = self._cell_center(row, col)
            self.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                outline=theme.WIN_LINE,
                width=self._visual_scale.ring_width,
            )

    def _draw_last_move(self) -> None:
        if self._last_move is None:
            return
        x, y = self._cell_center(self._last_move.row, self._last_move.col)
        radius = self._visual_scale.last_move_radius
        self.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=theme.WARM_ACCENT,
            outline="",
        )

    def _draw_stone(self, row: int, col: int, stone: Stone, radius: float) -> None:
        x, y = self._cell_center(row, col)
        shadow_offset = max(1.2, radius * 0.1)
        self.create_oval(
            x - radius + shadow_offset,
            y - radius + shadow_offset,
            x + radius + shadow_offset,
            y + radius + shadow_offset,
            fill="#6A4526",
            outline="",
        )

        if stone is Stone.BLACK:
            base = theme.BLACK_STONE
            inner = "#293234"
            outline = "#090C0D"
            highlight = theme.BLACK_STONE_LIGHT
        else:
            base = theme.WHITE_STONE
            inner = theme.WHITE_STONE_LIGHT
            outline = theme.WHITE_OUTLINE
            highlight = "#FFFFFF"

        self.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=base,
            outline=outline,
            width=1,
        )
        inner_radius = radius * 0.76
        self.create_oval(
            x - inner_radius - radius * 0.06,
            y - inner_radius - radius * 0.06,
            x + inner_radius - radius * 0.06,
            y + inner_radius - radius * 0.06,
            fill=inner,
            outline="",
        )
        gloss_width = radius * 0.46
        gloss_height = radius * 0.28
        self.create_oval(
            x - radius * 0.52,
            y - radius * 0.58,
            x - radius * 0.52 + gloss_width,
            y - radius * 0.58 + gloss_height,
            fill=highlight,
            stipple="gray50",
            outline="",
        )

    def _draw_hover(self) -> None:
        self.delete("hover")
        if not self._interactive or self._hover is None:
            return

        row, col = self._hover
        if self._board[row][col] is not Stone.EMPTY:
            return

        x, y = self._cell_center(row, col)
        radius = self._visual_scale.stone_radius * 0.92
        halo_radius = radius + max(3.0, self._step * 0.08)
        self.create_oval(
            x - halo_radius,
            y - halo_radius,
            x + halo_radius,
            y + halo_radius,
            fill=theme.WIN_LINE,
            stipple="gray12",
            outline="",
            tags=("hover",),
        )
        fill = theme.BLACK_STONE if self._current_stone is Stone.BLACK else theme.WHITE_STONE
        self.create_oval(
            x - radius,
            y - radius,
            x + radius,
            y + radius,
            fill=fill,
            stipple="gray50",
            outline=theme.HOVER_OUTLINE,
            width=2,
            dash=(4, 3),
            tags=("hover",),
        )

    def _cell_center(self, row: int, col: int) -> tuple[float, float]:
        return (
            self._grid_left + col * self._step,
            self._grid_top + row * self._step,
        )

    @staticmethod
    def _rounded_points(
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        radius: float,
    ) -> tuple[float, ...]:
        return (
            x0 + radius,
            y0,
            x1 - radius,
            y0,
            x1,
            y0,
            x1,
            y0 + radius,
            x1,
            y1 - radius,
            x1,
            y1,
            x1 - radius,
            y1,
            x0 + radius,
            y1,
            x0,
            y1,
            x0,
            y1 - radius,
            x0,
            y0 + radius,
            x0,
            y0,
        )
