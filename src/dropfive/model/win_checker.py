"""只围绕最后一手检查五连。

五子棋上一局已经结束的情况下不可能继续落子，因此新产生的胜负只可能与
刚刚落下的棋子有关。围绕最后一手检查可避免每次扫描整个棋盘。
"""

from dropfive.model.board import Board
from dropfive.model.stone import Stone

_DIRECTIONS = (
    (0, 1),  # 横向
    (1, 0),  # 纵向
    (1, 1),  # 左上到右下
    (1, -1),  # 右上到左下
)


class WinChecker:
    """检测最后一手形成的连续棋子。"""

    @staticmethod
    def winner_from_last_move(board: Board, row: int, col: int) -> Stone | None:
        """返回形成五连的棋种；没有胜负时返回 ``None``。"""
        if not WinChecker.winning_line_from_last_move(board, row, col):
            return None
        return board.stone_at(row, col)

    @staticmethod
    def winning_line_from_last_move(
        board: Board, row: int, col: int
    ) -> tuple[tuple[int, int], ...]:
        """返回包含最后一手的完整获胜棋线。

        长连（超过五子）也会返回整条连续棋线，供 UI 高亮和测试使用。
        """
        stone = board.stone_at(row, col)
        if stone is Stone.EMPTY:
            return ()

        for row_step, col_step in _DIRECTIONS:
            before = WinChecker._collect_direction(board, row, col, stone, -row_step, -col_step)
            after = WinChecker._collect_direction(board, row, col, stone, row_step, col_step)
            line = tuple(reversed(before)) + ((row, col),) + tuple(after)
            if len(line) >= 5:
                return line
        return ()

    @staticmethod
    def _collect_direction(
        board: Board,
        row: int,
        col: int,
        stone: Stone,
        row_step: int,
        col_step: int,
    ) -> list[tuple[int, int]]:
        """沿指定方向收集连续同色棋子，不包含最后一手自身。"""
        cells: list[tuple[int, int]] = []
        row += row_step
        col += col_step
        while board.in_bounds(row, col) and board.stone_at(row, col) is stone:
            cells.append((row, col))
            row += row_step
            col += col_step
        return cells
