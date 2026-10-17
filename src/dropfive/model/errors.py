"""Domain errors raised by the core game model."""


class DropFiveError(Exception):
    """Base class for expected game errors."""


class OutOfBoundsError(DropFiveError, ValueError):
    """Raised when a board position is outside the playable area."""


class OccupiedError(DropFiveError, ValueError):
    """Raised when a move targets an occupied position."""


class InvalidStoneError(DropFiveError, ValueError):
    """Raised when an empty stone is used in a board mutation."""


class CellStateError(DropFiveError, ValueError):
    """Raised when a board mutation is inconsistent with the cell state."""


class GameFinishedError(DropFiveError):
    """Raised when a move is attempted after the game has finished."""


class NoMoveToUndoError(DropFiveError):
    """Raised when undo is requested without a recorded move."""
