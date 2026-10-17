"""Game state transitions and legal move execution."""

from enum import Enum

from dropfive.model.board import Board
from dropfive.model.errors import GameFinishedError, NoMoveToUndoError
from dropfive.model.history import Move, MoveHistory
from dropfive.model.stone import Stone
from dropfive.model.win_checker import WinChecker


class GameResult(Enum):
    ONGOING = "ongoing"
    BLACK_WIN = "black_win"
    WHITE_WIN = "white_win"
    DRAW = "draw"

    @property
    def is_finished(self) -> bool:
        return self is not GameResult.ONGOING


class GameEngine:
    """Own the board, turn, result, and move history for one game."""

    def __init__(self, board_size: int = 15) -> None:
        self._board = Board(board_size)
        self._history = MoveHistory()
        self._current_stone = Stone.BLACK
        self._result = GameResult.ONGOING
        self._winning_line: tuple[tuple[int, int], ...] = ()

    @property
    def board(self) -> Board:
        return self._board

    @property
    def history(self) -> MoveHistory:
        return self._history

    @property
    def current_stone(self) -> Stone:
        return self._current_stone

    @property
    def result(self) -> GameResult:
        return self._result

    @property
    def winning_line(self) -> tuple[tuple[int, int], ...]:
        return self._winning_line

    @property
    def is_over(self) -> bool:
        return self._result.is_finished

    def play(self, row: int, col: int) -> Move:
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
        if self._history.is_empty:
            raise NoMoveToUndoError("There are no moves to undo")

        move = self._history.pop()
        self._board.remove(move.row, move.col)
        self._current_stone = move.stone
        self._result = GameResult.ONGOING
        self._winning_line = ()
        return move

    def reset(self) -> None:
        self._board.reset()
        self._history.clear()
        self._current_stone = Stone.BLACK
        self._result = GameResult.ONGOING
        self._winning_line = ()
