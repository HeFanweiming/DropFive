"""棋盘格子的稳定状态枚举。"""

from enum import IntEnum


class Stone(IntEnum):
    """五子棋棋盘中的三种稳定状态。

    使用整数枚举而不是字符串，可以保证模型、存档和 AI 输入之间的值稳定，
    同时避免 ``"black"``、``"BLACK"`` 等拼写差异造成规则错误。
    """

    EMPTY = 0
    BLACK = 1
    WHITE = 2

    @property
    def opponent(self) -> "Stone":
        """返回对手棋子；空格没有对手，因此会抛出 ``ValueError``。"""

        if self is Stone.BLACK:
            return Stone.WHITE
        if self is Stone.WHITE:
            return Stone.BLACK
        raise ValueError("An empty cell has no opponent stone")
