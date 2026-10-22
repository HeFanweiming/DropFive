"""与 UI 无关的棋局会话协调器。

控制器把“棋局规则”“当前模式”“AI 请求”“异步搜索版本号”放在同一层，
确保 UI 不需要理解 Alpha-Beta、线程或棋局内部数组。
"""

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
    """当前对局的操作模式。"""

    TWO_PLAYER = "two_player"
    HUMAN_VS_AI = "human_vs_ai"


class SearchPurpose(Enum):
    """后台搜索的用途：真正落子或只给出提示。"""

    AI_MOVE = "ai_move"
    HINT = "hint"


@dataclass(frozen=True, slots=True)
class GameView:
    """供 UI 安全读取的不可变棋局快照。"""

    board: tuple[tuple[Stone, ...], ...]
    current_stone: Stone
    result: GameResult
    last_move: Move | None
    move_count: int
    winning_cells: tuple[tuple[int, int], ...]
    mode: GameMode
    difficulty: Difficulty
    human_stone: Stone
    game_id: int
    is_ai_turn: bool
    can_human_play: bool
    can_request_hint: bool


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """一次后台 AI 搜索所需的全部输入。

    ``game_id`` 是异步竞态保护的关键：重开、悔棋或切换模式后，旧请求即使
    晚到也会因版本不匹配被拒绝，不能污染新棋局。
    """

    game_id: int
    board: tuple[tuple[Stone, ...], ...]
    stone: Stone
    difficulty: Difficulty
    purpose: SearchPurpose


class ActionError(Enum):
    """控制器向 UI 返回的稳定错误码。"""

    OUT_OF_BOUNDS = "out_of_bounds"
    OCCUPIED = "occupied"
    GAME_OVER = "game_over"
    NO_UNDO = "no_undo"
    NOT_YOUR_TURN = "not_your_turn"
    STALE_REQUEST = "stale_request"


@dataclass(frozen=True, slots=True)
class ActionResult:
    """一次用户操作的轻量结果，不包含 UI 文案。"""

    ok: bool
    error: ActionError | None = None


class GameController:
    """协调一局棋中的玩家、AI、模式和搜索请求。"""

    def __init__(
        self,
        board_size: int = 15,
        *,
        mode: GameMode = GameMode.TWO_PLAYER,
        difficulty: Difficulty = Difficulty.HARD,
        human_stone: Stone = Stone.BLACK,
    ) -> None:
        """创建棋局并确定人类与 AI 各执何色。"""
        if human_stone is Stone.EMPTY:
            raise ValueError("Human stone cannot be empty")
        self._engine = GameEngine(board_size)
        self._mode = mode
        self._difficulty = difficulty
        self._human_stone = human_stone
        self._ai_stone = human_stone.opponent
        self._game_id = 1

    @property
    def is_ai_turn(self) -> bool:
        """当前是否应由 AI 落子。"""
        return (
            self._mode is GameMode.HUMAN_VS_AI
            and not self._engine.is_over
            and self._engine.current_stone is self._ai_stone
        )

    @property
    def can_human_play(self) -> bool:
        """棋盘当前是否允许人类点击落子。"""
        return not self._engine.is_over and (
            self._mode is GameMode.TWO_PLAYER or self._engine.current_stone is not self._ai_stone
        )

    @property
    def can_request_hint(self) -> bool:
        """当前是否允许请求提示。"""
        return not self._engine.is_over and not self.is_ai_turn

    def play(self, row: int, col: int) -> ActionResult:
        """尝试执行人类落子，并把领域异常转换为操作错误码。"""
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
        """提交后台 AI 结果；旧 ``game_id`` 的结果会被直接拒绝。"""
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
        """模型或搜索失败时，在当前 AI 回合落一个备用合法空位。"""
        if game_id != self._game_id:
            return ActionResult(ok=False, error=ActionError.STALE_REQUEST)
        if not self.is_ai_turn:
            return ActionResult(ok=False, error=ActionError.NOT_YOUR_TURN)

        for row, col in self._engine.board.iter_empty():
            self._engine.play(row, col)
            return ActionResult(ok=True)
        return ActionResult(ok=False, error=ActionError.GAME_OVER)

    def undo(self) -> ActionResult:
        """执行悔棋。

        双人模式撤销一手；人机模式若最后一步来自 AI，则同时撤销 AI 与玩家
        的一手，让玩家重新思考。任何悔棋都会推进 ``game_id`` 使旧搜索失效。
        """
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
        """清空当前棋局并推进版本号。"""
        self._engine.reset()
        self._game_id += 1
        return ActionResult(ok=True)

    def set_mode(self, mode: GameMode) -> ActionResult:
        """切换模式；模式变化会重置棋盘并创建新的搜索版本。"""
        if mode is not self._mode:
            self._mode = mode
            self._engine.reset()
            self._game_id += 1
        return ActionResult(ok=True)

    def set_difficulty(self, difficulty: Difficulty) -> ActionResult:
        """切换难度；不改动棋盘，但会让已在途的提示/搜索结果失效。"""
        if difficulty is not self._difficulty:
            self._difficulty = difficulty
            self._game_id += 1
        return ActionResult(ok=True)

    def make_search_request(self, purpose: SearchPurpose) -> SearchRequest | None:
        """在状态允许时创建不可变搜索请求，否则返回 ``None``。"""
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
        """生成 UI 只读快照，并在此处推导当前回合权限。"""
        return GameView(
            board=self._engine.board.snapshot(),
            current_stone=self._engine.current_stone,
            result=self._engine.result,
            last_move=self._engine.history.last,
            move_count=len(self._engine.history),
            winning_cells=self._engine.winning_line,
            mode=self._mode,
            difficulty=self._difficulty,
            human_stone=self._human_stone,
            game_id=self._game_id,
            is_ai_turn=self.is_ai_turn,
            can_human_play=self.can_human_play,
            can_request_hint=self.can_request_hint,
        )
