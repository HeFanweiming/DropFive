"""Difficulty-aware AI strategy facade."""

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
    def __init__(
        self,
        difficulty: Difficulty,
        *,
        rng: random.Random | None = None,
        policy_model: OnnxPolicyModel | None = None,
    ) -> None:
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
        board = Board.from_snapshot(snapshot)
        priors = None
        if self._policy_model is not None:
            try:
                output = self._policy_model.infer(snapshot, stone)
                priors = policy_priors(output.logits, snapshot)
            except Exception as exc:
                self.last_model_error = str(exc)

        result = AlphaBetaSearch(self._config).search(board, stone, priors)
        if (
            self._difficulty is not Difficulty.EASY
            or result.reason != "search"
            or self._rng.random() >= self._config.randomness
        ):
            return result

        candidates = MoveGenerator(Evaluator(), 3).generate(board, stone)
        if not candidates:
            return result
        return replace(result, move=self._rng.choice(candidates), reason="easy_random")
