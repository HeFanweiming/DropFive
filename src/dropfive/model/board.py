"""Two-dimensional board state with guarded mutations."""

from collections.abc import Iterator

from dropfive.model.errors import (
    CellStateError,
    InvalidStoneError,
    OccupiedError,
    OutOfBoundsError,
)
from dropfive.model.stone import Stone


class Board:
    """Store stones using row-major coordinates."""

    def __init__(self, size: int = 15) -> None:
        if size < 1:
            raise ValueError("Board size must be positive")
        self._size = size
        self._cells: list[list[Stone]] = [[Stone.EMPTY for _ in range(size)] for _ in range(size)]
        self._stone_count = 0

    @classmethod
    def from_snapshot(cls, snapshot: tuple[tuple[Stone, ...], ...]) -> "Board":
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
        return self._size

    @property
    def stone_count(self) -> int:
        return self._stone_count

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self._size and 0 <= col < self._size

    def stone_at(self, row: int, col: int) -> Stone:
        self._require_in_bounds(row, col)
        return self._cells[row][col]

    def is_empty(self, row: int, col: int) -> bool:
        return self.stone_at(row, col) is Stone.EMPTY

    def place(self, row: int, col: int, stone: Stone) -> None:
        self._require_in_bounds(row, col)
        if stone is Stone.EMPTY:
            raise InvalidStoneError("Cannot place an empty stone")
        if self._cells[row][col] is not Stone.EMPTY:
            raise OccupiedError(f"Position ({row}, {col}) is occupied")
        self._cells[row][col] = stone
        self._stone_count += 1

    def remove(self, row: int, col: int) -> Stone:
        self._require_in_bounds(row, col)
        stone = self._cells[row][col]
        if stone is Stone.EMPTY:
            raise CellStateError(f"Position ({row}, {col}) is already empty")
        self._cells[row][col] = Stone.EMPTY
        self._stone_count -= 1
        return stone

    def is_full(self) -> bool:
        return self._stone_count == self._size * self._size

    def iter_empty(self) -> Iterator[tuple[int, int]]:
        for row in range(self._size):
            for col in range(self._size):
                if self._cells[row][col] is Stone.EMPTY:
                    yield row, col

    def snapshot(self) -> tuple[tuple[Stone, ...], ...]:
        return tuple(tuple(row) for row in self._cells)

    def reset(self) -> None:
        for row in self._cells:
            row[:] = [Stone.EMPTY] * self._size
        self._stone_count = 0

    def _require_in_bounds(self, row: int, col: int) -> None:
        if not self.in_bounds(row, col):
            raise OutOfBoundsError(f"Position ({row}, {col}) is outside the board")
