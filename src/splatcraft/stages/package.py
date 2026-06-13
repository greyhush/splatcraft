"""Stage 7: Package everything for VRChat."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from splatcraft.config import PipelineConfig, OutputMode
from splatcraft.utils.vrchat import validate_for_vrchat, Platform

log = logging.getLogger(__name__)


def package_vrchat(
    cfg: PipelineConfig,
    splat_path: Path | None = None,
    mesh_path: Path | None = None,
    physics_dir: Path | None = None,
) -> Path:
    """Package all outputs into a VRChat-ready directory.

    Creates a clean output folder with:
    - .ply file (for VRChatGaussianSplatting)
    - .obj/.fbx mesh (for avatar/world props)
    - Physics colliders
    - Unity setup instructions
    - README with upload steps

    Returns:
        Path to package directory.
    """
    pkg_dir = cfg.output_dir / "vrchat_package"
    pkg_dir.mkdir(parents=True, exist_ok=True)

    files = {}

    # Copy splat
    if splat_path and splat_path.exists():
        dest = pkg_dir / splat_path.name
        shutil.copy2(splat_path, dest)
        files["splat"] = str(dest)
        log.info(f"Packaged splat: {dest}")

    # Copy mesh
    if mesh_path and mesh_path.exists():
        dest = pkg_dir / mesh_path.name
        shutil.copy2(mesh_path, dest)
        files["mesh"] = str(dest)
        log.info(f"Packaged mesh: {dest}")

    # Copy physics
    if physics_dir and physics_dir.exists():
        physics_dest = pkg_dir / "physics"
        if physics_dest.exists():
            shutil.rmtree(physics_dest)
        shutil.copytree(physics_dir, physics_dest)
        files["physics"] = str(physics_dest)
        log.info(f"Packaged physics: {physics_dest}")

    # Generate README
    readme = _generate_readme(cfg, files)
    with open(pkg_dir / "README.md", "w") as f:
        f.write(readme)

    # Generate package info
    info = {
        "splatcraft_version": "0.1.0",
        "output_mode": cfg.output_mode.value,
        "platform": cfg.target_platform.value,
        "files": files,
    }
    with open(pkg_dir / "package_info.json", "w") as f:
        json.dump(info, f, indent=2)

    log.info(f"VRChat package: {pkg_dir}")
    return pkg_dir


def _generate_readme(cfg: PipelineConfig, files: dict) -> str:
    """Generate upload instructions."""
    sections = ["# SplatCraft VRChat Package\n"]

    if "splat" in files:
        sections.append("""## Option A: Gaussian Splat Rendering (Worlds)

This uses VRChat's native 3DGS support for photorealistic rendering.

### Setup:
1. Install [VRChatGaussianSplatting](https://github.com/MichaelMoroz/VRChatGaussianSplatting) Unity package
2. Open your VRChat world project in Unity
3. Drag the `.ply` file into Unity's Project window
4. The package auto-generates a prefab with materials
5. Place the prefab in your world scene
6. Upload via VRChat SDK → Builder → Build & Publish

### Notes:
- Best for static objects (furniture, decorations, landmarks)
- No physics — use colliders separately if needed
- MSAA must be OFF in project settings
- Works on PC and Quest (with limitations)
""")

    if "mesh" in files:
        sections.append(f"""## Option B: Mesh with Physics (Avatars/Props)

Traditional mesh-based asset with auto-generated colliders.

### Setup:
1. Import the `.obj` file into Blender or Unity
2. Import physics colliders from `physics/` folder
3. For avatars: Set up Humanoid rig → Add VRCAvatarDescriptor
4. For props: Attach to world or avatar
5. Upload via VRChat SDK

### Performance:
- Platform: {cfg.target_platform.value}
- Target rank: {cfg.target_rank.value}
- Use VRChat's Avatar Performance Rank to verify
""")

    sections.append("""## Troubleshooting

- **Splat looks weird**: Ensure photos cover all angles, good lighting, no motion blur
- **Mesh has holes**: Try more input images or different COLMAP settings
- **Physics colliders too complex**: Reduce CoACD threshold or max parts
- **Quest not working**: Check polygon limits (7.5k for Excellent)
""")

    return "\n".join(sections)
