"""SplatCraft pipeline orchestrator."""
from __future__ import annotations

import logging
import time
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from splatcraft.config import PipelineConfig, OutputMode
from splatcraft.stages.preprocess import preprocess
from splatcraft.stages.train import train
from splatcraft.stages.export_splat import export_splat
from splatcraft.stages.extract import extract_mesh
from splatcraft.stages.optimize import optimize
from splatcraft.stages.physics import generate_physics
from splatcraft.stages.package import package_vrchat

log = logging.getLogger(__name__)
console = Console()


class PipelineError(Exception):
    """Pipeline stage failure with context."""
    def __init__(self, stage: str, message: str, cause: Exception | None = None):
        self.stage = stage
        self.cause = cause
        super().__init__(f"[{stage}] {message}")


def run_pipeline(cfg: PipelineConfig) -> Path:
    """Run the full SplatCraft pipeline.

    Pipeline stages:
    1. Preprocess: COLMAP on input photos
    2. Train: 3DGS model training
    3a. Export .ply (for splat rendering)
    3b. Extract mesh (for physics/avatar)
    4. Optimize: Decimate to VRChat limits
    5. Physics: Generate convex colliders
    6. Package: Bundle for VRChat

    Returns:
        Path to final VRChat package directory.
    """
    start_time = time.time()
    results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        # Stage 1: Preprocess
        task = progress.add_task("Preprocessing photos (COLMAP)...", total=None)
        try:
            data_dir = preprocess(cfg)
            results["data_dir"] = data_dir
            progress.update(task, description="[green]✓ Preprocessing done")
        except Exception as e:
            progress.update(task, description="[red]✗ Preprocessing failed")
            raise PipelineError("preprocess", str(e), e)

        # Stage 2: Train
        task = progress.add_task("Training 3DGS model...", total=None)
        try:
            model_dir = train(cfg, data_dir)
            results["model_dir"] = model_dir
            progress.update(task, description="[green]✓ Training done")
        except Exception as e:
            progress.update(task, description="[red]✗ Training failed")
            raise PipelineError("train", str(e), e)

        # Stage 3a: Export splat (.ply)
        splat_path = None
        if cfg.output_mode in (OutputMode.SPLAT, OutputMode.BOTH):
            task = progress.add_task("Exporting .ply splat...", total=None)
            try:
                splat_path = export_splat(cfg, model_dir)
                results["splat_path"] = splat_path
                progress.update(task, description="[green]✓ Splat exported")
            except Exception as e:
                progress.update(task, description="[yellow]⚠ Splat export failed (non-fatal)")
                log.warning(f"Splat export failed: {e}")

        # Stage 3b+4: Extract & optimize mesh
        mesh_path = None
        if cfg.output_mode in (OutputMode.MESH, OutputMode.BOTH):
            task = progress.add_task("Extracting mesh (SuGaR)...", total=None)
            try:
                raw_mesh = extract_mesh(cfg, model_dir, data_dir)
                progress.update(task, description="[green]✓ Mesh extracted")

                task2 = progress.add_task("Optimizing for VRChat...", total=None)
                mesh_path = optimize(cfg, raw_mesh)
                results["mesh_path"] = mesh_path
                progress.update(task2, description="[green]✓ Mesh optimized")
            except Exception as e:
                progress.update(task, description="[yellow]⚠ Mesh extraction failed (non-fatal)")
                log.warning(f"Mesh pipeline failed: {e}")

        # Stage 5: Physics colliders
        physics_dir = None
        if mesh_path and cfg.generate_colliders:
            task = progress.add_task("Generating physics colliders...", total=None)
            try:
                physics_dir = generate_physics(cfg, mesh_path)
                results["physics_dir"] = physics_dir
                progress.update(task, description="[green]✓ Physics done")
            except Exception as e:
                progress.update(task, description="[yellow]⚠ Physics failed (non-fatal)")
                log.warning(f"Physics generation failed: {e}")

        # Stage 6: Package
        task = progress.add_task("Packaging for VRChat...", total=None)
        try:
            pkg_dir = package_vrchat(cfg, splat_path, mesh_path, physics_dir)
            results["package_dir"] = pkg_dir
            progress.update(task, description="[green]✓ Package ready")
        except Exception as e:
            progress.update(task, description="[red]✗ Packaging failed")
            raise PipelineError("package", str(e), e)

    elapsed = time.time() - start_time
    console.print(f"\n[bold green]Done![/] Total time: {elapsed:.0f}s")
    console.print(f"Output: [cyan]{results['package_dir']}[/]")

    return results["package_dir"]
