"""可选的 ONNX 策略模型接入。

模型协议与当前使用的 15×15 Gomoku 模型保持兼容：

* 输入：``float32[1, 2, H, W]``；
* 通道 0：当前行动方的棋子；
* 通道 1：对手棋子；
* 输出：长度为 ``H*W`` 的策略分数，以及可选的单值局面价值。

ONNX Runtime 属于可选依赖，模块顶层不会导入 numpy/onnxruntime，因此没有
模型时纯搜索版本仍能正常启动。
"""

from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dropfive.model.stone import Stone

_GPU_PROVIDER_PRIORITY = (
    "TensorrtExecutionProvider",
    "CUDAExecutionProvider",
    "ROCMExecutionProvider",
    "DmlExecutionProvider",
    "OpenVINOExecutionProvider",
    "CoreMLExecutionProvider",
)

_PROVIDER_LABELS = {
    "TensorrtExecutionProvider": "ONNX TensorRT",
    "CUDAExecutionProvider": "ONNX CUDA",
    "ROCMExecutionProvider": "ONNX ROCm",
    "DmlExecutionProvider": "ONNX DirectML",
    "OpenVINOExecutionProvider": "ONNX OpenVINO",
    "CoreMLExecutionProvider": "ONNX CoreML",
    "CPUExecutionProvider": "ONNX CPU",
}


class ModelLoadError(RuntimeError):
    """Raised when an optional ONNX model cannot be used."""


@dataclass(frozen=True, slots=True)
class PolicyOutput:
    """模型一次前向的结果和运行信息。"""

    logits: tuple[float, ...]
    value: float
    elapsed_ms: float
    backend: str


def discover_model_path() -> Path | None:
    """按优先级寻找本地模型。

    优先使用环境变量，便于高级用户指定任意模型；否则依次查看当前工作目录
    和源码/安装目录下的 ``models``。仓库不携带大模型文件。
    """
    configured = os.environ.get("DROPFIVE_ONNX_MODEL", "").strip()
    if configured:
        path = Path(configured).expanduser()
        return path if path.is_file() else None

    repository_root = Path(__file__).resolve().parents[3]
    candidates = (
        Path.cwd() / "models",
        repository_root / "models",
    )
    for directory in candidates:
        if not directory.is_dir():
            continue
        models = sorted(directory.glob("*.onnx"))
        if models:
            preferred = [path for path in models if "bs15" in path.name]
            return preferred[0] if preferred else models[0]
    return None


def choose_providers(
    available: tuple[str, ...] | list[str],
    *,
    prefer_gpu: bool = True,
) -> tuple[str, ...]:
    """从 ONNX Runtime 已编译的 Provider 中选择执行顺序。

    GPU Provider 按 TensorRT、CUDA、ROCm、DirectML、OpenVINO、CoreML
    的收益/兼容性顺序尝试，最后始终加入 CPU，保证至少有一条可执行路径。
    """
    available_set = set(available)
    providers: list[str] = []
    if prefer_gpu and os.environ.get("DROPFIVE_ONNX_DISABLE_GPU") != "1":
        providers.extend(
            provider for provider in _GPU_PROVIDER_PRIORITY if provider in available_set
        )
    if "CPUExecutionProvider" in available_set:
        providers.append("CPUExecutionProvider")
    return tuple(dict.fromkeys(providers))


def encode_board(
    snapshot: tuple[tuple[Stone, ...], ...],
    current_player: Stone,
) -> tuple[float, ...]:
    """将棋盘编码为当前玩家视角的双通道张量数据。"""
    size = len(snapshot)
    if size < 1 or any(len(row) != size for row in snapshot):
        raise ValueError("Board snapshot must be a non-empty square")
    if current_player is Stone.EMPTY:
        raise ValueError("A player stone is required")

    encoded = [0.0] * (2 * size * size)
    plane_size = size * size
    for row in range(size):
        for col in range(size):
            stone = snapshot[row][col]
            index = row * size + col
            if stone is current_player:
                encoded[index] = 1.0
            elif stone is not Stone.EMPTY:
                encoded[plane_size + index] = 1.0
    return tuple(encoded)


def policy_priors(
    logits: tuple[float, ...],
    snapshot: tuple[tuple[Stone, ...], ...],
) -> dict[tuple[int, int], float]:
    """只对合法空位做数值稳定的 softmax，返回坐标到概率的映射。"""
    size = len(snapshot)
    if len(logits) != size * size:
        raise ValueError(f"Expected {size * size} policy values, received {len(logits)}")

    legal_indices = [
        row * size + col
        for row in range(size)
        for col in range(size)
        if snapshot[row][col] is Stone.EMPTY
    ]
    if not legal_indices:
        return {}

    max_logit = max(logits[index] for index in legal_indices)
    # 先减最大值再取 exp，防止极端 logits 造成上溢。
    weights = {index: math.exp(logits[index] - max_logit) for index in legal_indices}
    total = sum(weights.values())
    if total <= 0:
        uniform = 1.0 / len(legal_indices)
        return {(index // size, index % size): uniform for index in legal_indices}
    return {(index // size, index % size): weights[index] / total for index in legal_indices}


class OnnxPolicyModel:
    """持有 ONNX Runtime Session，并把推理结果转换为搜索先验。"""

    def __init__(
        self,
        model_path: Path,
        *,
        prefer_gpu: bool = True,
    ) -> None:
        """加载模型并自动选择 GPU/CPU Provider。"""
        try:
            import numpy as np
            import onnxruntime as ort
        except ImportError as exc:
            raise ModelLoadError("ONNX support requires numpy and onnxruntime") from exc

        self.path = model_path
        self._np = np
        # 只看当前安装的 onnxruntime 包实际编译进二进制的 Provider。
        available = tuple(ort.get_available_providers())
        providers = choose_providers(available, prefer_gpu=prefer_gpu)
        if not providers:
            raise ModelLoadError("No usable ONNX Runtime provider is available")

        try:
            self._session = ort.InferenceSession(str(model_path), providers=list(providers))
        except Exception as exc:
            if providers == ("CPUExecutionProvider",):
                raise ModelLoadError(f"Failed to load ONNX model: {exc}") from exc
            try:
                # GPU 驱动、显存或 Provider 初始化失败时仍可安全使用 CPU。
                self._session = ort.InferenceSession(
                    str(model_path),
                    providers=["CPUExecutionProvider"],
                )
            except Exception as cpu_exc:
                raise ModelLoadError(f"Failed to load ONNX model: {cpu_exc}") from cpu_exc

        self._input = self._session.get_inputs()[0]
        self._outputs = tuple(self._session.get_outputs())
        self._input_name = self._input.name
        self._active_providers = tuple(self._session.get_providers())
        self.backend_label = _provider_label(self._active_providers)
        self._validate_input()

    def infer(
        self,
        snapshot: tuple[tuple[Stone, ...], ...],
        current_player: Stone,
    ) -> PolicyOutput:
        """执行一次同步推理；调用方通过后台线程避免阻塞 tkinter。"""
        size = len(snapshot)
        encoded = encode_board(snapshot, current_player)
        input_tensor = self._np.asarray(encoded, dtype=self._np.float32).reshape(1, 2, size, size)

        started = time.perf_counter()
        outputs = self._session.run(None, {self._input_name: input_tensor})
        elapsed_ms = (time.perf_counter() - started) * 1000
        logits, value = self._extract_outputs(outputs, size)
        return PolicyOutput(
            logits=logits,
            value=value,
            elapsed_ms=elapsed_ms,
            backend=self.backend_label,
        )

    def _extract_outputs(
        self,
        outputs: list[Any],
        board_size: int,
    ) -> tuple[tuple[float, ...], float]:
        """根据名称和形状识别策略输出与价值输出。"""
        flat_outputs: list[tuple[str, Any]] = []
        for metadata, value in zip(self._outputs, outputs, strict=True):
            flat_outputs.append((metadata.name.lower(), self._np.asarray(value).reshape(-1)))

        policy_values = next(
            (
                values
                for name, values in flat_outputs
                if "policy" in name and values.size == board_size * board_size
            ),
            None,
        )
        if policy_values is None:
            # 兼容未按约定命名的自定义模型，退化为按输出元素数量识别。
            policy_values = next(
                (values for _, values in flat_outputs if values.size == board_size * board_size),
                None,
            )
        if policy_values is None:
            raise ModelLoadError("ONNX model did not return a board-sized policy output")

        value_output = next(
            (values for name, values in flat_outputs if "value" in name and values.size == 1),
            None,
        )
        if value_output is None:
            value_output = next(
                (values for _, values in flat_outputs if values.size == 1),
                None,
            )
        value = float(value_output[0]) if value_output is not None else 0.0
        return tuple(float(value) for value in policy_values), value

    def _validate_input(self) -> None:
        """尽早拒绝通道数不兼容的模型，而不是等到第一次落子才崩溃。"""
        shape = tuple(self._input.shape)
        if len(shape) != 4 or shape[1] != 2:
            raise ModelLoadError(
                "ONNX model input must use shape [batch, 2, board_height, board_width]"
            )


def load_optional_model(
    model_path: Path | None = None,
) -> tuple[OnnxPolicyModel | None, str | None]:
    """尝试加载模型；失败时返回错误字符串供诊断，但不阻止程序启动。"""
    path = model_path or discover_model_path()
    if path is None:
        return None, None
    try:
        return OnnxPolicyModel(path), None
    except (ModelLoadError, OSError, ValueError) as exc:
        return None, str(exc)


def _provider_label(providers: tuple[str, ...]) -> str:
    """把 ONNX Runtime Provider 名称转换成界面可读标签。"""
    for provider in providers:
        if provider in _PROVIDER_LABELS:
            if provider == "CPUExecutionProvider":
                break
            return _PROVIDER_LABELS[provider]
    return _PROVIDER_LABELS["CPUExecutionProvider"]
