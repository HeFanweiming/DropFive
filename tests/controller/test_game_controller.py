from dropfive.controller.game_controller import ActionError, GameController
from dropfive.model.game import GameResult
from dropfive.model.stone import Stone


def test_controller_returns_immutable_view() -> None:
    controller = GameController()
    controller.play(7, 7)

    view = controller.view()

    assert view.board[7][7] is Stone.BLACK
    assert view.current_stone is Stone.WHITE
    assert view.last_move is not None
    assert view.move_count == 1


def test_controller_maps_invalid_actions_without_mutation() -> None:
    controller = GameController()
    controller.play(7, 7)

    occupied = controller.play(7, 7)

    assert not occupied.ok
    assert occupied.error is ActionError.OCCUPIED
    assert controller.view().move_count == 1


def test_controller_restart_and_undo() -> None:
    controller = GameController()
    controller.play(7, 7)

    assert controller.undo().ok
    assert controller.view().move_count == 0
    assert not controller.undo().ok

    controller.play(7, 7)
    controller.restart()

    view = controller.view()
    assert view.result is GameResult.ONGOING
    assert view.move_count == 0
    assert view.current_stone is Stone.BLACK
