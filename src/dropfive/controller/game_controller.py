"""UI-independent coordination around a game session."""

from dataclasses import dataclass
from enum import Enum

from dropfive.ai.difficulty import Difficulty
from dropfive.model.errors import (
    GameFinishedError,
    OccupiedError,
    OutOfBoundsError,
)
from dropfive.model.game import GameEngine, GameResult
from dropfive.model.history import Move
from dropfive.model.stone import Stone


class GameMode(Enum):
    TWO_PLAYER = "two_player"
    HUMAN_VS_AI = "human_vs_ai"


class SearchPurpose(Enum):
    AI_MOVE = "ai_move"
    HINT = "hint"


@dataclass(frozen=True, slots=True)
class GameView:
    board: tuple[tuple[Stone, ...], ...]
    current_stone: Stone
    result: GameResult
    last_move: Move | None
    move_count: int
    winning_cells: tuple[tuple[int, int], ...]
    mode: GameMode
    difficulty: Difficulty
    game_id: int
    is_ai_turn: bool
    can_human_play: bool
    can_request_hint: bool


@dataclass(frozen=True, slots=True)
class SearchRequest:
    game_id: int
    board: tuple[tuple[Stone, ...], ...]
    stone: Stone
    difficulty: Difficulty
    purpose: SearchPurpose


class ActionError(Enum):
    OUT_OF_BOUNDS = "out_of_bounds"
    OCCUPIED = "occupied"
    GAME_OVER = "game_over"
    NO_UNDO = "no_undo"
    NOT_YOUR_TURN = "not_your_turn"
    STALE_REQUEST = "stale_request"


@dataclass(frozen=True, slots=True)
class ActionResult:
    ok: bool
    error: ActionError | None = None


class GameController:
    """Coordinate turns, modes, and search requests for one game session."""

    def __init__(
        self,
        board_size: int = 15,
        *,
        mode: GameMode = GameMode.TWO_PLAYER,
        difficulty: Difficulty = Difficulty.HARD,
    ) -> None:
        self._engine = GameEngine(board_size)
        self._mode = mode
        self._difficulty = difficulty
        self._ai_stone = Stone.WHITE
        self._game_id = 1

    @property
    def is_ai_turn(self) -> bool:
        return (
            self._mode is GameMode.HUMAN_VS_AI
            and not self._engine.is_over
            and self._engine.current_stone is self._ai_stone
        )

    @property
    def can_human_play(self) -> bool:
        return not self._engine.is_over and (
            self._mode is GameMode.TWO_PLAYER or self._engine.current_stone is not self._ai_stone
        )

    @property
    def can_request_hint(self) -> bool:
        return not self._engine.is_over and not self.is_ai_turn

    def play(self, row: int, col: int) -> ActionResult:
        if self.is_ai_turn:
            return ActionResult(ok=False, error=ActionError.NOT_YOUR_TURN)
        try:
            self._engine.play(row, col)
        except GameFinishedError:
            return ActionResult(ok=False, error=ActionError.GAME_OVER)
        except OutOfBoundsError:
            return ActionResult(ok=False, error=ActionError.OUT_OF_BOUNDS)
        except OccupiedError:
            return ActionResult(ok=False, error=ActionError.OCCUPIED)
        return ActionResult(ok=True)

    def play_ai_move(self, row: int, col: int, game_id: int) -> ActionResult:
        if game_id != self._game_id:
            return ActionResult(ok=False, error=ActionError.STALE_REQUEST)
        if not self.is_ai_turn:
            return ActionResult(ok=False, error=ActionError.NOT_YOUR_TURN)
        try:
            self._engine.play(row, col)
        except GameFinishedError:
            return ActionResult(ok=False, error=ActionError.GAME_OVER)
        except OutOfBoundsError:
            return ActionResult(ok=False, error=ActionError.OUT_OF_BOUNDS)
        except OccupiedError:
            return ActionResult(ok=False, error=ActionError.OCCUPIED)
        return ActionResult(ok=True)

    def apply_ai_fallback(self, game_id: int) -> ActionResult:
        if game_id != self._game_id:
            return ActionResult(ok=False, error=ActionError.STALE_REQUEST)
        if not self.is_ai_turn:
            return ActionResult(ok=False, error=ActionError.NOT_YOUR_TURN)

        for row, col in self._engine.board.iter_empty():
            self._engine.play(row, col)
            return ActionResult(ok=True)
        return ActionResult(ok=False, error=ActionError.GAME_OVER)

    def undo(self) -> ActionResult:
        if self._engine.history.is_empty:
            return ActionResult(ok=False, error=ActionError.NO_UNDO)

        undone = self._engine.undo()
        if (
            self._mode is GameMode.HUMAN_VS_AI
            and undone.stone is self._ai_stone
            and not self._engine.history.is_empty
        ):
            self._engine.undo()
        self._game_id += 1
        return ActionResult(ok=True)

    def restart(self) -> ActionResult:
        self._engine.reset()
        self._game_id += 1
        return ActionResult(ok=True)

    def set_mode(self, mode: GameMode) -> ActionResult:
        if mode is not self._mode:
            self._mode = mode
            self._engine.reset()
            self._game_id += 1
        return ActionResult(ok=True)

    def set_difficulty(self, difficulty: Difficulty) -> ActionResult:
        if difficulty is not self._difficulty:
            self._difficulty = difficulty
            self._game_id += 1
        return ActionResult(ok=True)

    def make_search_request(self, purpose: SearchPurpose) -> SearchRequest | None:
        if purpose is SearchPurpose.AI_MOVE:
            if not self.is_ai_turn:
                return None
        elif not self.can_request_hint:
            return None

        return SearchRequest(
            game_id=self._game_id,
            board=self._engine.board.snapshot(),
            stone=self._engine.current_stone,
            difficulty=self._difficulty,
            purpose=purpose,
        )

    def view(self) -> GameView:
        return GameView(
            board=self._engine.board.snapshot(),
            current_stone=self._engine.current_stone,
            result=self._engine.result,
            last_move=self._engine.history.last,
            move_count=len(self._engine.history),
            winning_cells=self._engine.winning_line,
            mode=self._mode,
            difficulty=self._difficulty,
            game_id=self._game_id,
            is_ai_turn=self.is_ai_turn,
            can_human_play=self.can_human_play,
            can_request_hint=self.can_request_hint,
        )
