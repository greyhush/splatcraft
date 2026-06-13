"""Gradio web UI for SplatCraft."""
from __future__ import annotations

import logging
import tempfile
import threading
from pathlib import Path

log = logging.getLogger(__name__)


def create_app():
    """Create Gradio application."""
    import gradio as gr
    from splatcraft.config import PipelineConfig, OutputMode, TrainBackend
    from splatcraft.utils.vrchat import Platform, PerformanceRank
    from splatcraft.utils.gpu import detect_gpu

    gpu = detect_gpu()
    gpu_info = f"{gpu.name} ({gpu.vram_total_mb}MB)" if gpu else "No GPU detected"

    def run_build(
        files, output_mode, backend, iterations, platform, rank, high_poly, generate_colliders,
    ):
        """Run pipeline from uploaded files."""
        if not files:
            return "❌ No files uploaded", None

        # Save uploaded files to temp directory
        input_dir = Path(tempfile.mkdtemp(prefix="splatcraft_input_"))
        for file in files:
            # Gradio gives us temp file paths
            import shutil
            dest = input_dir / Path(file).name
            shutil.copy2(file, dest)

        output_dir = Path(tempfile.mkdtemp(prefix="splatcraft_output_"))

        cfg = PipelineConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            output_mode=OutputMode(output_mode),
            backend=TrainBackend(backend),
            max_iterations=int(iterations),
            target_platform=Platform(platform),
            target_rank=PerformanceRank(rank),
            extract_high_poly=high_poly,
            generate_colliders=generate_colliders,
        )

        from splatcraft.pipeline import run_pipeline, PipelineError
        try:
            pkg_dir = run_pipeline(cfg)
            return f"✅ Done! Output: {pkg_dir}", str(pkg_dir)
        except PipelineError as e:
            return f"❌ Failed at [{e.stage}]: {e}", None
        except Exception as e:
            return f"❌ Error: {e}", None

    def run_check():
        """System check."""
        from splatcraft.utils.gpu import detect_gpu
        import shutil as sh

        lines = ["## System Check\n"]

        g = detect_gpu()
        lines.append(f"**GPU:** {g.name} ({g.vram_total_mb}MB)" if g else "**GPU:** ❌ Not found")

        deps = ["ns-process-data", "ns-train", "ns-export", "colmap", "blender", "coacd"]
        lines.append("\n### Dependencies")
        for cmd in deps:
            found = sh.which(cmd)
            lines.append(f"- {'✅' if found else '❌'} `{cmd}`")

        return "\n".join(lines)

    with gr.Blocks(title="SplatCraft", theme=gr.themes.Soft()) as demo:
        gr.Markdown("""
# 📸 SplatCraft
### Photo → 3D Gaussian Splatting → VRChat Asset

Upload photos of an object from multiple angles. SplatCraft trains a 3DGS model
and exports VRChat-ready assets.
""")

        with gr.Row():
            with gr.Column():
                file_input = gr.File(
                    label="📸 Input Photos",
                    file_count="multiple",
                    file_types=["image"],
                    height=200,
                )
                with gr.Row():
                    output_mode = gr.Radio(
                        ["splat", "mesh", "both"],
                        value="both",
                        label="Output Mode",
                        info="splat=.ply for VRChat worlds, mesh=.obj with physics",
                    )
                    backend = gr.Radio(
                        ["nerfstudio", "opensplat", "original"],
                        value="nerfstudio",
                        label="3DGS Backend",
                    )

                with gr.Row():
                    iterations = gr.Slider(
                        5000, 100000, value=30000, step=5000,
                        label="Training Iterations",
                        info="More = better quality, slower",
                    )

                with gr.Row():
                    platform = gr.Radio(["pc", "quest"], value="pc", label="Target Platform")
                    rank = gr.Radio(
                        ["excellent", "good", "medium", "poor"],
                        value="good", label="Performance Rank",
                    )

                with gr.Row():
                    high_poly = gr.Checkbox(label="High Poly Mesh", value=False)
                    generate_colliders = gr.Checkbox(label="Generate Physics", value=True)

                build_btn = gr.Button("🚀 Build", variant="primary", size="lg")

            with gr.Column():
                status = gr.Textbox(label="Status", lines=5, interactive=False)
                output_path = gr.Textbox(label="Output Path", interactive=False)
                check_btn = gr.Button("🔍 System Check")
                check_output = gr.Markdown()

        build_btn.click(
            fn=run_build,
            inputs=[file_input, output_mode, backend, iterations, platform, rank, high_poly, generate_colliders],
            outputs=[status, output_path],
        )
        check_btn.click(fn=run_check, outputs=[check_output])

        gr.Markdown(f"""
---
**System:** {gpu_info} | **SplatCraft v0.1.0**
[GitHub](https://github.com/greyhush/splatcraft) | [VRChatGaussianSplatting](https://github.com/MichaelMoroz/VRChatGaussianSplatting)
""")

    return demo
