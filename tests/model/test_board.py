import pytest

from dropfive.model.board import Board
from dropfive.model.errors import (
    CellStateError,
    InvalidStoneError,
    OccupiedError,
    OutOfBoundsError,
)
from dropfive.model.stone import Stone


def test_new_board_is_empty() -> None:
    board = Board()

    assert board.stone_count == 0
    assert not board.is_full()
    assert all(
        board.stone_at(row, col) is Stone.EMPTY
        for row in range(board.size)
        for col in range(board.size)
    )


def test_place_and_remove_stone() -> None:
    board = Board()

    board.place(7, 7, Stone.BLACK)

    assert board.stone_at(7, 7) is Stone.BLACK
    assert board.stone_count == 1
    assert board.remove(7, 7) is Stone.BLACK
    assert board.is_empty(7, 7)
    assert board.stone_count == 0


def test_rejects_out_of_bounds_position() -> None:
    board = Board()

    with pytest.raises(OutOfBoundsError):
        board.place(-1, 0, Stone.BLACK)
    with pytest.raises(OutOfBoundsError):
        board.stone_at(15, 0)


def test_rejects_occupied_position_without_mutating_board() -> None:
    board = Board()
    board.place(7, 7, Stone.BLACK)

    with pytest.raises(OccupiedError):
        board.place(7, 7, Stone.WHITE)

    assert board.stone_at(7, 7) is Stone.BLACK
    assert board.stone_count == 1


def test_rejects_empty_stone_and_empty_removal() -> None:
    board = Board()

    with pytest.raises(InvalidStoneError):
        board.place(0, 0, Stone.EMPTY)
    with pytest.raises(CellStateError):
        board.remove(0, 0)


def test_small_board_can_be_full_and_reset() -> None:
    board = Board(2)
    board.place(0, 0, Stone.BLACK)
    board.place(0, 1, Stone.WHITE)
    board.place(1, 0, Stone.WHITE)
    board.place(1, 1, Stone.BLACK)

    assert board.is_full()
    assert list(board.iter_empty()) == []

    board.reset()

    assert board.stone_count == 0
    assert not board.is_full()
