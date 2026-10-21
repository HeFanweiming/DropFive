from dropfive.controller.game_controller import (
    ActionError,
    GameController,
    GameMode,
    SearchPurpose,
)
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
    assert view.winning_cells == ()


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


def test_human_vs_ai_requests_and_applies_ai_move() -> None:
    controller = GameController(mode=GameMode.HUMAN_VS_AI)

    assert controller.play(7, 7).ok
    view = controller.view()
    assert view.is_ai_turn
    assert not view.can_human_play

    request = controller.make_search_request(SearchPurpose.AI_MOVE)
    assert request is not None
    assert request.stone is Stone.WHITE

    blocked = controller.play(7, 8)
    assert blocked.error is ActionError.NOT_YOUR_TURN
    assert controller.view().move_count == 1

    assert controller.play_ai_move(7, 8, request.game_id).ok
    assert controller.view().current_stone is Stone.BLACK
    assert controller.view().move_count == 2


def test_human_vs_ai_undo_removes_both_turns() -> None:
    controller = GameController(mode=GameMode.HUMAN_VS_AI)
    controller.play(7, 7)
    request = controller.make_search_request(SearchPurpose.AI_MOVE)
    assert request is not None
    controller.play_ai_move(7, 8, request.game_id)

    assert controller.undo().ok

    view = controller.view()
    assert view.move_count == 0
    assert view.current_stone is Stone.BLACK
    assert view.board[7][7] is Stone.EMPTY
    assert view.board[7][8] is Stone.EMPTY


def test_stale_ai_result_is_rejected_after_restart() -> None:
    controller = GameController(mode=GameMode.HUMAN_VS_AI)
    controller.play(7, 7)
    request = controller.make_search_request(SearchPurpose.AI_MOVE)
    assert request is not None

    controller.restart()

    result = controller.play_ai_move(7, 8, request.game_id)
    assert result.error is ActionError.STALE_REQUEST
    assert controller.view().move_count == 0


def test_two_player_can_request_a_hint_for_the_current_side() -> None:
    controller = GameController()
    controller.play(7, 7)

    request = controller.make_search_request(SearchPurpose.HINT)

    assert request is not None
    assert request.stone is Stone.WHITE


def test_mode_change_resets_the_game() -> None:
    controller = GameController()
    controller.play(7, 7)

    controller.set_mode(GameMode.HUMAN_VS_AI)

    view = controller.view()
    assert view.mode is GameMode.HUMAN_VS_AI
    assert view.move_count == 0
    assert view.current_stone is Stone.BLACK


def test_human_can_choose_white_and_ai_moves_first() -> None:
    controller = GameController(
        mode=GameMode.HUMAN_VS_AI,
        human_stone=Stone.WHITE,
    )

    view = controller.view()
    assert view.human_stone is Stone.WHITE
    assert view.is_ai_turn

    request = controller.make_search_request(SearchPurpose.AI_MOVE)
    assert request is not None
    assert request.stone is Stone.BLACK
    assert controller.play_ai_move(7, 7, request.game_id).ok

    view = controller.view()
    assert view.current_stone is Stone.WHITE
    assert view.can_human_play
