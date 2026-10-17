"""Move history used for undo and presentation."""

from dataclasses import dataclass

from dropfive.model.errors import NoMoveToUndoError
from dropfive.model.stone import Stone


@dataclass(frozen=True, slots=True)
class Move:
    row: int
    col: int
    stone: Stone
    number: int


class MoveHistory:
    """Append-only move records with explicit undo support."""

    def __init__(self) -> None:
        self._moves: list[Move] = []

    def __len__(self) -> int:
        return len(self._moves)

    @property
    def is_empty(self) -> bool:
        return not self._moves

    @property
    def last(self) -> Move | None:
        return self._moves[-1] if self._moves else None

    @property
    def moves(self) -> tuple[Move, ...]:
        return tuple(self._moves)

    def push(self, row: int, col: int, stone: Stone) -> Move:
        move = Move(row=row, col=col, stone=stone, number=len(self._moves) + 1)
        self._moves.append(move)
        return move

    def pop(self) -> Move:
        if not self._moves:
            raise NoMoveToUndoError("There are no moves to undo")
        return self._moves.pop()

    def clear(self) -> None:
        self._moves.clear()
