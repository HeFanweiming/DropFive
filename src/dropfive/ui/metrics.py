"""棋盘响应式绘制尺寸。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoardVisualScale:
    """由格距推导出的棋子、字体、线宽等尺寸集合。"""

    stone_radius: float
    coordinate_font_size: int
    grid_line_width: float
    last_move_radius: float
    winning_line_width: float
    ring_width: float


def board_visual_scale(step: float) -> BoardVisualScale:
    """按格距缩放棋盘细节。

    不直接按窗口宽度缩放，是因为棋盘高度受窗口限制；使用格距可以保证
    普通窗口、全屏和不同 DPI 下棋子与网格比例一致。
    """

    return BoardVisualScale(
        stone_radius=max(8.0, step * 0.44),
        coordinate_font_size=max(8, min(15, round(step * 0.22))),
        grid_line_width=max(1.0, min(2.0, step * 0.025)),
        last_move_radius=max(2.6, step * 0.11),
        winning_line_width=max(3.0, min(8.0, step * 0.11)),
        ring_width=max(2.0, min(4.0, step * 0.055)),
    )
