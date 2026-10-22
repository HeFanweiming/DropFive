"""带合法性保护的二维棋盘模型。

内部坐标始终使用零基 ``(row, col)``：

* ``row`` 从上到下递增；
* ``col`` 从左到右递增；
* 像素坐标只在 UI 层存在，不能进入棋盘模型。
"""

from collections.abc import Iterator

from dropfive.model.errors import (
    CellStateError,
    InvalidStoneError,
    OccupiedError,
    OutOfBoundsError,
)
from dropfive.model.stone import Stone


class Board:
    """保存棋盘状态，并保证所有修改都经过合法性检查。"""

    def __init__(self, size: int = 15) -> None:
        """创建 ``size × size`` 的空棋盘。"""
        if size < 1:
            raise ValueError("Board size must be positive")
        self._size = size
        self._cells: list[list[Stone]] = [[Stone.EMPTY for _ in range(size)] for _ in range(size)]
        self._stone_count = 0

    @classmethod
    def from_snapshot(cls, snapshot: tuple[tuple[Stone, ...], ...]) -> "Board":
        """从不可变快照重建可搜索棋盘。

        AI 搜索会在副本上落子和撤销，不能直接修改正在进行的真实棋局。
        这里通过重新落子同时重建棋子计数，避免调用方手工维护内部字段。
        """
        size = len(snapshot)
        if size < 1 or any(len(row) != size for row in snapshot):
            raise ValueError("Board snapshot must be a non-empty square")

        board = cls(size)
        for row_index, row in enumerate(snapshot):
            for col_index, stone in enumerate(row):
                if stone is not Stone.EMPTY:
                    board.place(row_index, col_index, stone)
        return board

    @property
    def size(self) -> int:
        """返回棋盘单边格数。"""
        return self._size

    @property
    def stone_count(self) -> int:
        """返回当前棋盘上的棋子总数。"""
        return self._stone_count

    def in_bounds(self, row: int, col: int) -> bool:
        """判断坐标是否落在棋盘范围内。"""
        return 0 <= row < self._size and 0 <= col < self._size

    def stone_at(self, row: int, col: int) -> Stone:
        """读取指定格子；越界时抛出 ``OutOfBoundsError``。"""
        self._require_in_bounds(row, col)
        return self._cells[row][col]

    def is_empty(self, row: int, col: int) -> bool:
        """判断指定格子是否为空。"""
        return self.stone_at(row, col) is Stone.EMPTY

    def place(self, row: int, col: int, stone: Stone) -> None:
        """放置棋子。

        越界、空格子棋种或重复落子都会在修改棋盘前失败，保证失败操作不会
        留下部分更新。
        """
        self._require_in_bounds(row, col)
        if stone is Stone.EMPTY:
            raise InvalidStoneError("Cannot place an empty stone")
        if self._cells[row][col] is not Stone.EMPTY:
            raise OccupiedError(f"Position ({row}, {col}) is occupied")
        self._cells[row][col] = stone
        self._stone_count += 1

    def remove(self, row: int, col: int) -> Stone:
        """删除棋子并返回被删除的棋种，主要供悔棋和 AI 撤销使用。"""
        self._require_in_bounds(row, col)
        stone = self._cells[row][col]
        if stone is Stone.EMPTY:
            raise CellStateError(f"Position ({row}, {col}) is already empty")
        self._cells[row][col] = Stone.EMPTY
        self._stone_count -= 1
        return stone

    def is_full(self) -> bool:
        """判断棋盘是否已无空位。"""
        return self._stone_count == self._size * self._size

    def iter_empty(self) -> Iterator[tuple[int, int]]:
        """按行优先顺序遍历所有空位。"""
        for row in range(self._size):
            for col in range(self._size):
                if self._cells[row][col] is Stone.EMPTY:
                    yield row, col

    def snapshot(self) -> tuple[tuple[Stone, ...], ...]:
        """返回不可变棋盘快照，供 AI 请求和 UI 渲染读取。"""
        return tuple(tuple(row) for row in self._cells)

    def reset(self) -> None:
        """恢复为全空棋盘。"""
        for row in self._cells:
            row[:] = [Stone.EMPTY] * self._size
        self._stone_count = 0

    def _require_in_bounds(self, row: int, col: int) -> None:
        """内部边界检查，统一产生领域异常。"""
        if not self.in_bounds(row, col):
            raise OutOfBoundsError(f"Position ({row}, {col}) is outside the board")
