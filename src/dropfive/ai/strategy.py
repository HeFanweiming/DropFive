"""难度感知的 AI 策略门面。

策略层负责把棋盘快照、难度参数、可选 ONNX 先验和搜索结果组合在一起；
真正的棋局合法性仍由控制器和规则层负责。
"""

import random
from dataclasses import replace

from dropfive.ai.difficulty import Difficulty, get_difficulty_config
from dropfive.ai.evaluator import Evaluator
from dropfive.ai.move_generator import MoveGenerator
from dropfive.ai.onnx_policy import OnnxPolicyModel, policy_priors
from dropfive.ai.search import AlphaBetaSearch, SearchResult
from dropfive.model.board import Board
from dropfive.model.stone import Stone


class GomokuAI:
    """对上层提供单次 ``choose_move`` 调用的 AI 门面。"""

    def __init__(
        self,
        difficulty: Difficulty,
        *,
        rng: random.Random | None = None,
        policy_model: OnnxPolicyModel | None = None,
    ) -> None:
        """保存难度、随机源和可选神经网络模型。"""
        self._difficulty = difficulty
        self._config = get_difficulty_config(difficulty)
        self._rng = rng or random.Random()
        self._policy_model = policy_model
        self.last_model_error: str | None = None

    def choose_move(
        self,
        snapshot: tuple[tuple[Stone, ...], ...],
        stone: Stone,
    ) -> SearchResult:
        """为一个棋盘快照计算落点。

        ONNX 只负责提供候选先验。即使模型加载、推理或输出解析失败，也会
        记录错误后继续使用纯搜索 AI，保证人机功能不会因可选依赖而中断。
        """
        board = Board.from_snapshot(snapshot)
        priors = None
        if self._policy_model is not None:
            try:
                output = self._policy_model.infer(snapshot, stone)
                priors = policy_priors(output.logits, snapshot)
            except Exception as exc:
                # 模型属于可选增强，任何推理异常都应降级而不是中断棋局。
                self.last_model_error = str(exc)

        result = AlphaBetaSearch(self._config).search(board, stone, priors)
        if (
            self._difficulty is not Difficulty.EASY
            or result.reason != "search"
            or self._rng.random() >= self._config.randomness
        ):
            return result

        # 简单档只在普通搜索结果的前三个近似候选中轻微随机扰动。
        candidates = MoveGenerator(Evaluator(), 3).generate(board, stone)
        if not candidates:
            return result
        return replace(result, move=self._rng.choice(candidates), reason="easy_random")
