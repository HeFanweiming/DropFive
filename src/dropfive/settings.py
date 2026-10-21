"""Persistent user preferences for DropFive."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from dropfive.ai.difficulty import Difficulty
from dropfive.controller.game_controller import GameMode
from dropfive.model.stone import Stone


@dataclass(frozen=True, slots=True)
class AppSettings:
    mode: GameMode = GameMode.HUMAN_VS_AI
    difficulty: Difficulty = Difficulty.HARD
    human_stone: Stone = Stone.BLACK
    use_onnx: bool = True


_DEFAULT_SETTINGS = AppSettings()


def default_settings_path() -> Path:
    configured = os.environ.get("DROPFIVE_SETTINGS_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".dropfive" / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    settings_path = path or default_settings_path()
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return _DEFAULT_SETTINGS
    if not isinstance(data, dict):
        return _DEFAULT_SETTINGS

    try:
        return AppSettings(
            mode=GameMode(data.get("mode", _DEFAULT_SETTINGS.mode.value)),
            difficulty=Difficulty(data.get("difficulty", _DEFAULT_SETTINGS.difficulty.value)),
            human_stone=Stone(data.get("human_stone", _DEFAULT_SETTINGS.human_stone.value)),
            use_onnx=bool(data.get("use_onnx", _DEFAULT_SETTINGS.use_onnx)),
        )
    except (TypeError, ValueError):
        return _DEFAULT_SETTINGS


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    settings_path = path or default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    payload["mode"] = settings.mode.value
    payload["difficulty"] = settings.difficulty.value
    payload["human_stone"] = settings.human_stone.value
    temporary = settings_path.with_suffix(f"{settings_path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(settings_path)
