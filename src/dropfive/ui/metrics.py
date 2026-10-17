"""Responsive drawing measurements shared by the board renderer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoardVisualScale:
    stone_radius: float
    coordinate_font_size: int
    grid_line_width: float
    last_move_radius: float
    winning_line_width: float
    ring_width: float


def board_visual_scale(step: float) -> BoardVisualScale:
    """Scale board details from cell spacing instead of window pixels."""

    return BoardVisualScale(
        stone_radius=max(8.0, step * 0.44),
        coordinate_font_size=max(8, min(15, round(step * 0.22))),
        grid_line_width=max(1.0, min(2.0, step * 0.025)),
        last_move_radius=max(2.6, step * 0.11),
        winning_line_width=max(3.0, min(8.0, step * 0.11)),
        ring_width=max(2.0, min(4.0, step * 0.055)),
    )
