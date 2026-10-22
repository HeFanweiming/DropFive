"""落五的纯规则领域模型。"""

from dropfive.model.board import Board
from dropfive.model.game import GameEngine, GameResult
from dropfive.model.history import Move, MoveHistory
from dropfive.model.stone import Stone
from dropfive.model.win_checker import WinChecker

# 模型包不导出 UI 或线程相关内容，便于独立单元测试。
__all__ = [
    "Board",
    "GameEngine",
    "GameResult",
    "Move",
    "MoveHistory",
    "Stone",
    "WinChecker",
]
