"""Time-bounded alpha-beta search."""

import time
from dataclasses import dataclass

from dropfive.ai.difficulty import DifficultyConfig
from dropfive.ai.evaluator import WIN_SCORE, Evaluator
from dropfive.ai.move_generator import MoveGenerator
from dropfive.model.board import Board
from dropfive.model.stone import Stone
from dropfive.model.win_checker import WinChecker

_INFINITY = WIN_SCORE * 2


@dataclass(frozen=True, slots=True)
class SearchResult:
    move: tuple[int, int] | None
    score: int
    depth: int
    nodes: int
    elapsed: float
    reason: str


class _SearchTimeout(Exception):
    pass


class _Deadline:
    def __init__(self, seconds: float) -> None:
        self._deadline = time.perf_counter() + seconds

    def check(self) -> None:
        if time.perf_counter() >= self._deadline:
            raise _SearchTimeout


class AlphaBetaSearch:
    def __init__(self, config: DifficultyConfig) -> None:
        self._config = config
        self._evaluator = Evaluator()
        self._generator = MoveGenerator(self._evaluator, config.candidate_limit)
        self._nodes = 0

    def search(self, board: Board, stone: Stone) -> SearchResult:
        started = time.perf_counter()
        self._nodes = 0
        deadline = _Deadline(self._config.time_limit)

        winning_moves = self._evaluator.find_winning_moves(board, stone)
        if winning_moves:
            return SearchResult(
                move=winning_moves[0],
                score=WIN_SCORE,
                depth=0,
                nodes=0,
                elapsed=time.perf_counter() - started,
                reason="immediate_win",
            )

        opponent_wins = self._evaluator.find_winning_moves(board, stone.opponent)
        if opponent_wins:
            return SearchResult(
                move=opponent_wins[0],
                score=0,
                depth=0,
                nodes=0,
                elapsed=time.perf_counter() - started,
                reason="block_win",
            )

        candidates = self._generator.generate(board, stone)
        if not candidates:
            return SearchResult(
                move=None,
                score=0,
                depth=0,
                nodes=0,
                elapsed=time.perf_counter() - started,
                reason="no_candidate",
            )

        best_move = candidates[0]
        best_score = -_INFINITY
        completed_depth = 0
        for depth in range(1, self._config.depth + 1):
            try:
                move, score = self._search_root(board, stone, depth, deadline)
            except _SearchTimeout:
                break
            best_move = move
            best_score = score
            completed_depth = depth
            if score >= WIN_SCORE:
                break

        return SearchResult(
            move=best_move,
            score=best_score,
            depth=completed_depth,
            nodes=self._nodes,
            elapsed=time.perf_counter() - started,
            reason="search" if completed_depth else "fallback_candidate",
        )

    def _search_root(
        self,
        board: Board,
        stone: Stone,
        depth: int,
        deadline: _Deadline,
    ) -> tuple[tuple[int, int], int]:
        best_move = (board.size // 2, board.size // 2)
        best_score = -_INFINITY
        alpha = -_INFINITY

        for row, col in self._generator.generate(board, stone):
            deadline.check()
            board.place(row, col, stone)
            try:
                if WinChecker.winner_from_last_move(board, row, col) is stone:
                    score = WIN_SCORE
                elif depth == 1:
                    score = self._evaluator.evaluate_board(board, stone)
                else:
                    score = self._minimax(
                        board,
                        stone.opponent,
                        depth - 1,
                        alpha,
                        _INFINITY,
                        stone,
                        deadline,
                    )
            finally:
                board.remove(row, col)

            self._nodes += 1
            if score > best_score:
                best_score = score
                best_move = (row, col)
            alpha = max(alpha, best_score)
        return best_move, best_score

    def _minimax(
        self,
        board: Board,
        stone: Stone,
        depth: int,
        alpha: int,
        beta: int,
        perspective: Stone,
        deadline: _Deadline,
    ) -> int:
        if depth == 0:
            return self._evaluator.evaluate_board(board, perspective)

        maximizing = stone is perspective
        score = -_INFINITY if maximizing else _INFINITY
        for row, col in self._generator.generate(board, stone):
            deadline.check()
            board.place(row, col, stone)
            try:
                if WinChecker.winner_from_last_move(board, row, col) is stone:
                    value = WIN_SCORE if maximizing else -WIN_SCORE
                else:
                    value = self._minimax(
                        board,
                        stone.opponent,
                        depth - 1,
                        alpha,
                        beta,
                        perspective,
                        deadline,
                    )
            finally:
                board.remove(row, col)

            self._nodes += 1
            if maximizing:
                score = max(score, value)
                alpha = max(alpha, score)
            else:
                score = min(score, value)
                beta = min(beta, score)
            if alpha >= beta:
                break
        return score
