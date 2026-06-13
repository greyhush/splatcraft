"""Stage 5: Optimize mesh — decimation, UV cleanup, VRChat limits."""
from __future__ import annotations

import logging
from pathlib import Path

from splatcraft.config import PipelineConfig
from splatcraft.utils.vrchat import get_target_triangles, validate_for_vrchat

log = logging.getLogger(__name__)


def optimize(cfg: PipelineConfig, mesh_path: Path) -> Path:
    """Optimize mesh for VRChat: decimate, fix normals, validate.

    Args:
        cfg: Pipeline configuration.
        mesh_path: Path to input .obj mesh.

    Returns:
        Path to optimized .obj mesh.
    """
    output_dir = cfg.output_dir / "mesh"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "splatcraft_optimized.obj"

    # Try trimesh first (pure Python, always available)
    try:
        return _optimize_trimesh(cfg, mesh_path, output_path)
    except ImportError:
        pass

    # Try Blender as fallback
    blender = _find_blender()
    if blender:
        return _optimize_blender(cfg, mesh_path, output_path, blender)

    # Last resort: just copy
    import shutil
    shutil.copy2(mesh_path, output_path)
    log.warning("No optimization tool available. Copied mesh as-is.")
    return output_path


def _optimize_trimesh(cfg: PipelineConfig, mesh_path: Path, output_path: Path) -> Path:
    """Optimize mesh using trimesh."""
    import trimesh
    import numpy as np

    log.info(f"Loading mesh: {mesh_path}")
    mesh = trimesh.load(str(mesh_path), force="mesh")
    original_faces = len(mesh.faces)
    log.info(f"Original: {original_faces:,} faces, {len(mesh.vertices):,} vertices")

    # Target triangle count
    target = get_target_triangles(cfg.target_platform, cfg.target_rank)

    if original_faces > target:
        ratio = target / original_faces
        log.info(f"Decimating {original_faces:,} → ~{target:,} faces (ratio {ratio:.3f})")

        try:
            # Try sklearn-based simplification
            mesh = _decimate_trimesh(mesh, target)
        except Exception as e:
            log.warning(f"Decimation failed ({e}), using vertex clustering")
            # Fallback: vertex clustering
            mesh = mesh.simplify_quadric_decimation(target)

        log.info(f"Decimated: {len(mesh.faces):,} faces")

    # Fix normals
    mesh.fix_normals()

    # Validate
    result = validate_for_vrchat(
        triangles=len(mesh.faces),
        platform=cfg.target_platform,
        target_rank=cfg.target_rank,
    )
    log.info(f"VRChat rank: {result.rank.value} ({'✓' if result.passes else '✗'})")
    for issue in result.issues:
        log.warning(f"  ⚠ {issue}")

    # Export
    mesh.export(str(output_path))
    log.info(f"Optimized mesh: {output_path}")
    return output_path


def _decimate_trimesh(mesh, target_faces: int):
    """Decimate mesh using trimesh's built-in simplification."""
    # trimesh doesn't have great decimation built-in,
    # but we can use simplify_quadric_decimation if available
    try:
        return mesh.simplify_quadric_decimation(target_faces)
    except AttributeError:
        # Try open3d if available
        try:
            import open3d as o3d
            o3d_mesh = o3d.geometry.TriangleMesh(
                vertices=o3d.utility.Vector3dVector(mesh.vertices),
                triangles=o3d.utility.Vector3iVector(mesh.faces),
            )
            if hasattr(mesh, 'vertex_normals') and mesh.vertex_normals is not None:
                o3d_mesh.vertex_normals = o3d.utility.Vector3dVector(mesh.vertex_normals)
            simplified = o3d_mesh.simplify_quadric_decimation(target_faces)
            return trimesh.Trimesh(
                vertices=np.asarray(simplified.vertices),
                faces=np.asarray(simplified.triangles),
            )
        except ImportError:
            raise RuntimeError("Need open3d for mesh decimation: pip install open3d")


def _optimize_blender(
    cfg: PipelineConfig, mesh_path: Path, output_path: Path, blender: str,
) -> Path:
    """Optimize mesh using Blender Python API."""
    import subprocess

    target = get_target_triangles(cfg.target_platform, cfg.target_rank)
    script = f"""
import bpy
import bmesh

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Import mesh
bpy.ops.import_scene.obj(filepath=r'{mesh_path}')
obj = bpy.context.selected_objects[0]
bpy.context.view_layer.objects.active = obj

# Decimate
original = len(obj.data.polygons)
if original > {target}:
    ratio = {target} / original
    mod = obj.modifiers.new(name='Decimate', type='DECIMATE')
    mod.ratio = ratio
    bpy.ops.object.modifier_apply(modifier='Decimate')

# Fix normals
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

# Export
bpy.ops.export_scene.obj(filepath=r'{output_path}')
print(f"Exported: {{len(obj.data.polygons)}} faces")
"""
    result = subprocess.run(
        [blender, "--background", "--python-expr", script],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Blender optimization failed:\n{result.stderr}")

    log.info(f"Blender optimized mesh: {output_path}")
    return output_path


def _find_blender() -> str | None:
    """Find Blender binary."""
    import shutil
    b = shutil.which("blender")
    if b:
        return b
    # Common Windows paths
    import os
    for candidate in [
        r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
        r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    ]:
        if os.path.exists(candidate):
            return candidate
    return None
