"""搜索型五子棋 AI 的公开入口。"""

from dropfive.ai.deepseek import DeepSeekError, DeepSeekStrategy
from dropfive.ai.difficulty import Difficulty, DifficultyConfig, get_difficulty_config
from dropfive.ai.search import AlphaBetaSearch, SearchResult
from dropfive.ai.strategy import GomokuAI

# UI 和控制器只依赖这组稳定接口，不需要知道搜索内部模块布局。
__all__ = [
    "AlphaBetaSearch",
    "Difficulty",
    "DifficultyConfig",
    "DeepSeekError",
    "DeepSeekStrategy",
    "GomokuAI",
    "SearchResult",
    "get_difficulty_config",
]
