"""Candidate generation and heuristic ordering."""

from dropfive.ai.evaluator import Evaluator
from dropfive.model.board import Board
from dropfive.model.stone import Stone


class MoveGenerator:
    def __init__(self, evaluator: Evaluator, candidate_limit: int) -> None:
        self._evaluator = evaluator
        self._candidate_limit = candidate_limit

    def generate(self, board: Board, stone: Stone) -> list[tuple[int, int]]:
        if board.stone_count == 0:
            center = board.size // 2
            return [(center, center)]

        candidates: set[tuple[int, int]] = set()
        for row in range(board.size):
            for col in range(board.size):
                if board.stone_at(row, col) is Stone.EMPTY:
                    continue
                for next_row in range(max(0, row - 2), min(board.size, row + 3)):
                    for next_col in range(max(0, col - 2), min(board.size, col + 3)):
                        if board.is_empty(next_row, next_col):
                            candidates.add((next_row, next_col))

        if not candidates:
            candidates.update(board.iter_empty())

        scored = [
            (
                self._evaluator.candidate_score(board, row, col, stone),
                -self._center_distance(board, row, col),
                row,
                col,
            )
            for row, col in candidates
        ]
        scored.sort(reverse=True)
        return [(row, col) for _, _, row, col in scored[: self._candidate_limit]]

    @staticmethod
    def _center_distance(board: Board, row: int, col: int) -> float:
        center = (board.size - 1) / 2
        return abs(row - center) + abs(col - center)
