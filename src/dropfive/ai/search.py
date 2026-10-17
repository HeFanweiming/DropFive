"""Time-bounded alpha-beta search with transposition caching."""

import contextlib
import random
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


@dataclass(slots=True)
class _TableEntry:
    depth: int
    score: int
    flag: str
    best_move: tuple[int, int] | None


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
        self._table: dict[tuple[int, int], _TableEntry] = {}
        self._zobrist: list[list[list[int]]] = []

    def search(self, board: Board, stone: Stone) -> SearchResult:
        started = time.perf_counter()
        self._nodes = 0
        self._table.clear()
        self._prepare_zobrist(board.size)

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

        vcf_deadline = _Deadline(min(0.3, self._config.time_limit * 0.25))
        forced_win: tuple[int, int] | None = None
        with contextlib.suppress(_SearchTimeout):
            forced_win = self._find_forced_win(board, stone, self._config.depth, vcf_deadline)
        if forced_win is not None:
            return SearchResult(
                move=forced_win,
                score=WIN_SCORE,
                depth=0,
                nodes=self._nodes,
                elapsed=time.perf_counter() - started,
                reason="forced_win",
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

        position_hash = self._hash_board(board)
        remaining_time = max(0.05, self._config.time_limit - (time.perf_counter() - started))
        deadline = _Deadline(remaining_time)
        best_move = candidates[0]
        best_score = -_INFINITY
        completed_depth = 0
        for depth in range(1, self._config.depth + 1):
            try:
                move, score = self._search_root(
                    board,
                    stone,
                    depth,
                    deadline,
                    position_hash,
                    best_move,
                )
            except _SearchTimeout:
                break
            best_move = move
            best_score = score
            completed_depth = depth
            self._table[(position_hash, stone.value)] = _TableEntry(
                depth=depth,
                score=score,
                flag="exact",
                best_move=move,
            )
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

    def _find_forced_win(
        self,
        board: Board,
        stone: Stone,
        depth: int,
        deadline: _Deadline,
    ) -> tuple[int, int] | None:
        if depth <= 0:
            return None
        deadline.check()

        winning_moves = self._evaluator.find_winning_moves(board, stone)
        if winning_moves:
            return winning_moves[0]

        forcing_moves: list[tuple[tuple[int, int], set[tuple[int, int]]]] = []
        for move in self._generator.generate(board, stone):
            deadline.check()
            points = self._evaluator.winning_points_after_move(board, move[0], move[1], stone)
            if points:
                forcing_moves.append((move, points))
        forcing_moves.sort(key=lambda item: len(item[1]), reverse=True)

        for move, points in forcing_moves:
            deadline.check()
            row, col = move
            board.place(row, col, stone)
            try:
                opponent_wins = self._evaluator.find_winning_moves(board, stone.opponent)
                if opponent_wins:
                    continue
                if len(points) >= 2:
                    return move

                block = next(iter(points))
                board.place(block[0], block[1], stone.opponent)
                try:
                    if (
                        WinChecker.winner_from_last_move(board, block[0], block[1])
                        is stone.opponent
                    ):
                        continue
                    if self._find_forced_win(board, stone, depth - 1, deadline) is not None:
                        return move
                finally:
                    board.remove(block[0], block[1])
            finally:
                board.remove(row, col)
        return None

    def _search_root(
        self,
        board: Board,
        stone: Stone,
        depth: int,
        deadline: _Deadline,
        position_hash: int,
        preferred_move: tuple[int, int],
    ) -> tuple[tuple[int, int], int]:
        best_move = preferred_move
        best_score = -_INFINITY
        alpha = -_INFINITY

        for row, col in self._ordered_candidates(board, stone, preferred_move):
            deadline.check()
            child_hash = position_hash ^ self._zobrist[row][col][stone.value]
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
                        child_hash,
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
        position_hash: int,
    ) -> int:
        if depth == 0:
            return self._evaluator.evaluate_board(board, perspective)

        key = (position_hash, stone.value)
        entry = self._table.get(key)
        preferred_move = entry.best_move if entry is not None else None
        if entry is not None and entry.depth >= depth:
            if entry.flag == "exact":
                return entry.score
            if entry.flag == "lower":
                alpha = max(alpha, entry.score)
            else:
                beta = min(beta, entry.score)
            if alpha >= beta:
                return entry.score

        original_alpha = alpha
        original_beta = beta
        maximizing = stone is perspective
        score = -_INFINITY if maximizing else _INFINITY
        best_move: tuple[int, int] | None = None

        for row, col in self._ordered_candidates(board, stone, preferred_move):
            deadline.check()
            child_hash = position_hash ^ self._zobrist[row][col][stone.value]
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
                        child_hash,
                    )
            finally:
                board.remove(row, col)

            self._nodes += 1
            if maximizing:
                if value > score:
                    score = value
                    best_move = (row, col)
                alpha = max(alpha, score)
            else:
                if value < score:
                    score = value
                    best_move = (row, col)
                beta = min(beta, score)
            if alpha >= beta:
                break

        if score <= original_alpha:
            flag = "upper"
        elif score >= original_beta:
            flag = "lower"
        else:
            flag = "exact"
        self._table[key] = _TableEntry(
            depth=depth,
            score=score,
            flag=flag,
            best_move=best_move,
        )
        return score

    def _ordered_candidates(
        self,
        board: Board,
        stone: Stone,
        preferred_move: tuple[int, int] | None,
    ) -> list[tuple[int, int]]:
        candidates = self._generator.generate(board, stone)
        if preferred_move in candidates:
            candidates.remove(preferred_move)
            candidates.insert(0, preferred_move)
        return candidates

    def _prepare_zobrist(self, size: int) -> None:
        if len(self._zobrist) == size:
            return
        rng = random.Random(0xD20F1E)
        self._zobrist = [
            [[rng.getrandbits(64) for _ in range(3)] for _ in range(size)] for _ in range(size)
        ]

    def _hash_board(self, board: Board) -> int:
        position_hash = 0
        for row in range(board.size):
            for col in range(board.size):
                stone = board.stone_at(row, col)
                if stone is not Stone.EMPTY:
                    position_hash ^= self._zobrist[row][col][stone.value]
        return position_hash
