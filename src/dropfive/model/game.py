"""棋局状态转换与合法落子执行。"""

from enum import Enum

from dropfive.model.board import Board
from dropfive.model.errors import GameFinishedError, NoMoveToUndoError
from dropfive.model.history import Move, MoveHistory
from dropfive.model.stone import Stone
from dropfive.model.win_checker import WinChecker


class GameResult(Enum):
    """一局棋的最终结果状态。"""

    ONGOING = "ongoing"
    BLACK_WIN = "black_win"
    WHITE_WIN = "white_win"
    DRAW = "draw"

    @property
    def is_finished(self) -> bool:
        """除“进行中”之外的任何结果都表示本局已结束。"""
        return self is not GameResult.ONGOING


class GameEngine:
    """纯规则棋局引擎。

    该类不知道 tkinter、线程、人物姓名或颜色显示方式，只负责棋盘、轮次、
    历史、胜负和和棋。UI 通过快照读取状态，不能绕过引擎直接修改棋盘。
    """

    def __init__(self, board_size: int = 15) -> None:
        """创建一局黑方先行的新棋。"""
        self._board = Board(board_size)
        self._history = MoveHistory()
        self._current_stone = Stone.BLACK
        self._result = GameResult.ONGOING
        self._winning_line: tuple[tuple[int, int], ...] = ()

    @property
    def board(self) -> Board:
        """返回当前棋盘模型。"""
        return self._board

    @property
    def history(self) -> MoveHistory:
        """返回当前落子历史。"""
        return self._history

    @property
    def current_stone(self) -> Stone:
        """返回当前应落子的棋种。"""
        return self._current_stone

    @property
    def result(self) -> GameResult:
        """返回当前棋局结果。"""
        return self._result

    @property
    def winning_line(self) -> tuple[tuple[int, int], ...]:
        """返回获胜的连续棋子坐标；未获胜时为空元组。"""
        return self._winning_line

    @property
    def is_over(self) -> bool:
        """判断棋局是否已经结束。"""
        return self._result.is_finished

    def play(self, row: int, col: int) -> Move:
        """执行一步合法落子并推进棋局。

        处理顺序固定为“规则校验 → 写入棋盘 → 记录历史 → 胜负判断 →
        和棋判断 → 切换回合”。该顺序保证最后一手能够被胜负检测读取。
        """
        if self.is_over:
            raise GameFinishedError("The game has already finished")

        self._board.place(row, col, self._current_stone)
        move = self._history.push(row, col, self._current_stone)
        winning_line = WinChecker.winning_line_from_last_move(self._board, row, col)

        if winning_line:
            self._winning_line = winning_line
            if self._current_stone is Stone.BLACK:
                self._result = GameResult.BLACK_WIN
            else:
                self._result = GameResult.WHITE_WIN
        elif self._board.is_full():
            self._result = GameResult.DRAW
        else:
            self._current_stone = self._current_stone.opponent
        return move

    def undo(self) -> Move:
        """撤销最后一手并恢复落子方、进行中状态和棋盘内容。"""
        if self._history.is_empty:
            raise NoMoveToUndoError("There are no moves to undo")

        move = self._history.pop()
        self._board.remove(move.row, move.col)
        self._current_stone = move.stone
        self._result = GameResult.ONGOING
        self._winning_line = ()
        return move

    def reset(self) -> None:
        """重置棋盘、历史、结果和先手方。"""
        self._board.reset()
        self._history.clear()
        self._current_stone = Stone.BLACK
        self._result = GameResult.ONGOING
        self._winning_line = ()
