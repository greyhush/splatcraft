"""SplatCraft CLI — Photo → 3DGS → VRChat."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import typer
from rich.console import Console

from splatcraft.config import PipelineConfig, OutputMode, TrainBackend
from splatcraft.utils.vrchat import Platform, PerformanceRank

app = typer.Typer(
    name="splatcraft",
    help="📸→🫧→🎮 Photo to VRChat 3DGS asset pipeline",
    add_completion=False,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def build(
    input_dir: Path = typer.Argument(..., help="Directory with input photos"),
    output_dir: Path = typer.Option(Path("output"), "-o", "--output", help="Output directory"),
    mode: OutputMode = typer.Option(OutputMode.BOTH, "-m", "--mode", help="Output mode"),
    backend: TrainBackend = typer.Option(TrainBackend.NERFSTUDIO, "-b", "--backend"),
    iterations: int = typer.Option(30000, "-i", "--iterations", help="Training iterations"),
    platform: Platform = typer.Option(Platform.PC, "-p", "--platform"),
    rank: PerformanceRank = typer.Option(PerformanceRank.GOOD, "-r", "--rank"),
    high_poly: bool = typer.Option(False, "--high-poly", help="High poly mesh extraction"),
    no_physics: bool = typer.Option(False, "--no-physics", help="Skip collider generation"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Build VRChat asset from photos."""
    _setup_logging(verbose)

    if not input_dir.exists():
        console.print(f"[red]Input directory not found: {input_dir}")
        raise typer.Exit(1)

    cfg = PipelineConfig(
        input_dir=input_dir,
        output_dir=output_dir,
        output_mode=mode,
        backend=backend,
        max_iterations=iterations,
        target_platform=platform,
        target_rank=rank,
        extract_high_poly=high_poly,
        generate_colliders=not no_physics,
    )

    from splatcraft.pipeline import run_pipeline, PipelineError
    try:
        pkg = run_pipeline(cfg)
        console.print(f"\n[bold]Package:[/] {pkg}")
    except PipelineError as e:
        console.print(f"\n[red bold]Pipeline failed at [{e.stage}]:[/] {e}")
        raise typer.Exit(1)


@app.command()
def check():
    """Check system requirements (GPU, dependencies)."""
    from splatcraft.utils.gpu import detect_gpu, check_vram
    import shutil

    console.print("[bold]SplatCraft System Check[/]\n")

    # GPU
    gpu = detect_gpu()
    if gpu:
        console.print(f"  GPU:     [green]{gpu.name}[/] ({gpu.vram_total_mb}MB)")
    else:
        console.print("  GPU:     [red]Not detected[/]")

    # Dependencies - check PATH and venv Scripts
    import sys
    venv_scripts = str(Path(sys.prefix) / "Scripts") if sys.platform == "win32" else str(Path(sys.prefix) / "bin")

    deps = {
        "ns-process-data": "nerfstudio (pip install nerfstudio)",
        "ns-train": "nerfstudio (pip install nerfstudio)",
        "ns-export": "nerfstudio (pip install nerfstudio)",
        "colmap": "COLMAP (colmap-3.9-windows)",
        "blender": "Blender (blender.org)",
        "coacd": "CoACD (pip install coacd)",
    }
    console.print("\n  [bold]Dependencies:[/]")
    for cmd, desc in deps.items():
        found = shutil.which(cmd) or shutil.which(cmd, path=venv_scripts)
        status = "[green]+[/]" if found else "[yellow]-[/]"
        console.print(f"    {status} {cmd:<20} {desc}")

    # Python packages
    console.print("\n  [bold]Python packages:[/]")
    for pkg in ["trimesh", "numpy", "torch", "gsplat"]:
        try:
            __import__(pkg)
            console.print(f"    [green]+[/] {pkg}")
        except ImportError:
            console.print(f"    [yellow]-[/] {pkg}")


@app.command()
def gui(
    port: int = typer.Option(7860, "-p", "--port"),
    share: bool = typer.Option(False, "--share", help="Create public link"),
):
    """Launch Gradio web interface."""
    try:
        from splatcraft.ui.gradio_app import create_app
        app = create_app()
        app.launch(server_port=port, share=share)
    except ImportError:
        console.print("[red]Gradio not installed. Run: pip install gradio")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
