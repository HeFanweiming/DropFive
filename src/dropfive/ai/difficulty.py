"""Difficulty presets for the search-based AI."""

from dataclasses import dataclass
from enum import Enum


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MASTER = "master"


@dataclass(frozen=True, slots=True)
class DifficultyConfig:
    depth: int
    candidate_limit: int
    time_limit: float
    randomness: float
    vcf_depth: int
    defensive_vcf: bool


_CONFIGS = {
    Difficulty.EASY: DifficultyConfig(
        depth=2,
        candidate_limit=8,
        time_limit=0.35,
        randomness=0.25,
        vcf_depth=2,
        defensive_vcf=False,
    ),
    Difficulty.MEDIUM: DifficultyConfig(
        depth=5,
        candidate_limit=11,
        time_limit=1.4,
        randomness=0.0,
        vcf_depth=4,
        defensive_vcf=True,
    ),
    Difficulty.HARD: DifficultyConfig(
        depth=6,
        candidate_limit=12,
        time_limit=2.4,
        randomness=0.0,
        vcf_depth=6,
        defensive_vcf=True,
    ),
    Difficulty.MASTER: DifficultyConfig(
        depth=8,
        candidate_limit=10,
        time_limit=5.0,
        randomness=0.0,
        vcf_depth=8,
        defensive_vcf=True,
    ),
}


def get_difficulty_config(difficulty: Difficulty) -> DifficultyConfig:
    return _CONFIGS[difficulty]
