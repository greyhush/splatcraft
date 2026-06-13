"""Stage 3: Export .ply splat file for VRChatGaussianSplatting."""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from splatcraft.config import PipelineConfig

log = logging.getLogger(__name__)


def export_splat(cfg: PipelineConfig, model_dir: Path) -> Path:
    """Export trained 3DGS model as .ply for VRChat.

    VRChat uses MichaelMoroz/VRChatGaussianSplatting which reads standard .ply files.

    Args:
        cfg: Pipeline configuration.
        model_dir: Path to trained model directory.

    Returns:
        Path to exported .ply file.
    """
    output_dir = cfg.output_dir / "splat"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try nerfstudio export first
    ns_export = shutil.which("ns-export")
    if ns_export:
        return _export_nerfstudio(ns_export, model_dir, output_dir)

    # Look for existing .ply in model directory
    ply_files = list(model_dir.rglob("*.ply"))
    if ply_files:
        # Copy the largest .ply (usually the final checkpoint)
        best = max(ply_files, key=lambda p: p.stat().st_size)
        dest = output_dir / "splatcraft_splat.ply"
        shutil.copy2(best, dest)
        log.info(f"Exported .ply (direct copy): {dest}")
        return dest

    raise RuntimeError(
        "No .ply file found and ns-export not available.\n"
        "Install nerfstudio or manually export .ply from your 3DGS trainer."
    )


def _export_nerfstudio(ns_export: str, model_dir: Path, output_dir: Path) -> Path:
    """Export via nerfstudio's ns-export."""
    # Find the config.yml in model_dir
    config_files = list(model_dir.rglob("config.yml"))
    if not config_files:
        raise FileNotFoundError(f"No config.yml found in {model_dir}")

    ply_path = output_dir / "splatcraft_splat.ply"
    cmd = [
        ns_export, "gaussian-splat",
        "--load-config", str(config_files[0]),
        "--output-dir", str(output_dir),
    ]
    log.info(f"Exporting .ply via ns-export")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"ns-export failed:\n{result.stderr}")

    # Find the exported .ply
    exported = list(output_dir.glob("*.ply"))
    if not exported:
        raise FileNotFoundError(f"ns-export ran but no .ply found in {output_dir}")

    # Rename to our standard name
    final = output_dir / "splatcraft_splat.ply"
    if exported[0] != final:
        exported[0].rename(final)

    log.info(f"Exported .ply: {final}")
    return final
