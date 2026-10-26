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

_DEFAULT_BASE_URL = "https://api.deepseek.com"
_DEFAULT_MODEL = "deepseek-flash"
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


class DeepSeekError(RuntimeError):
    """DeepSeek 调用、返回格式或落点校验失败。"""


class DeepSeekResponseError(DeepSeekError):
    """模型返回无法解析或不是合法落点，可进行一次纠错重试。"""


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
        content = self._extract_content(self._request(payload))
        try:
            move = self._parse_move(content, snapshot)
        except DeepSeekResponseError as first_error:
            repair_payload = self._build_payload(
                snapshot,
                stone,
                repair=(content, str(first_error)),
            )
            repaired_content = self._extract_content(self._request(repair_payload))
            move = self._parse_move(repaired_content, snapshot)
        return self._result(move, started, "deepseek_api", 0)

    def _build_payload(
        self,
        snapshot: tuple[tuple[Stone, ...], ...],
        stone: Stone,
        *,
        repair: tuple[str, str] | None = None,
    ) -> dict[str, Any]:
        """构造 Chat Completions 请求体。"""

        prompt = self._build_prompt(snapshot, stone)
        legal_moves = self._legal_move_labels(snapshot)
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "你是五子棋落子引擎。只返回 JSON，不要解释。"
                    '格式必须是 {"move": "H8"}，其中列使用 A-O，行使用 1-15。'
                ),
            },
            {"role": "user", "content": prompt},
        ]
        if repair is not None:
            previous, reason = repair
            messages.extend(
                [
                    {"role": "assistant", "content": previous},
                    {
                        "role": "user",
                        "content": (
                            f"上一步非法：{reason}。必须从合法落点列表中选择一个空位，只返回 JSON。"
                        ),
                    },
                ]
            )
        return {
            "model": self._model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 512,
            "stream": False,
            # 五子棋只需要一个短 JSON；关闭默认思考模式可避免思考 token
            # 占满额度并导致 content 为空或 JSON 被截断。
            "thinking": {"type": "disabled"},
            "reasoning_effort": "none",
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "select_move",
                        "description": "Select one legal Gomoku move.",
                        "strict": True,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "move": {
                                    "type": "string",
                                    "enum": legal_moves,
                                }
                            },
                            "required": ["move"],
                            "additionalProperties": False,
                        },
                    },
                }
            ],
            "tool_choice": {
                "type": "function",
                "function": {"name": "select_move"},
            },
        }

    @staticmethod
    def _build_prompt(
        snapshot: tuple[tuple[Stone, ...], ...],
        stone: Stone,
    ) -> str:
        """把棋盘转换为紧凑、无歧义的文本局面。"""

        size = len(snapshot)
        column_header = "   " + " ".join(chr(ord("A") + col) for col in range(size))
        rows: list[str] = []
        for row_index, row in enumerate(snapshot):
            rows.append(
                f"{row_index + 1:>2} "
                + " ".join(
                    "X" if cell is stone else "O" if cell is not Stone.EMPTY else "."
                    for cell in row
                )
            )
        side = "黑方" if stone is Stone.BLACK else "白方"
        legal_moves = " ".join(DeepSeekStrategy._legal_move_labels(snapshot))
        return (
            f"{size}x{size} 五子棋，无禁手，当前轮到{side}。\n"
            "X 表示当前方，O 表示对手，. 表示空位。\n"
            "列坐标从左到右是 A-O，行坐标从上到下是 1-15。\n"
            f"{column_header}\n" + "\n".join(rows) + f"\n合法落点：{legal_moves}\n"
            "必须从合法落点中选择，优先立即获胜或封堵对手五连。"
            '只返回 JSON，例如 {"move": "H8"}。'
        )

    @staticmethod
    def _legal_move_labels(
        snapshot: tuple[tuple[Stone, ...], ...],
    ) -> list[str]:
        """按行优先顺序生成所有合法 A–O/1–15 坐标。"""

        return [
            f"{chr(ord('A') + col)}{row + 1}"
            for row in range(len(snapshot))
            for col in range(len(snapshot))
            if snapshot[row][col] is Stone.EMPTY
        ]

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
            detail = self._http_error_detail(exc)
            if exc.code in (401, 403):
                raise DeepSeekError("DeepSeek API Key 无效或没有权限") from exc
            if exc.code == 429:
                raise DeepSeekError("DeepSeek API 请求过于频繁，请稍后重试") from exc
            raise DeepSeekError(f"DeepSeek API 请求失败（HTTP {exc.code}）{detail}") from exc
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
            raise DeepSeekResponseError("DeepSeek 响应缺少 message")
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            first_call = tool_calls[0]
            function = first_call.get("function") if isinstance(first_call, dict) else None
            arguments = function.get("arguments") if isinstance(function, dict) else None
            if isinstance(arguments, str) and arguments.strip():
                return arguments
        finish_reason = first.get("finish_reason")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            if finish_reason == "length":
                raise DeepSeekResponseError("DeepSeek 输出达到 token 上限，未生成完整落点")
            raise DeepSeekResponseError("DeepSeek 未返回落子内容")
        return content

    @staticmethod
    def _http_error_detail(exc: urllib.error.HTTPError) -> str:
        """提取官方错误响应中的简短 message，便于定位参数问题。"""

        try:
            body = exc.read().decode("utf-8")
            data = json.loads(body)
            error = data.get("error") if isinstance(data, dict) else None
            message = error.get("message") if isinstance(error, dict) else None
            if isinstance(message, str) and message.strip():
                return f"：{message.strip()[:300]}"
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            pass
        return ""

    @staticmethod
    def _parse_move(
        content: str,
        snapshot: tuple[tuple[Stone, ...], ...],
    ) -> tuple[int, int]:
        """解析模型 JSON，并验证边界和空位。"""

        match = _JSON_OBJECT_PATTERN.search(content)
        if match is None:
            raise DeepSeekResponseError("DeepSeek 返回内容中没有 JSON 落点")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise DeepSeekResponseError("DeepSeek 返回的落点 JSON 无效") from exc
        if not isinstance(data, dict):
            raise DeepSeekResponseError("DeepSeek 落点不是 JSON 对象")

        move_value = data.get("move")
        if isinstance(move_value, str):
            move_match = re.fullmatch(r"([A-Oa-o])(1[0-5]|[1-9])", move_value.strip())
            if move_match is None:
                raise DeepSeekResponseError("DeepSeek 返回的 move 坐标格式无效")
            row = int(move_match.group(2)) - 1
            col = ord(move_match.group(1).upper()) - ord("A")
        else:
            try:
                row = int(data["row"])
                col = int(data["col"])
            except (KeyError, TypeError, ValueError) as exc:
                raise DeepSeekResponseError(
                    "DeepSeek 落点必须包含 move，或整数 row 和 col"
                ) from exc

        size = len(snapshot)
        if not (0 <= row < size and 0 <= col < size):
            raise DeepSeekResponseError("DeepSeek 返回了越界落点")
        if snapshot[row][col] is not Stone.EMPTY:
            raise DeepSeekResponseError("DeepSeek 返回了已占用的落点")
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
