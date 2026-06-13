"""Stage 4: Extract mesh from 3DGS via SuGaR."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from splatcraft.config import PipelineConfig

log = logging.getLogger(__name__)


def extract_mesh(cfg: PipelineConfig, model_dir: Path, data_dir: Path) -> Path:
    """Extract textured mesh from trained 3DGS model.

    Uses SuGaR (CVPR 2024) to regularize Gaussians onto surfaces,
    then performs Poisson reconstruction to get a clean mesh.

    Args:
        cfg: Pipeline configuration.
        model_dir: Path to trained 3DGS model.
        data_dir: Path to COLMAP-processed data (for camera poses).

    Returns:
        Path to extracted .obj mesh file.
    """
    output_dir = cfg.intermediate_dir("mesh")

    # Try SuGaR first
    sugar = _find_sugar()
    if sugar:
        return _extract_sugar(sugar, cfg, model_dir, data_dir, output_dir)

    # Try nerfstudio's mesh export as fallback
    ns_export = shutil.which("ns-export")
    if ns_export:
        return _extract_nerfstudio_mesh(ns_export, cfg, model_dir, output_dir)

    raise RuntimeError(
        "No mesh extraction tool found.\n"
        "Install SuGaR: git clone https://github.com/Anttwo/SuGaR && cd SuGaR && pip install -e .\n"
        "Or install nerfstudio for basic mesh export."
    )


def _find_sugar() -> str | None:
    """Find SuGaR installation."""
    # Check if sugar is importable
    try:
        import importlib
        importlib.import_module("sugar")
        return "sugar"
    except ImportError:
        pass
    # Check for the script directly
    sugar_script = shutil.which("sugar_train_extract")
    return sugar_script


def _extract_sugar(
    sugar: str, cfg: PipelineConfig, model_dir: Path, data_dir: Path, output_dir: Path,
) -> Path:
    """Extract mesh via SuGaR."""
    # SuGaR expects nerfstudio config or a specific directory structure
    config_files = list(model_dir.rglob("config.yml"))

    poly_flag = "--high_poly" if cfg.extract_high_poly else ""
    cmd = [
        "python", "-m", "sugar_trainers.sugar_gui",
        "-s", str(data_dir),
        "-c", str(config_files[0]) if config_files else str(model_dir),
        "-o", str(output_dir),
        "--poly_flag", "1" if cfg.extract_high_poly else "0",
    ]
    # Remove empty strings
    cmd = [c for c in cmd if c]

    log.info(f"Extracting mesh via SuGaR ({'high' if cfg.extract_high_poly else 'low'} poly)")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        raise RuntimeError(f"SuGaR extraction failed:\n{result.stderr}")

    # Find output .obj
    obj_files = list(output_dir.rglob("*.obj"))
    if obj_files:
        best = max(obj_files, key=lambda p: p.stat().st_size)
        final = output_dir / "splatcraft_mesh.obj"
        if best != final:
            shutil.copy2(best, final)
        log.info(f"Extracted mesh: {final}")
        return final

    raise FileNotFoundError(f"SuGaR ran but no .obj found in {output_dir}")


def _extract_nerfstudio_mesh(
    ns_export: str, cfg: PipelineConfig, model_dir: Path, output_dir: Path,
) -> Path:
    """Extract mesh via nerfstudio's tsdf or poisson export."""
    config_files = list(model_dir.rglob("config.yml"))
    if not config_files:
        raise FileNotFoundError(f"No config.yml in {model_dir}")

    cmd = [
        ns_export, "tsdf",
        "--load-config", str(config_files[0]),
        "--output-dir", str(output_dir),
        "--num-pixels-per-side", "2048",
    ]
    log.info("Extracting mesh via nerfstudio TSDF")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0:
        # Try poisson as fallback
        cmd[1] = "poisson"
        log.info("TSDF failed, trying poisson...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f"nerfstudio mesh export failed:\n{result.stderr}")

    # Find output mesh
    for ext in ["*.obj", "*.ply", "*.glb"]:
        meshes = list(output_dir.glob(ext))
        if meshes:
            final = output_dir / "splatcraft_mesh.obj"
            shutil.copy2(meshes[0], final)
            log.info(f"Extracted mesh: {final}")
            return final

    raise FileNotFoundError(f"No mesh found in {output_dir}")
