"""开局页和设置页共享的标签与选项值。"""

from dropfive.ai.difficulty import Difficulty
from dropfive.controller.game_controller import GameMode

MODE_LABELS = {
    GameMode.TWO_PLAYER: "双人对战",
    GameMode.HUMAN_VS_AI: "人机对战",
}

DIFFICULTY_LABELS = {
    Difficulty.EASY: "简单",
    Difficulty.MEDIUM: "普通",
    Difficulty.HARD: "困难",
    Difficulty.MASTER: "大师",
}

MODE_OPTIONS = [
    (GameMode.TWO_PLAYER.value, "双人"),
    (GameMode.HUMAN_VS_AI.value, "人机"),
]

DIFFICULTY_OPTIONS = [
    (Difficulty.EASY.value, "简单"),
    (Difficulty.MEDIUM.value, "普通"),
    (Difficulty.HARD.value, "困难"),
    (Difficulty.MASTER.value, "大师"),
]

SIDE_OPTIONS = [
    (str(1), "先手"),
    (str(2), "后手"),
]
