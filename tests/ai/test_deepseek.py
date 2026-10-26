import pytest

from dropfive.ai.deepseek import DeepSeekError, DeepSeekStrategy
from dropfive.model.board import Board
from dropfive.model.stone import Stone


def test_deepseek_response_is_parsed_into_legal_move() -> None:
    board = Board()
    board.place(7, 7, Stone.BLACK)
    captured: list[dict] = []

    def transport(payload: dict) -> dict:
        captured.append(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"row": 7, "col": 8}',
                    }
                }
            ]
        }

    strategy = DeepSeekStrategy("sk-test-secret", transport=transport)
    result = strategy.choose_move(board.snapshot(), Stone.WHITE)

    assert result.move == (7, 8)
    assert result.reason == "deepseek_api"
    assert len(captured) == 1
    assert captured[0]["model"] == "deepseek-flash"
    assert captured[0]["thinking"] == {"type": "disabled"}
    assert captured[0]["reasoning_effort"] == "none"
    assert captured[0]["max_tokens"] == 512
    assert "sk-test-secret" not in str(captured[0])
    prompt = captured[0]["messages"][1]["content"]
    assert "当前轮到白方" in prompt
    assert "合法落点" in prompt
    assert "O" in prompt


def test_deepseek_is_not_called_when_local_tactics_find_a_win() -> None:
    board = Board()
    for col in range(3, 7):
        board.place(7, col, Stone.WHITE)

    def transport(_payload: dict) -> dict:
        raise AssertionError("transport should not be called")

    result = DeepSeekStrategy("unused", transport=transport).choose_move(
        board.snapshot(),
        Stone.WHITE,
    )

    assert result.move in {(7, 2), (7, 7)}
    assert result.reason == "immediate_win"


def test_missing_api_key_falls_back_to_error_for_normal_position() -> None:
    board = Board()
    board.place(7, 7, Stone.BLACK)

    with pytest.raises(DeepSeekError, match="API Key"):
        DeepSeekStrategy("").choose_move(board.snapshot(), Stone.WHITE)


def test_invalid_or_occupied_api_move_is_rejected() -> None:
    board = Board()
    board.place(7, 7, Stone.BLACK)
    strategy = DeepSeekStrategy(
        "sk-test",
        transport=lambda _payload: {"choices": [{"message": {"content": '{"row": 7, "col": 7}'}}]},
    )

    with pytest.raises(DeepSeekError, match="已占用"):
        strategy.choose_move(board.snapshot(), Stone.WHITE)


def test_coordinate_move_and_one_repair_retry_are_supported() -> None:
    board = Board()
    board.place(7, 7, Stone.BLACK)
    calls: list[dict] = []

    def transport(payload: dict) -> dict:
        calls.append(payload)
        content = '{"move": "H8"}' if len(calls) == 1 else '{"move": "I8"}'
        return {"choices": [{"message": {"content": content}}]}

    result = DeepSeekStrategy("sk-test", transport=transport).choose_move(
        board.snapshot(),
        Stone.WHITE,
    )

    assert result.move == (7, 8)
    assert len(calls) == 2
    repair_messages = calls[1]["messages"]
    assert "上一步非法" in repair_messages[-1]["content"]
