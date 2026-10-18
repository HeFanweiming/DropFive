"""Optional ONNX policy model integration with CPU/GPU provider fallback."""

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
    logits: tuple[float, ...]
    value: float
    elapsed_ms: float
    backend: str


def discover_model_path() -> Path | None:
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
    weights = {index: math.exp(logits[index] - max_logit) for index in legal_indices}
    total = sum(weights.values())
    if total <= 0:
        uniform = 1.0 / len(legal_indices)
        return {(index // size, index % size): uniform for index in legal_indices}
    return {(index // size, index % size): weights[index] / total for index in legal_indices}


class OnnxPolicyModel:
    """Load one model session and expose move priors for the search engine."""

    def __init__(
        self,
        model_path: Path,
        *,
        prefer_gpu: bool = True,
    ) -> None:
        try:
            import numpy as np
            import onnxruntime as ort
        except ImportError as exc:
            raise ModelLoadError("ONNX support requires numpy and onnxruntime") from exc

        self.path = model_path
        self._np = np
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
        shape = tuple(self._input.shape)
        if len(shape) != 4 or shape[1] != 2:
            raise ModelLoadError(
                "ONNX model input must use shape [batch, 2, board_height, board_width]"
            )


def load_optional_model(
    model_path: Path | None = None,
) -> tuple[OnnxPolicyModel | None, str | None]:
    path = model_path or discover_model_path()
    if path is None:
        return None, None
    try:
        return OnnxPolicyModel(path), None
    except (ModelLoadError, OSError, ValueError) as exc:
        return None, str(exc)


def _provider_label(providers: tuple[str, ...]) -> str:
    for provider in providers:
        if provider in _PROVIDER_LABELS:
            if provider == "CPUExecutionProvider":
                break
            return _PROVIDER_LABELS[provider]
    return _PROVIDER_LABELS["CPUExecutionProvider"]
