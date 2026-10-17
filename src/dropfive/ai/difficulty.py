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
        depth=2,
        candidate_limit=8,
        time_limit=0.35,
        randomness=0.25,
    ),
    Difficulty.MEDIUM: DifficultyConfig(
        depth=3,
        candidate_limit=12,
        time_limit=0.7,
        randomness=0.0,
    ),
    Difficulty.HARD: DifficultyConfig(
        depth=5,
        candidate_limit=11,
        time_limit=1.4,
        randomness=0.0,
    ),
}


def get_difficulty_config(difficulty: Difficulty) -> DifficultyConfig:
    return _CONFIGS[difficulty]
