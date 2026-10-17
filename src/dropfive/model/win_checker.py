"""Win detection from the most recently played move."""

from dropfive.model.board import Board
from dropfive.model.stone import Stone

_DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


class WinChecker:
    @staticmethod
    def winner_from_last_move(board: Board, row: int, col: int) -> Stone | None:
        stone = board.stone_at(row, col)
        if stone is Stone.EMPTY:
            return None

        for row_step, col_step in _DIRECTIONS:
            count = 1
            count += WinChecker._count_direction(board, row, col, stone, row_step, col_step)
            count += WinChecker._count_direction(board, row, col, stone, -row_step, -col_step)
            if count >= 5:
                return stone
        return None

    @staticmethod
    def _count_direction(
        board: Board,
        row: int,
        col: int,
        stone: Stone,
        row_step: int,
        col_step: int,
    ) -> int:
        count = 0
        row += row_step
        col += col_step
        while board.in_bounds(row, col) and board.stone_at(row, col) is stone:
            count += 1
            row += row_step
            col += col_step
        return count
