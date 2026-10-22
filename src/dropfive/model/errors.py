"""游戏领域层的可预期异常。

界面层通过捕获这些异常把失败原因转换为提示信息；模型层不依赖 tkinter，
因此相同规则也可以直接在测试或未来命令行版本中复用。
"""


class DropFiveError(Exception):
    """落五领域异常基类。"""


class OutOfBoundsError(DropFiveError, ValueError):
    """坐标超出棋盘范围。"""


class OccupiedError(DropFiveError, ValueError):
    """尝试在已有棋子的位置继续落子。"""


class InvalidStoneError(DropFiveError, ValueError):
    """尝试把 ``EMPTY`` 当作落子写入棋盘。"""


class CellStateError(DropFiveError, ValueError):
    """撤销或删除棋子时，目标格子的状态与操作不一致。"""


class GameFinishedError(DropFiveError):
    """棋局已经结束，但仍有代码尝试继续落子。"""


class NoMoveToUndoError(DropFiveError):
    """没有历史记录时请求悔棋。"""
