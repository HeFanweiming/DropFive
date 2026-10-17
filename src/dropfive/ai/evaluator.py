"""Pattern scoring and tactical move detection."""

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

_Window = tuple[tuple[int, int], ...]


class Evaluator:
    """Score positions from one fixed stone perspective."""

    def __init__(self) -> None:
        self._line_window_cache: dict[int, tuple[_Window, ...]] = {}
        self._move_window_cache: dict[tuple[int, int, int], tuple[_Window, ...]] = {}

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

    def candidate_score(self, board: Board, row: int, col: int, stone: Stone) -> int:
        if not board.is_empty(row, col):
            return -WIN_SCORE

        attack = self._score_placed_stone(board, row, col, stone)
        defense = self._score_placed_stone(board, row, col, stone.opponent)
        return attack + int(defense * 0.95)

    def winning_points_after_move(
        self,
        board: Board,
        row: int,
        col: int,
        stone: Stone,
    ) -> set[tuple[int, int]]:
        if not board.is_empty(row, col):
            return set()
        board.place(row, col, stone)
        try:
            points, _ = self._window_features_for_placed(board, row, col, stone)
            return points
        finally:
            board.remove(row, col)

    def evaluate_board(self, board: Board, perspective: Stone) -> int:
        opponent = perspective.opponent
        score = 0
        for window in self._line_windows(board.size):
            mine = 0
            theirs = 0
            for row, col in window:
                cell = board.stone_at(row, col)
                if cell is perspective:
                    mine += 1
                elif cell is opponent:
                    theirs += 1
            if mine and theirs:
                continue
            if mine:
                score += _WINDOW_SCORES[mine]
            elif theirs:
                score -= int(_WINDOW_SCORES[theirs] * 1.15)
        return score

    def _score_placed_stone(self, board: Board, row: int, col: int, stone: Stone) -> int:
        board.place(row, col, stone)
        try:
            total = 0
            fours = 0
            open_threes = 0
            for row_step, col_step in _DIRECTIONS:
                run, open_ends = self._run_info(board, row, col, stone, row_step, col_step)
                if run >= 5:
                    return WIN_SCORE
                total += self._pattern_score(run, open_ends)
                if run >= 4 and open_ends >= 1:
                    fours += 1
                elif run == 3 and open_ends == 2:
                    open_threes += 1

            winning_points, three_windows = self._window_features_for_placed(board, row, col, stone)
            if fours >= 2:
                total += 140_000
            elif fours >= 1 and open_threes >= 1:
                total += 70_000
            elif open_threes >= 2:
                total += 20_000
            if len(winning_points) >= 2:
                total += 300_000
            elif len(winning_points) == 1:
                total += 60_000
            total += min(6_000, three_windows * 240)
            return total
        finally:
            board.remove(row, col)

    def _window_features_for_placed(
        self,
        board: Board,
        row: int,
        col: int,
        stone: Stone,
    ) -> tuple[set[tuple[int, int]], int]:
        winning_points: set[tuple[int, int]] = set()
        three_windows = 0
        for window in self._windows_containing_move(board.size, row, col):
            cells = [board.stone_at(window_row, window_col) for window_row, window_col in window]
            if stone.opponent in cells:
                continue
            mine = sum(cell is stone for cell in cells)
            if mine == 4:
                for window_row, window_col in window:
                    if board.is_empty(window_row, window_col):
                        winning_points.add((window_row, window_col))
            elif mine == 3:
                three_windows += 1
        return winning_points, three_windows

    def _line_windows(self, size: int) -> tuple[_Window, ...]:
        cached = self._line_window_cache.get(size)
        if cached is not None:
            return cached

        windows: list[_Window] = []
        for row in range(size):
            for col in range(size):
                for row_step, col_step in _DIRECTIONS:
                    end_row = row + row_step * 4
                    end_col = col + col_step * 4
                    if not (0 <= end_row < size and 0 <= end_col < size):
                        continue
                    windows.append(
                        tuple(
                            (
                                row + row_step * offset,
                                col + col_step * offset,
                            )
                            for offset in range(5)
                        )
                    )
        result = tuple(windows)
        self._line_window_cache[size] = result
        return result

    def _windows_containing_move(self, size: int, row: int, col: int) -> tuple[_Window, ...]:
        key = (size, row, col)
        cached = self._move_window_cache.get(key)
        if cached is not None:
            return cached

        windows: list[_Window] = []
        for row_step, col_step in _DIRECTIONS:
            for start_offset in range(-4, 1):
                cells = tuple(
                    (
                        row + (start_offset + offset) * row_step,
                        col + (start_offset + offset) * col_step,
                    )
                    for offset in range(5)
                )
                if all(
                    0 <= cell_row < size and 0 <= cell_col < size for cell_row, cell_col in cells
                ):
                    windows.append(cells)
        result = tuple(windows)
        self._move_window_cache[key] = result
        return result

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
