import pytest

from dropfive.model.errors import GameFinishedError, NoMoveToUndoError
from dropfive.model.game import GameEngine, GameResult
from dropfive.model.stone import Stone


def test_turn_alternates_after_each_move() -> None:
    game = GameEngine()

    game.play(7, 7)
    assert game.current_stone is Stone.WHITE

    game.play(7, 8)
    assert game.current_stone is Stone.BLACK


def test_black_win_stops_the_game() -> None:
    game = GameEngine()
    for col in range(4):
        game.play(7, 3 + col)
        game.play(8, 3 + col)
    game.play(7, 7)

    assert game.result is GameResult.BLACK_WIN
    assert game.is_over

    with pytest.raises(GameFinishedError):
        game.play(9, 9)
    assert game.board.stone_at(9, 9) is Stone.EMPTY


def test_undo_restores_turn_board_and_ongoing_result() -> None:
    game = GameEngine()
    for col in range(4):
        game.play(7, 3 + col)
        game.play(8, 3 + col)
    winning_move = game.play(7, 7)

    undone_move = game.undo()

    assert undone_move == winning_move
    assert game.result is GameResult.ONGOING
    assert game.current_stone is Stone.BLACK
    assert game.board.is_empty(7, 7)
    assert len(game.history) == 8


def test_full_small_board_is_a_draw() -> None:
    game = GameEngine(board_size=4)
    for row in range(4):
        for col in range(4):
            game.play(row, col)

    assert game.result is GameResult.DRAW
    assert game.board.is_full()


def test_undo_without_history_is_rejected() -> None:
    game = GameEngine()

    with pytest.raises(NoMoveToUndoError):
        game.undo()


def test_reset_clears_all_game_state() -> None:
    game = GameEngine()
    game.play(7, 7)
    game.play(7, 8)

    game.reset()

    assert game.current_stone is Stone.BLACK
    assert game.result is GameResult.ONGOING
    assert game.history.is_empty
    assert game.board.stone_count == 0
