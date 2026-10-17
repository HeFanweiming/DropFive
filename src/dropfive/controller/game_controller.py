"""UI-independent coordination around a single game session."""

from dataclasses import dataclass
from enum import Enum

from dropfive.model.errors import (
    GameFinishedError,
    NoMoveToUndoError,
    OccupiedError,
    OutOfBoundsError,
)
from dropfive.model.game import GameEngine, GameResult
from dropfive.model.history import Move
from dropfive.model.stone import Stone


@dataclass(frozen=True, slots=True)
class GameView:
    board: tuple[tuple[Stone, ...], ...]
    current_stone: Stone
    result: GameResult
    last_move: Move | None
    move_count: int


class ActionError(Enum):
    OUT_OF_BOUNDS = "out_of_bounds"
    OCCUPIED = "occupied"
    GAME_OVER = "game_over"
    NO_UNDO = "no_undo"


@dataclass(frozen=True, slots=True)
class ActionResult:
    ok: bool
    error: ActionError | None = None


class GameController:
    """Translate user commands into game operations and status snapshots."""

    def __init__(self, board_size: int = 15) -> None:
        self._engine = GameEngine(board_size)

    def play(self, row: int, col: int) -> ActionResult:
        try:
            self._engine.play(row, col)
        except GameFinishedError:
            return ActionResult(ok=False, error=ActionError.GAME_OVER)
        except OutOfBoundsError:
            return ActionResult(ok=False, error=ActionError.OUT_OF_BOUNDS)
        except OccupiedError:
            return ActionResult(ok=False, error=ActionError.OCCUPIED)
        return ActionResult(ok=True)

    def undo(self) -> ActionResult:
        try:
            self._engine.undo()
        except NoMoveToUndoError:
            return ActionResult(ok=False, error=ActionError.NO_UNDO)
        return ActionResult(ok=True)

    def restart(self) -> ActionResult:
        self._engine.reset()
        return ActionResult(ok=True)

    def view(self) -> GameView:
        return GameView(
            board=self._engine.board.snapshot(),
            current_stone=self._engine.current_stone,
            result=self._engine.result,
            last_move=self._engine.history.last,
            move_count=len(self._engine.history),
        )
