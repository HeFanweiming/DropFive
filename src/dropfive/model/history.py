"""落子历史与悔棋记录。"""

from dataclasses import dataclass

from dropfive.model.errors import NoMoveToUndoError
from dropfive.model.stone import Stone


@dataclass(frozen=True, slots=True)
class Move:
    """一步不可变落子记录，``number`` 从 1 开始计数。"""

    row: int
    col: int
    stone: Stone
    number: int


class MoveHistory:
    """按时间顺序保存落子，并允许从末尾撤销。"""

    def __init__(self) -> None:
        self._moves: list[Move] = []

    def __len__(self) -> int:
        """返回当前历史中的步数。"""
        return len(self._moves)

    @property
    def is_empty(self) -> bool:
        """是否尚无落子。"""
        return not self._moves

    @property
    def last(self) -> Move | None:
        """返回最后一手；空历史返回 ``None``。"""
        return self._moves[-1] if self._moves else None

    @property
    def moves(self) -> tuple[Move, ...]:
        """返回只读历史副本，避免外部代码直接修改内部列表。"""
        return tuple(self._moves)

    def push(self, row: int, col: int, stone: Stone) -> Move:
        """追加一步落子并返回生成的不可变记录。"""
        move = Move(row=row, col=col, stone=stone, number=len(self._moves) + 1)
        self._moves.append(move)
        return move

    def pop(self) -> Move:
        """弹出最后一步；没有历史时抛出 ``NoMoveToUndoError``。"""
        if not self._moves:
            raise NoMoveToUndoError("There are no moves to undo")
        return self._moves.pop()

    def clear(self) -> None:
        """清空全部历史，供重新开局使用。"""
        self._moves.clear()
