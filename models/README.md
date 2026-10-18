# Optional ONNX Model

DropFive automatically loads the first `.onnx` model found in this directory. The model file is intentionally excluded from Git because it is a large binary asset.

Supported model contract:

- Input: `float32[1, 2, board_size, board_size]`
- Channel 0: stones belonging to the side to move
- Channel 1: opponent stones
- Output: one board-sized policy tensor and one scalar position value

Recommended source:

- Repository: `https://github.com/whyb/Gomoku-AI`
- File: `webdemo/model_bs15_win5.onnx`
- License: BSD-3-Clause

Model discovery order:

1. `DROPFIVE_ONNX_MODEL` environment variable
2. `models/*.onnx` under the current working directory
3. `models/*.onnx` under the DropFive repository or installation root

Install CPU inference dependencies:

```powershell
uv pip install --python .\.venv\Scripts\python.exe -e ".[onnx]"
```

GPU providers are selected automatically when available. Install only one ONNX Runtime package:

- NVIDIA CUDA: `onnxruntime-gpu`
- Windows DirectML: `onnxruntime-directml`
- CPU fallback: `onnxruntime`

Set `DROPFIVE_ONNX_DISABLE_GPU=1` to force CPU execution.
