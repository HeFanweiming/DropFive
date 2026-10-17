"""Pattern scoring and tactical move detection."""

from collections.abc import Iterator

from dropfive.model.board import Board
from dropfive.model.stone import Stone
from dropfive.model.win_checker import WinChecker

WIN_SCORE = 10_000_000

_DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))
_WINDOW_SCORES = {
    1: 2,
    2: 18,
    3: 160,
    4: 2_200,
    5: WIN_SCORE,
}


class Evaluator:
    """Score positions from one fixed stone perspective."""

    @staticmethod
    def find_winning_moves(board: Board, stone: Stone) -> list[tuple[int, int]]:
        moves: list[tuple[int, int]] = []
        for row, col in board.iter_empty():
            board.place(row, col, stone)
            try:
                if WinChecker.winner_from_last_move(board, row, col) is stone:
                    moves.append((row, col))
            finally:
                board.remove(row, col)
        return moves

    @staticmethod
    def candidate_score(board: Board, row: int, col: int, stone: Stone) -> int:
        if not board.is_empty(row, col):
            return -WIN_SCORE

        attack = Evaluator._score_placed_stone(board, row, col, stone)
        defense = Evaluator._score_placed_stone(board, row, col, stone.opponent)
        return attack + int(defense * 0.92)

    @staticmethod
    def evaluate_board(board: Board, perspective: Stone) -> int:
        opponent = perspective.opponent
        score = 0
        for window in Evaluator._iter_windows(board):
            mine = sum(cell is perspective for cell in window)
            theirs = sum(cell is opponent for cell in window)
            if mine and theirs:
                continue
            if mine:
                score += _WINDOW_SCORES[mine]
            elif theirs:
                score -= int(_WINDOW_SCORES[theirs] * 1.15)
        return score

    @staticmethod
    def _score_placed_stone(board: Board, row: int, col: int, stone: Stone) -> int:
        board.place(row, col, stone)
        try:
            total = 0
            fours = 0
            open_threes = 0
            for row_step, col_step in _DIRECTIONS:
                run, open_ends = Evaluator._run_info(board, row, col, stone, row_step, col_step)
                if run >= 5:
                    return WIN_SCORE
                total += Evaluator._pattern_score(run, open_ends)
                if run >= 4 and open_ends >= 1:
                    fours += 1
                elif run == 3 and open_ends == 2:
                    open_threes += 1

            if fours >= 2:
                total += 140_000
            elif fours >= 1 and open_threes >= 1:
                total += 70_000
            elif open_threes >= 2:
                total += 20_000
            return total
        finally:
            board.remove(row, col)

    @staticmethod
    def _run_info(
        board: Board,
        row: int,
        col: int,
        stone: Stone,
        row_step: int,
        col_step: int,
    ) -> tuple[int, int]:
        count = 1
        open_ends = 0

        next_row = row - row_step
        next_col = col - col_step
        while board.in_bounds(next_row, next_col) and board.stone_at(next_row, next_col) is stone:
            count += 1
            next_row -= row_step
            next_col -= col_step
        if board.in_bounds(next_row, next_col) and board.is_empty(next_row, next_col):
            open_ends += 1

        next_row = row + row_step
        next_col = col + col_step
        while board.in_bounds(next_row, next_col) and board.stone_at(next_row, next_col) is stone:
            count += 1
            next_row += row_step
            next_col += col_step
        if board.in_bounds(next_row, next_col) and board.is_empty(next_row, next_col):
            open_ends += 1
        return count, open_ends

    @staticmethod
    def _pattern_score(run: int, open_ends: int) -> int:
        if run >= 5:
            return WIN_SCORE
        if run == 4:
            return 120_000 if open_ends == 2 else 20_000 if open_ends == 1 else 400
        if run == 3:
            return 8_000 if open_ends == 2 else 1_000 if open_ends == 1 else 80
        if run == 2:
            return 240 if open_ends == 2 else 60 if open_ends == 1 else 8
        return 8 if open_ends == 2 else 2 if open_ends == 1 else 0

    @staticmethod
    def _iter_windows(board: Board) -> Iterator[tuple[Stone, ...]]:
        size = board.size
        for row in range(size):
            for col in range(size):
                for row_step, col_step in _DIRECTIONS:
                    end_row = row + row_step * 4
                    end_col = col + col_step * 4
                    if not board.in_bounds(end_row, end_col):
                        continue
                    yield tuple(
                        board.stone_at(
                            row + row_step * offset,
                            col + col_step * offset,
                        )
                        for offset in range(5)
                    )
