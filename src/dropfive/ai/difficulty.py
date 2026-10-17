"""Difficulty presets for the search-based AI."""

from dataclasses import dataclass
from enum import Enum


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass(frozen=True, slots=True)
class DifficultyConfig:
    depth: int
    candidate_limit: int
    time_limit: float
    randomness: float


_CONFIGS = {
    Difficulty.EASY: DifficultyConfig(
        depth=1,
        candidate_limit=6,
        time_limit=0.18,
        randomness=0.45,
    ),
    Difficulty.MEDIUM: DifficultyConfig(
        depth=2,
        candidate_limit=10,
        time_limit=0.45,
        randomness=0.0,
    ),
    Difficulty.HARD: DifficultyConfig(
        depth=4,
        candidate_limit=12,
        time_limit=0.9,
        randomness=0.0,
    ),
}


def get_difficulty_config(difficulty: Difficulty) -> DifficultyConfig:
    return _CONFIGS[difficulty]
