"""Stone values used by the game model."""

from enum import IntEnum


class Stone(IntEnum):
    """The three stable cell states on a Gomoku board."""

    EMPTY = 0
    BLACK = 1
    WHITE = 2

    @property
    def opponent(self) -> "Stone":
        """Return the opposing stone."""

        if self is Stone.BLACK:
            return Stone.WHITE
        if self is Stone.WHITE:
            return Stone.BLACK
        raise ValueError("An empty cell has no opponent stone")
