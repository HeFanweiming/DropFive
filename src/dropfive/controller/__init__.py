"""棋局流程协调层的公开接口。"""

from dropfive.controller.game_controller import (
    ActionError,
    ActionResult,
    GameController,
    GameMode,
    GameView,
    SearchPurpose,
    SearchRequest,
)

# 对 UI 暴露的控制器、视图快照和搜索请求类型。
__all__ = [
    "ActionError",
    "ActionResult",
    "GameController",
    "GameMode",
    "GameView",
    "SearchPurpose",
    "SearchRequest",
]
