import math
from pathlib import Path

import pytest

from dropfive.ai.onnx_policy import (
    OnnxPolicyModel,
    choose_providers,
    discover_model_path,
    encode_board,
    policy_priors,
)
from dropfive.model.board import Board
from dropfive.model.stone import Stone


def test_board_encoding_uses_current_player_first() -> None:
    board = Board(3)
    board.place(0, 0, Stone.BLACK)
    board.place(1, 1, Stone.WHITE)

    encoded = encode_board(board.snapshot(), Stone.BLACK)

    assert len(encoded) == 18
    assert encoded[0] == 1.0
    assert encoded[9 + 4] == 1.0
    assert sum(encoded) == 2.0


def test_policy_priors_mask_occupied_cells_and_normalize() -> None:
    board = Board(3)
    board.place(0, 0, Stone.BLACK)
    logits = tuple(float(index) for index in range(9))

    priors = policy_priors(logits, board.snapshot())

    assert (0, 0) not in priors
    assert math.isclose(sum(priors.values()), 1.0)
    assert max(priors, key=priors.get) == (2, 2)


def test_gpu_provider_is_preferred_but_cpu_remains_fallback() -> None:
    providers = choose_providers(
        ["CPUExecutionProvider", "CUDAExecutionProvider"],
    )

    assert providers == ("CUDAExecutionProvider", "CPUExecutionProvider")


def test_cpu_is_used_when_no_gpu_provider_exists() -> None:
    assert choose_providers(["CPUExecutionProvider"]) == ("CPUExecutionProvider",)


def test_configured_model_path_is_discovered(monkeypatch, tmp_path: Path) -> None:
    model_path = tmp_path / "test.onnx"
    model_path.write_bytes(b"placeholder")
    monkeypatch.setenv("DROPFIVE_ONNX_MODEL", str(model_path))

    assert discover_model_path() == model_path


def test_real_onnx_model_inference_when_available() -> None:
    model_path = discover_model_path()
    if model_path is None:
        pytest.skip("No local ONNX model is installed")
    pytest.importorskip("onnxruntime")

    model = OnnxPolicyModel(model_path)
    output = model.infer(Board().snapshot(), Stone.BLACK)

    assert len(output.logits) == 225
    assert math.isfinite(output.value)
