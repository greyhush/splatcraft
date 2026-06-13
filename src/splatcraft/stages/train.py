"""Stage 2: Train 3D Gaussian Splatting model."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from splatcraft.config import PipelineConfig, TrainBackend

log = logging.getLogger(__name__)


def train(cfg: PipelineConfig, data_dir: Path) -> Path:
    """Train 3DGS model from preprocessed data.

    Args:
        cfg: Pipeline configuration.
        data_dir: Path to COLMAP-processed data directory.

    Returns:
        Path to trained model output directory.
    """
    output_dir = cfg.intermediate_dir("trained")

    match cfg.backend:
        case TrainBackend.NERFSTUDIO:
            return _train_nerfstudio(cfg, data_dir, output_dir)
        case TrainBackend.OPENSPLAT:
            return _train_opensplat(cfg, data_dir, output_dir)
        case TrainBackend.ORIGINAL:
            return _train_original(cfg, data_dir, output_dir)
        case _:
            raise ValueError(f"Unknown backend: {cfg.backend}")


def _train_nerfstudio(cfg: PipelineConfig, data_dir: Path, output_dir: Path) -> Path:
    """Train via nerfstudio's splatfacto."""
    ns_train = shutil.which("ns-train")
    if not ns_train:
        raise RuntimeError("ns-train not found. Install: pip install nerfstudio")

    cmd = [
        ns_train, "splatfacto",
        "--data", str(data_dir),
        "--output-dir", str(output_dir),
        "--max-num-iterations", str(cfg.max_iterations),
        "--pipeline.model.sh-degree", "2",
    ]
    log.info(f"Training 3DGS (nerfstudio/splatfacto, {cfg.max_iterations} iters)")
    log.info(f"Command: {' '.join(cmd)}")

    # Training can take hours — stream output
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    last_line = ""
    for line in process.stdout:
        line = line.rstrip()
        if line:
            last_line = line
            if "Step" in line or "loss" in line.lower():
                log.info(line)
    process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"Training failed (exit {process.returncode}). Last output: {last_line}")

    # Find the trained model output
    # nerfstudio outputs to output_dir/<experiment_name>/<timestamp>/
    model_dir = _find_nerfstudio_output(output_dir)
    log.info(f"Model trained: {model_dir}")
    return model_dir


def _train_opensplat(cfg: PipelineConfig, data_dir: Path, output_dir: Path) -> Path:
    """Train via OpenSplat."""
    opensplat = shutil.which("opensplat")
    if not opensplat:
        raise RuntimeError("opensplat not found. Build from: github.com/pierotofy/OpenSplat")

    model_path = output_dir / "model.ply"
    cmd = [
        opensplat, str(data_dir),
        "-o", str(output_dir),
        "--max-iters", str(cfg.max_iterations),
    ]
    log.info(f"Training 3DGS (OpenSplat, {cfg.max_iterations} iters)")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if result.returncode != 0:
        raise RuntimeError(f"OpenSplat failed:\n{result.stderr}")
    return output_dir


def _train_original(cfg: PipelineConfig, data_dir: Path, output_dir: Path) -> Path:
    """Train via original gaussian-splatting implementation."""
    # The original implementation expects a specific directory structure
    cmd = [
        "python", "-m", "train",
        "-s", str(data_dir),
        "-m", str(output_dir),
        "--iterations", str(cfg.max_iterations),
    ]
    log.info(f"Training 3DGS (original, {cfg.max_iterations} iters)")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    if result.returncode != 0:
        raise RuntimeError(f"Original 3DGS training failed:\n{result.stderr}")
    return output_dir


def _find_nerfstudio_output(output_dir: Path) -> Path:
    """Find nerfstudio's actual model output directory."""
    # nerfstudio creates output_dir/method_name/timestamp/
    for method_dir in output_dir.iterdir():
        if method_dir.is_dir():
            timestamps = sorted(method_dir.iterdir(), key=lambda p: p.stat().st_mtime)
            if timestamps:
                return timestamps[-1]
    # If no subdirectory structure, assume output_dir itself
    return output_dir
