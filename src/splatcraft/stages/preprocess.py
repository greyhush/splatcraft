"""Stage 1: Preprocess input photos (COLMAP / SfM)."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from splatcraft.config import PipelineConfig

log = logging.getLogger(__name__)


def _find_colmap() -> str | None:
    """Find COLMAP binary."""
    return shutil.which("colmap")


def _validate_images(image_dir: Path) -> list[Path]:
    """Return list of valid image files in directory."""
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
    images = sorted(
        p for p in image_dir.iterdir()
        if p.suffix.lower() in exts and p.is_file()
    )
    if len(images) < 3:
        raise ValueError(
            f"Need ≥3 images, found {len(images)} in {image_dir}. "
            f"Provide multiple views of the object from different angles."
        )
    return images


def preprocess(cfg: PipelineConfig) -> Path:
    """Run COLMAP preprocessing on input images.

    Uses nerfstudio's ns-process-data which handles COLMAP automatically.
    Returns path to processed output directory.
    """
    output_dir = cfg.intermediate_dir("colmap")
    images = _validate_images(cfg.input_dir)

    log.info(f"Preprocessing {len(images)} images from {cfg.input_dir}")

    # Check if nerfstudio is available
    ns_process = shutil.which("ns-process-data")
    if ns_process:
        return _preprocess_nerfstudio(cfg, output_dir)

    # Fallback: raw COLMAP
    colmap = _find_colmap()
    if colmap:
        return _preprocess_colmap_raw(cfg, output_dir, colmap)

    raise RuntimeError(
        "Neither ns-process-data nor colmap found in PATH.\n"
        "Install: pip install nerfstudio  OR  conda install colmap"
    )


def _preprocess_nerfstudio(cfg: PipelineConfig, output_dir: Path) -> Path:
    """Preprocess via nerfstudio's ns-process-data."""
    cmd = [
        "ns-process-data", "images",
        "--data", str(cfg.input_dir),
        "--output-dir", str(output_dir),
        "--num-downscales", str(cfg.resolution - 1) if cfg.resolution > 1 else "0",
    ]
    log.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"ns-process-data failed:\n{result.stderr}")
    log.info(f"COLMAP output: {output_dir}")
    return output_dir


def _preprocess_colmap_raw(cfg: PipelineConfig, output_dir: Path, colmap: str) -> Path:
    """Preprocess via raw COLMAP commands."""
    db_path = output_dir / "database.db"
    sparse_dir = output_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)

    steps = [
        # Feature extraction
        [colmap, "feature_extractor",
         "--database_path", str(db_path),
         "--image_path", str(cfg.input_dir),
         "--ImageReader.single_camera", "1"],
        # Feature matching
        [colmap, "exhaustive_matcher",
         "--database_path", str(db_path)],
        # Sparse reconstruction
        [colmap, "mapper",
         "--database_path", str(db_path),
         "--image_path", str(cfg.input_dir),
         "--output_path", str(sparse_dir)],
    ]
    for step in steps:
        log.info(f"Running: {step[0]} {step[1]}")
        result = subprocess.run(step, capture_output=True, text=True, timeout=3600)
        if result.returncode != 0:
            raise RuntimeError(f"COLMAP step '{step[1]}' failed:\n{result.stderr}")

    log.info(f"COLMAP output: {output_dir}")
    return output_dir
