"""通过 DeepSeek Chat Completions API 获取人机落子。"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from dropfive.ai.evaluator import WIN_SCORE, Evaluator
from dropfive.ai.search import SearchResult
from dropfive.model.board import Board
from dropfive.model.stone import Stone

_DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
_DEFAULT_MODEL = "deepseek-flash"
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


class DeepSeekError(RuntimeError):
    """DeepSeek 调用、返回格式或落点校验失败。"""


class DeepSeekStrategy:
    """使用 DeepSeek API 产生落点，并保留本地战术兜底。

    API 之前先检查空棋盘、一步获胜和对手一步获胜，避免把最简单的必胜/
    必堵局面交给网络判断。网络失败由 UI 层捕获并切换本地 AI。
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 20.0,
        transport: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        """保存认证与请求配置。

        ``transport`` 仅用于测试注入，生产环境使用标准库 urllib 发起 HTTPS。
        """

        self._api_key = api_key.strip()
        self._model = model or os.environ.get("DEEPSEEK_MODEL", _DEFAULT_MODEL)
        configured_base = base_url or os.environ.get(
            "DEEPSEEK_API_BASE",
            _DEFAULT_BASE_URL,
        )
        self._endpoint = configured_base.rstrip("/") + "/chat/completions"
        self._timeout = timeout
        self._transport = transport

    def choose_move(
        self,
        snapshot: tuple[tuple[Stone, ...], ...],
        stone: Stone,
    ) -> SearchResult:
        """请求 DeepSeek 返回一个坐标，并验证该坐标可以合法落子。"""

        started = time.perf_counter()
        board = Board.from_snapshot(snapshot)

        if board.stone_count == 0:
            center = board.size // 2
            return self._result(
                (center, center),
                started,
                "center_opening",
                WIN_SCORE // 2,
            )

        evaluator = Evaluator()
        winning_moves = evaluator.find_winning_moves(board, stone)
        if winning_moves:
            return self._result(winning_moves[0], started, "immediate_win", WIN_SCORE)

        opponent_wins = evaluator.find_winning_moves(board, stone.opponent)
        if opponent_wins:
            return self._result(opponent_wins[0], started, "block_win", 0)

        if not self._api_key:
            raise DeepSeekError("未配置 DeepSeek API Key，请在设置中填写或设置 DEEPSEEK_API_KEY")

        payload = self._build_payload(snapshot, stone)
        response = self._request(payload)
        content = self._extract_content(response)
        move = self._parse_move(content, snapshot)
        return self._result(move, started, "deepseek_api", 0)

    def _build_payload(
        self,
        snapshot: tuple[tuple[Stone, ...], ...],
        stone: Stone,
    ) -> dict[str, Any]:
        """构造 Chat Completions 请求体。"""

        prompt = self._build_prompt(snapshot, stone)
        return {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是五子棋落子引擎。只返回 JSON，不要解释。"
                        '格式必须是 {"row": 0到14的整数, "col": 0到14的整数}。'
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 200,
            "stream": False,
            "response_format": {"type": "json_object"},
        }

    @staticmethod
    def _build_prompt(
        snapshot: tuple[tuple[Stone, ...], ...],
        stone: Stone,
    ) -> str:
        """把棋盘转换为紧凑、无歧义的文本局面。"""

        size = len(snapshot)
        rows: list[str] = []
        for row in snapshot:
            rows.append(
                "".join(
                    "X" if cell is stone else "O" if cell is not Stone.EMPTY else "."
                    for cell in row
                )
            )
        side = "黑方" if stone is Stone.BLACK else "白方"
        return (
            f"{size}x{size} 五子棋，无禁手，当前轮到{side}。\n"
            "X 表示当前方，O 表示对手，. 表示空位。\n"
            "坐标使用零基 row/col，从 0 开始。\n"
            + "\n".join(f"{index}: {line}" for index, line in enumerate(rows))
            + "\n请选择一个空位，优先立即获胜或封堵对手五连。只返回 JSON。"
        )

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """调用网络或测试 transport，并统一处理 JSON 响应。"""

        if self._transport is not None:
            response = self._transport(payload)
            if not isinstance(response, dict):
                raise DeepSeekError("DeepSeek 返回格式不是 JSON 对象")
            return response

        request = urllib.request.Request(
            self._endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise DeepSeekError("DeepSeek API Key 无效或没有权限") from exc
            if exc.code == 429:
                raise DeepSeekError("DeepSeek API 请求过于频繁，请稍后重试") from exc
            raise DeepSeekError(f"DeepSeek API 请求失败（HTTP {exc.code}）") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise DeepSeekError("无法连接 DeepSeek API，请检查网络") from exc

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError as exc:
            raise DeepSeekError("DeepSeek API 返回了无效 JSON") from exc
        if not isinstance(parsed, dict):
            raise DeepSeekError("DeepSeek API 返回格式不是 JSON 对象")
        return parsed

    @staticmethod
    def _extract_content(response: dict[str, Any]) -> str:
        """从 OpenAI 兼容响应中提取文本消息。"""

        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise DeepSeekError("DeepSeek 响应缺少 choices")
        first = choices[0]
        if not isinstance(first, dict):
            raise DeepSeekError("DeepSeek choices 格式错误")
        message = first.get("message")
        if not isinstance(message, dict):
            raise DeepSeekError("DeepSeek 响应缺少 message")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise DeepSeekError("DeepSeek 未返回落子内容")
        return content

    @staticmethod
    def _parse_move(
        content: str,
        snapshot: tuple[tuple[Stone, ...], ...],
    ) -> tuple[int, int]:
        """解析模型 JSON，并验证边界和空位。"""

        match = _JSON_OBJECT_PATTERN.search(content)
        if match is None:
            raise DeepSeekError("DeepSeek 返回内容中没有 JSON 落点")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise DeepSeekError("DeepSeek 返回的落点 JSON 无效") from exc
        if not isinstance(data, dict):
            raise DeepSeekError("DeepSeek 落点不是 JSON 对象")

        try:
            row = int(data["row"])
            col = int(data["col"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DeepSeekError("DeepSeek 落点必须包含整数 row 和 col") from exc

        size = len(snapshot)
        if not (0 <= row < size and 0 <= col < size):
            raise DeepSeekError("DeepSeek 返回了越界落点")
        if snapshot[row][col] is not Stone.EMPTY:
            raise DeepSeekError("DeepSeek 返回了已占用的落点")
        return row, col

    @staticmethod
    def _result(
        move: tuple[int, int],
        started: float,
        reason: str,
        score: int,
    ) -> SearchResult:
        """统一构造与本地 AI 相同类型的搜索结果。"""

        return SearchResult(
            move=move,
            score=score,
            depth=0,
            nodes=0,
            elapsed=time.perf_counter() - started,
            reason=reason,
        )
