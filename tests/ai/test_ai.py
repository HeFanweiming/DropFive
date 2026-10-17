import time

import pytest

from dropfive.ai.difficulty import Difficulty, get_difficulty_config
from dropfive.ai.strategy import GomokuAI
from dropfive.model.board import Board
from dropfive.model.stone import Stone


def _snapshot_with_line(stone: Stone) -> tuple[tuple[Stone, ...], ...]:
    board = Board()
    for col in range(3, 7):
        board.place(7, col, stone)
    return board.snapshot()


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_all_difficulties_take_an_immediate_win(difficulty: Difficulty) -> None:
    result = GomokuAI(difficulty).choose_move(_snapshot_with_line(Stone.WHITE), Stone.WHITE)

    assert result.move in {(7, 2), (7, 7)}
    assert result.reason == "immediate_win"


@pytest.mark.parametrize("difficulty", list(Difficulty))
def test_all_difficulties_block_an_immediate_loss(difficulty: Difficulty) -> None:
    result = GomokuAI(difficulty).choose_move(_snapshot_with_line(Stone.BLACK), Stone.WHITE)

    assert result.move in {(7, 2), (7, 7)}
    assert result.reason == "block_win"


def test_empty_board_starts_at_center() -> None:
    result = GomokuAI(Difficulty.MEDIUM).choose_move(Board().snapshot(), Stone.WHITE)

    assert result.move == (7, 7)


def test_search_returns_a_legal_move_and_preserves_snapshot() -> None:
    board = Board()
    board.place(7, 7, Stone.BLACK)
    board.place(8, 8, Stone.WHITE)
    board.place(6, 6, Stone.BLACK)
    snapshot = board.snapshot()
    before = tuple(tuple(row) for row in snapshot)

    result = GomokuAI(Difficulty.MEDIUM).choose_move(snapshot, Stone.WHITE)

    assert result.move is not None
    assert snapshot == before
    assert result.nodes >= 1


def test_hard_search_stays_within_its_time_budget() -> None:
    board = Board()
    board.place(7, 7, Stone.BLACK)
    board.place(8, 8, Stone.WHITE)
    board.place(6, 6, Stone.BLACK)

    started = time.perf_counter()
    result = GomokuAI(Difficulty.HARD).choose_move(board.snapshot(), Stone.WHITE)
    elapsed = time.perf_counter() - started

    assert result.move is not None
    assert elapsed < get_difficulty_config(Difficulty.HARD).time_limit + 0.5
