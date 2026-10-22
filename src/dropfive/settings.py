"""落五的用户偏好设置持久化。

设置文件位于用户主目录，而不是仓库内部。这样源码、编译产物和个人偏好
彼此分离，也不会把本机路径或模式选择提交到 GitHub。
"""

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
    """跨启动保存的默认对局配置。"""

    # 默认进入人机模式；首次启动后用户可以在开始页面覆盖本局选择。
    mode: GameMode = GameMode.HUMAN_VS_AI
    difficulty: Difficulty = Difficulty.HARD
    human_stone: Stone = Stone.BLACK
    # 有兼容模型时默认尝试 ONNX；模型缺失或 Provider 失败会自动回退。
    use_onnx: bool = True


_DEFAULT_SETTINGS = AppSettings()


def default_settings_path() -> Path:
    """返回设置文件路径，可用环境变量覆盖以便测试或便携部署。"""
    configured = os.environ.get("DROPFIVE_SETTINGS_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".dropfive" / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    """读取设置；文件缺失、损坏或含未知值时安全回退到默认配置。"""
    settings_path = path or default_settings_path()
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return _DEFAULT_SETTINGS
    if not isinstance(data, dict):
        return _DEFAULT_SETTINGS

    try:
        # 使用枚举构造器做最终校验，避免把任意字符串传进控制器。
        return AppSettings(
            mode=GameMode(data.get("mode", _DEFAULT_SETTINGS.mode.value)),
            difficulty=Difficulty(data.get("difficulty", _DEFAULT_SETTINGS.difficulty.value)),
            human_stone=Stone(data.get("human_stone", _DEFAULT_SETTINGS.human_stone.value)),
            use_onnx=bool(data.get("use_onnx", _DEFAULT_SETTINGS.use_onnx)),
        )
    except (TypeError, ValueError):
        return _DEFAULT_SETTINGS


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    """以原子替换方式保存设置，避免程序中断留下半个 JSON 文件。"""
    settings_path = path or default_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(settings)
    payload["mode"] = settings.mode.value
    payload["difficulty"] = settings.difficulty.value
    payload["human_stone"] = settings.human_stone.value
    temporary = settings_path.with_suffix(f"{settings_path.suffix}.tmp")
    # 先完整写入临时文件，再 replace，失败时原设置仍然可用。
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(settings_path)
