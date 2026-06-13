"""GPU detection and memory utilities."""
from __future__ import annotations

import subprocess
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GPUInfo:
    name: str
    vram_total_mb: int
    vram_free_mb: int
    cuda_version: str


def detect_gpu() -> GPUInfo | None:
    """Detect NVIDIA GPU via nvidia-smi. Returns None if no GPU found."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return None
    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total,memory.free,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        parts = [p.strip() for p in result.stdout.strip().split(",")]
        if len(parts) < 4:
            return None
        return GPUInfo(
            name=parts[0],
            vram_total_mb=int(parts[1]),
            vram_free_mb=int(parts[2]),
            cuda_version=parts[3],
        )
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return None


def check_vram(required_mb: int = 8000) -> tuple[bool, str]:
    """Check if enough VRAM is available. Returns (ok, message)."""
    gpu = detect_gpu()
    if gpu is None:
        return False, "No NVIDIA GPU detected. SplatCraft requires CUDA-capable GPU."
    if gpu.vram_free_mb < required_mb:
        return False, (
            f"{gpu.name}: {gpu.vram_free_mb}MB free, need {required_mb}MB. "
            f"Close other GPU apps and try again."
        )
    return True, f"{gpu.name}: {gpu.vram_free_mb}MB free ✓"


def require_gpu(min_vram_mb: int = 8000) -> GPUInfo:
    """Raise RuntimeError if no suitable GPU found."""
    gpu = detect_gpu()
    if gpu is None:
        raise RuntimeError("No NVIDIA GPU detected. SplatCraft requires CUDA-capable GPU.")
    if gpu.vram_total_mb < min_vram_mb:
        raise RuntimeError(
            f"{gpu.name} has {gpu.vram_total_mb}MB VRAM, need ≥{min_vram_mb}MB."
        )
    return gpu
