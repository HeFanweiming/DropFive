"""AI 候选点生成与启发式排序。"""

from dropfive.ai.evaluator import Evaluator
from dropfive.model.board import Board
from dropfive.model.stone import Stone


class MoveGenerator:
    """限制搜索宽度，同时保留已有棋子附近最值得检查的位置。"""

    def __init__(self, evaluator: Evaluator, candidate_limit: int) -> None:
        """保存评分器和每层最大候选数。"""
        self._evaluator = evaluator
        self._candidate_limit = candidate_limit

    def generate(self, board: Board, stone: Stone) -> list[tuple[int, int]]:
        """生成降序排列的候选落点。

        空棋盘固定返回天元。非空棋盘只考虑已有棋子周围两格范围，以减少
        Alpha-Beta 分支；若过滤后为空，则退回全部空位，绝不把“无候选”
        误判为棋盘已满。
        """
        if board.stone_count == 0:
            center = board.size // 2
            return [(center, center)]

        candidates: set[tuple[int, int]] = set()
        for row in range(board.size):
            for col in range(board.size):
                if board.stone_at(row, col) is Stone.EMPTY:
                    continue
                for next_row in range(max(0, row - 2), min(board.size, row + 3)):
                    for next_col in range(max(0, col - 2), min(board.size, col + 3)):
                        if board.is_empty(next_row, next_col):
                            candidates.add((next_row, next_col))

        if not candidates:
            candidates.update(board.iter_empty())

        scored = [
            # 分数相同或接近时，优先靠近棋盘中心的点，减少边缘开局偏差。
            (
                self._evaluator.candidate_score(board, row, col, stone),
                -self._center_distance(board, row, col),
                row,
                col,
            )
            for row, col in candidates
        ]
        scored.sort(reverse=True)
        return [(row, col) for _, _, row, col in scored[: self._candidate_limit]]

    @staticmethod
    def _center_distance(board: Board, row: int, col: int) -> float:
        """使用曼哈顿距离衡量落点与棋盘中心的偏离程度。"""
        center = (board.size - 1) / 2
        return abs(row - center) + abs(col - center)
