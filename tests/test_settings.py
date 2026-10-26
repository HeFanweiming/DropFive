import json
from pathlib import Path

from dropfive.ai.difficulty import Difficulty
from dropfive.controller.game_controller import GameMode
from dropfive.model.stone import Stone
from dropfive.settings import AiEngine, AppSettings, load_settings, save_settings


def test_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    expected = AppSettings(
        mode=GameMode.HUMAN_VS_AI,
        difficulty=Difficulty.MASTER,
        human_stone=Stone.WHITE,
        ai_engine=AiEngine.DEEPSEEK_API,
        deepseek_api_key="sk-test-secret",
    )

    save_settings(expected, path)

    assert load_settings(path) == expected
    assert "sk-test-secret" not in repr(expected)


def test_legacy_onnx_setting_is_migrated(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"use_onnx": False}), encoding="utf-8")

    assert load_settings(path).ai_engine is AiEngine.LOCAL_CPU


def test_invalid_settings_fall_back_to_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{invalid json", encoding="utf-8")

    settings = load_settings(path)

    assert settings.mode is GameMode.HUMAN_VS_AI
    assert settings.difficulty is Difficulty.HARD
    assert settings.human_stone is Stone.BLACK


def test_unknown_values_do_not_crash_settings_loading(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "mode": "unknown",
                "difficulty": "impossible",
                "human_stone": 99,
            }
        ),
        encoding="utf-8",
    )

    assert load_settings(path) == AppSettings()
