"""Win detection from the most recently played move."""

from dropfive.model.board import Board
from dropfive.model.stone import Stone

_DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


class WinChecker:
    @staticmethod
    def winner_from_last_move(board: Board, row: int, col: int) -> Stone | None:
        if not WinChecker.winning_line_from_last_move(board, row, col):
            return None
        return board.stone_at(row, col)

    @staticmethod
    def winning_line_from_last_move(
        board: Board, row: int, col: int
    ) -> tuple[tuple[int, int], ...]:
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
        cells: list[tuple[int, int]] = []
        row += row_step
        col += col_step
        while board.in_bounds(row, col) and board.stone_at(row, col) is stone:
            cells.append((row, col))
            row += row_step
            col += col_step
        return cells
