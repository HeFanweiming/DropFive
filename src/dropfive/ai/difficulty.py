"""四档 AI 的参数配置。"""

from dataclasses import dataclass
from enum import Enum


class Difficulty(Enum):
    """对外展示的四个难度等级。"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MASTER = "master"


@dataclass(frozen=True, slots=True)
class DifficultyConfig:
    """一个难度档位的搜索预算。

    参数只描述“怎么搜”，不直接保存棋子或棋局状态：

    * ``depth``：迭代加深允许达到的最大层数；
    * ``candidate_limit``：每层最多保留的启发式候选数；
    * ``time_limit``：单步硬性时间预算；
    * ``randomness``：简单档在近似候选中扰动概率；
    * ``vcf_depth``：连续冲四强制胜搜索的最大深度；
    * ``defensive_vcf``：是否主动检查对手的强制胜线路。
    """

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
        # 原困难档下沉为普通档，保持 1.4 秒内的稳定搜索。
        depth=5,
        candidate_limit=11,
        time_limit=1.4,
        randomness=0.0,
        vcf_depth=4,
        defensive_vcf=True,
    ),
    Difficulty.HARD: DifficultyConfig(
        # 新困难档增加时间、候选宽度和防守型强制搜索。
        depth=6,
        candidate_limit=12,
        time_limit=2.4,
        randomness=0.0,
        vcf_depth=6,
        defensive_vcf=True,
    ),
    Difficulty.MASTER: DifficultyConfig(
        # 大师档使用更少但更深的候选路线，以五秒预算换取更深层搜索。
        depth=8,
        candidate_limit=10,
        time_limit=5.0,
        randomness=0.0,
        vcf_depth=8,
        defensive_vcf=True,
    ),
}


def get_difficulty_config(difficulty: Difficulty) -> DifficultyConfig:
    """按难度返回不可变配置。"""

    return _CONFIGS[difficulty]
