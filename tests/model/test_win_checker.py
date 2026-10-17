import pytest

from dropfive.model.board import Board
from dropfive.model.stone import Stone
from dropfive.model.win_checker import WinChecker


def _board_with_line(moves: list[tuple[int, int]]) -> Board:
    board = Board()
    for row, col in moves:
        board.place(row, col, Stone.BLACK)
    return board


@pytest.mark.parametrize(
    ("moves", "last_row", "last_col"),
    [
        ([(7, 3), (7, 4), (7, 5), (7, 6), (7, 7)], 7, 7),
        ([(3, 7), (4, 7), (5, 7), (6, 7), (7, 7)], 7, 7),
        ([(3, 3), (4, 4), (5, 5), (6, 6), (7, 7)], 7, 7),
        ([(3, 11), (4, 10), (5, 9), (6, 8), (7, 7)], 7, 7),
    ],
)
def test_detects_five_in_each_direction(
    moves: list[tuple[int, int]], last_row: int, last_col: int
) -> None:
    board = _board_with_line(moves)

    assert WinChecker.winner_from_last_move(board, last_row, last_col) is Stone.BLACK


def test_detects_five_at_board_edge() -> None:
    board = _board_with_line([(0, 10), (0, 11), (0, 12), (0, 13), (0, 14)])

    assert WinChecker.winner_from_last_move(board, 0, 14) is Stone.BLACK


def test_detects_long_line() -> None:
    board = _board_with_line([(7, 2), (7, 3), (7, 4), (7, 5), (7, 6), (7, 7)])

    assert WinChecker.winner_from_last_move(board, 7, 7) is Stone.BLACK


def test_four_stones_do_not_win() -> None:
    board = _board_with_line([(7, 3), (7, 4), (7, 5), (7, 6)])

    assert WinChecker.winner_from_last_move(board, 7, 6) is None


def test_broken_line_does_not_win() -> None:
    board = _board_with_line([(7, 2), (7, 3), (7, 5), (7, 6), (7, 7)])

    assert WinChecker.winner_from_last_move(board, 7, 7) is None
