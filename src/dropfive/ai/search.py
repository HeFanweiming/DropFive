"""带时间上限、置换表和强制胜搜索的 Alpha-Beta。

单步搜索按以下顺序执行：

1. 立即获胜；
2. 封堵对手立即获胜；
3. VCF 连续冲四强制胜；
4. 可选地检查对手强制胜并提前防守；
5. 迭代加深 Alpha-Beta。

前置战术层比普通启发式搜索更可靠，也能在很短时间内发现多步必胜线路。
"""

import contextlib
import random
import time
from dataclasses import dataclass

from dropfive.ai.difficulty import DifficultyConfig
from dropfive.ai.evaluator import WIN_SCORE, Evaluator
from dropfive.ai.move_generator import MoveGenerator
from dropfive.model.board import Board
from dropfive.model.stone import Stone
from dropfive.model.win_checker import WinChecker

_INFINITY = WIN_SCORE * 2


@dataclass(frozen=True, slots=True)
class SearchResult:
    """一次搜索的落点、评分、完成深度和运行统计。"""

    move: tuple[int, int] | None
    score: int
    depth: int
    nodes: int
    elapsed: float
    reason: str


@dataclass(slots=True)
class _TableEntry:
    """置换表项。

    ``flag`` 使用 Alpha-Beta 常见语义：

    * ``exact``：该深度下得到精确值；
    * ``lower``：真实值不小于当前记录；
    * ``upper``：真实值不大于当前记录。
    """

    depth: int
    score: int
    flag: str
    best_move: tuple[int, int] | None


class _SearchTimeout(Exception):
    pass


class _Deadline:
    """使用单调时钟执行可中断的时间检查。"""

    def __init__(self, seconds: float) -> None:
        """记录当前时刻加上允许的搜索秒数。"""
        self._deadline = time.perf_counter() + seconds

    def check(self) -> None:
        """超时后抛出内部异常，由根搜索捕获并返回已完成深度结果。"""
        if time.perf_counter() >= self._deadline:
            raise _SearchTimeout


class AlphaBetaSearch:
    """一次搜索请求对应的有状态搜索器。"""

    def __init__(self, config: DifficultyConfig) -> None:
        """创建评估器、候选生成器和空置换表。"""
        self._config = config
        self._evaluator = Evaluator()
        self._generator = MoveGenerator(self._evaluator, config.candidate_limit)
        self._nodes = 0
        self._table: dict[tuple[int, int], _TableEntry] = {}
        self._zobrist: list[list[list[int]]] = []

    def search(
        self,
        board: Board,
        stone: Stone,
        policy_priors: dict[tuple[int, int], float] | None = None,
    ) -> SearchResult:
        """执行完整战术与 Alpha-Beta 搜索。

        ``policy_priors`` 是可选 ONNX 概率。模型先验只影响根节点候选扩展
        和排序，不会绕过立即胜负、VCF 或搜索评分。
        """
        started = time.perf_counter()
        self._nodes = 0
        self._table.clear()
        self._prepare_zobrist(board.size)

        winning_moves = self._evaluator.find_winning_moves(board, stone)
        if winning_moves:
            # 直接成五优先级最高，不需要进入昂贵搜索。
            return SearchResult(
                move=winning_moves[0],
                score=WIN_SCORE,
                depth=0,
                nodes=0,
                elapsed=time.perf_counter() - started,
                reason="immediate_win",
            )

        opponent_wins = self._evaluator.find_winning_moves(board, stone.opponent)
        if opponent_wins:
            # 若对手下一手能赢，先占据其一端；双活四等无法全堵的情况仍交给搜索。
            return SearchResult(
                move=opponent_wins[0],
                score=0,
                depth=0,
                nodes=0,
                elapsed=time.perf_counter() - started,
                reason="block_win",
            )

        vcf_deadline = _Deadline(min(0.3, self._config.time_limit * 0.25))
        forced_win: tuple[int, int] | None = None
        with contextlib.suppress(_SearchTimeout):
            forced_win = self._find_forced_win(
                board,
                stone,
                self._config.vcf_depth,
                vcf_deadline,
            )
        if forced_win is not None:
            # VCF 找到的线路已经验证过对手每步都必须防守，可直接返回。
            return SearchResult(
                move=forced_win,
                score=WIN_SCORE,
                depth=0,
                nodes=self._nodes,
                elapsed=time.perf_counter() - started,
                reason="forced_win",
            )

        if self._config.defensive_vcf:
            # 主动寻找对手的连续冲四线路，并抢占其首个关键发起点。
            defense_deadline = _Deadline(min(0.5, self._config.time_limit * 0.2))
            opponent_force: tuple[int, int] | None = None
            with contextlib.suppress(_SearchTimeout):
                opponent_force = self._find_forced_win(
                    board,
                    stone.opponent,
                    self._config.vcf_depth,
                    defense_deadline,
                )
            if opponent_force is not None:
                return SearchResult(
                    move=opponent_force,
                    score=0,
                    depth=0,
                    nodes=self._nodes,
                    elapsed=time.perf_counter() - started,
                    reason="block_forced_win",
                )

        candidates = self._generator.generate(board, stone)
        if not candidates:
            return SearchResult(
                move=None,
                score=0,
                depth=0,
                nodes=0,
                elapsed=time.perf_counter() - started,
                reason="no_candidate",
            )

        position_hash = self._hash_board(board)
        remaining_time = max(0.05, self._config.time_limit - (time.perf_counter() - started))
        deadline = _Deadline(remaining_time)
        best_move = candidates[0]
        best_score = -_INFINITY
        completed_depth = 0
        for depth in range(1, self._config.depth + 1):
            try:
                move, score = self._search_root(
                    board,
                    stone,
                    depth,
                    deadline,
                    position_hash,
                    best_move,
                    policy_priors,
                )
            except _SearchTimeout:
                break
            best_move = move
            best_score = score
            completed_depth = depth
            self._table[(position_hash, stone.value)] = _TableEntry(
                depth=depth,
                score=score,
                flag="exact",
                best_move=move,
            )
            if score >= WIN_SCORE:
                break

        return SearchResult(
            move=best_move,
            score=best_score,
            depth=completed_depth,
            nodes=self._nodes,
            elapsed=time.perf_counter() - started,
            reason="search" if completed_depth else "fallback_candidate",
        )

    def _find_forced_win(
        self,
        board: Board,
        stone: Stone,
        depth: int,
        deadline: _Deadline,
    ) -> tuple[int, int] | None:
        """递归搜索连续冲四强制胜线路。

        每一步只考虑能制造“下一手必胜点”的落子。若制造出两个或更多必胜
        点，且对手没有立即反赢，则对手无法同时封堵；若只有一个必胜点，
        对手必然落子封堵，再递归寻找下一条冲四。
        """
        if depth <= 0:
            return None
        deadline.check()

        winning_moves = self._evaluator.find_winning_moves(board, stone)
        if winning_moves:
            return winning_moves[0]

        forcing_moves: list[tuple[tuple[int, int], set[tuple[int, int]]]] = []
        for move in self._generator.generate(board, stone):
            deadline.check()
            points = self._evaluator.winning_points_after_move(board, move[0], move[1], stone)
            if points:
                forcing_moves.append((move, points))
        # 先尝试双威胁，再尝试单点冲四，通常能更快找到强制胜。
        forcing_moves.sort(key=lambda item: len(item[1]), reverse=True)

        for move, points in forcing_moves:
            deadline.check()
            row, col = move
            board.place(row, col, stone)
            try:
                opponent_wins = self._evaluator.find_winning_moves(board, stone.opponent)
                if opponent_wins:
                    # 对手可以忽略当前威胁直接获胜，这条强制线路失败。
                    continue
                if len(points) >= 2:
                    return move

                block = next(iter(points))
                board.place(block[0], block[1], stone.opponent)
                try:
                    if (
                        WinChecker.winner_from_last_move(board, block[0], block[1])
                        is stone.opponent
                    ):
                        continue
                    if self._find_forced_win(board, stone, depth - 1, deadline) is not None:
                        return move
                finally:
                    board.remove(block[0], block[1])
            finally:
                board.remove(row, col)
        return None

    def _search_root(
        self,
        board: Board,
        stone: Stone,
        depth: int,
        deadline: _Deadline,
        position_hash: int,
        preferred_move: tuple[int, int],
        policy_priors: dict[tuple[int, int], float] | None,
    ) -> tuple[tuple[int, int], int]:
        """完成一个迭代加深层级的根节点搜索。"""
        best_move = preferred_move
        best_score = -_INFINITY
        alpha = -_INFINITY

        candidates = self._ordered_candidates(board, stone, preferred_move)
        if policy_priors:
            candidates = self._apply_policy_priors(
                candidates,
                board,
                policy_priors,
                preferred_move,
            )
        for row, col in candidates:
            deadline.check()
            child_hash = position_hash ^ self._zobrist[row][col][stone.value]
            board.place(row, col, stone)
            try:
                if WinChecker.winner_from_last_move(board, row, col) is stone:
                    score = WIN_SCORE
                elif depth == 1:
                    score = self._evaluator.evaluate_board(board, stone)
                else:
                    score = self._minimax(
                        board,
                        stone.opponent,
                        depth - 1,
                        alpha,
                        _INFINITY,
                        stone,
                        deadline,
                        child_hash,
                    )
            finally:
                board.remove(row, col)

            self._nodes += 1
            if score > best_score:
                best_score = score
                best_move = (row, col)
            alpha = max(alpha, best_score)
        return best_move, best_score

    def _minimax(
        self,
        board: Board,
        stone: Stone,
        depth: int,
        alpha: int,
        beta: int,
        perspective: Stone,
        deadline: _Deadline,
        position_hash: int,
    ) -> int:
        """Alpha-Beta 递归主体。

        AI 层取最大值，对手层取最小值；叶子使用固定 AI 视角评估，因此
        正负号不会在递归中意外翻转。
        """
        if depth == 0:
            return self._evaluator.evaluate_board(board, perspective)

        key = (position_hash, stone.value)
        entry = self._table.get(key)
        preferred_move = entry.best_move if entry is not None else None
        if entry is not None and entry.depth >= depth:
            # 更深或同等深度的缓存值足以回答当前浅层查询。
            if entry.flag == "exact":
                return entry.score
            if entry.flag == "lower":
                alpha = max(alpha, entry.score)
            else:
                beta = min(beta, entry.score)
            if alpha >= beta:
                return entry.score

        original_alpha = alpha
        original_beta = beta
        maximizing = stone is perspective
        score = -_INFINITY if maximizing else _INFINITY
        best_move: tuple[int, int] | None = None

        for row, col in self._ordered_candidates(board, stone, preferred_move):
            deadline.check()
            child_hash = position_hash ^ self._zobrist[row][col][stone.value]
            board.place(row, col, stone)
            try:
                if WinChecker.winner_from_last_move(board, row, col) is stone:
                    value = WIN_SCORE if maximizing else -WIN_SCORE
                else:
                    value = self._minimax(
                        board,
                        stone.opponent,
                        depth - 1,
                        alpha,
                        beta,
                        perspective,
                        deadline,
                        child_hash,
                    )
            finally:
                board.remove(row, col)

            self._nodes += 1
            if maximizing:
                if value > score:
                    score = value
                    best_move = (row, col)
                alpha = max(alpha, score)
            else:
                if value < score:
                    score = value
                    best_move = (row, col)
                beta = min(beta, score)
            if alpha >= beta:
                # 当前分支已经无法影响父节点选择，可以安全剪枝。
                break

        if score <= original_alpha:
            flag = "upper"
        elif score >= original_beta:
            flag = "lower"
        else:
            flag = "exact"
        self._table[key] = _TableEntry(
            depth=depth,
            score=score,
            flag=flag,
            best_move=best_move,
        )
        return score

    def _ordered_candidates(
        self,
        board: Board,
        stone: Stone,
        preferred_move: tuple[int, int] | None,
    ) -> list[tuple[int, int]]:
        """生成候选并把上一层最佳着法放到最前，改善剪枝效率。"""
        candidates = self._generator.generate(board, stone)
        if preferred_move in candidates:
            candidates.remove(preferred_move)
            candidates.insert(0, preferred_move)
        return candidates

    @staticmethod
    def _apply_policy_priors(
        candidates: list[tuple[int, int]],
        board: Board,
        priors: dict[tuple[int, int], float],
        preferred_move: tuple[int, int],
    ) -> list[tuple[int, int]]:
        """使用 ONNX 策略概率重排根节点候选。

        空棋盘不加入模型给出的远端点，避免破坏天元开局；非空棋盘只扩展
        已有棋子两格范围内的高概率位置。
        """
        if board.stone_count == 0:
            return candidates
        prior_moves = [
            move
            for move in sorted(priors, key=priors.get, reverse=True)
            if board.is_empty(*move) and AlphaBetaSearch._is_local_move(board, move)
        ][:4]
        combined = list(dict.fromkeys([*candidates, *prior_moves]))
        combined.sort(key=lambda move: priors.get(move, -1.0), reverse=True)
        if preferred_move in combined:
            combined.remove(preferred_move)
            combined.insert(0, preferred_move)
        return combined

    @staticmethod
    def _is_local_move(board: Board, move: tuple[int, int]) -> bool:
        """判断一个点是否靠近已有棋子，属于合理的局部候选。"""
        row, col = move
        for next_row in range(max(0, row - 2), min(board.size, row + 3)):
            for next_col in range(max(0, col - 2), min(board.size, col + 3)):
                if board.stone_at(next_row, next_col) is not Stone.EMPTY:
                    return True
        return False

    def _prepare_zobrist(self, size: int) -> None:
        """按棋盘尺寸生成稳定的 Zobrist 随机表。"""
        if len(self._zobrist) == size:
            return
        rng = random.Random(0xD20F1E)
        self._zobrist = [
            [[rng.getrandbits(64) for _ in range(3)] for _ in range(size)] for _ in range(size)
        ]

    def _hash_board(self, board: Board) -> int:
        """计算当前棋盘异或哈希；搜索落子和撤销时同步异或即可 O(1) 更新。"""
        position_hash = 0
        for row in range(board.size):
            for col in range(board.size):
                stone = board.stone_at(row, col)
                if stone is not Stone.EMPTY:
                    position_hash ^= self._zobrist[row][col][stone.value]
        return position_hash
