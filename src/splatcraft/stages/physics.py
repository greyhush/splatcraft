"""Stage 6: Generate physics colliders via convex decomposition."""
from __future__ import annotations

import json
import logging
import subprocess
import shutil
from pathlib import Path

from splatcraft.config import PipelineConfig

log = logging.getLogger(__name__)


def generate_physics(cfg: PipelineConfig, mesh_path: Path) -> Path:
    """Generate convex hull colliders for VRChat physics.

    Uses CoACD (Approximate Convex Decomposition) to break the mesh
    into convex hulls that work as Unity MeshColliders.

    Args:
        cfg: Pipeline configuration.
        mesh_path: Path to optimized .obj mesh.

    Returns:
        Path to physics directory containing collider meshes + metadata.
    """
    output_dir = cfg.output_dir / "physics"
    output_dir.mkdir(parents=True, exist_ok=True)

    if cfg.collider_method == "coacd":
        collider_dir = _decompose_coacd(mesh_path, output_dir)
    elif cfg.collider_method == "vhacd":
        collider_dir = _decompose_vhacd(mesh_path, output_dir)
    else:
        raise ValueError(f"Unknown collider method: {cfg.collider_method}")

    # Generate metadata for Unity import
    _generate_unity_metadata(collider_dir, output_dir)

    log.info(f"Physics colliders: {output_dir}")
    return output_dir


def _decompose_coacd(mesh_path: Path, output_dir: Path) -> Path:
    """Convex decomposition via CoACD."""
    coacd = shutil.which("coacd")
    collider_dir = output_dir / "colliders"
    collider_dir.mkdir(exist_ok=True)

    output_mesh = collider_dir / "colliders.obj"

    if coacd:
        cmd = [
            coacd,
            "-i", str(mesh_path),
            "-o", str(output_mesh),
            "-t", "0.05",  # threshold (lower = more convex parts)
            "-n", "20",     # max convex parts
        ]
        log.info(f"Running CoACD convex decomposition")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"CoACD failed:\n{result.stderr}")
    else:
        # Try Python coacd package
        try:
            import coacd
            log.info("Running CoACD (Python)")
            # Python API usage
            result = coacd.run_coacd(
                str(mesh_path),
                threshold=0.05,
                max_convex_hulls=20,
            )
            if result:
                import trimesh
                mesh = trimesh.load(str(mesh_path), force="mesh")
                parts = coacd.run_coacd(mesh, threshold=0.05, max_convex_hulls=20)
                # Export each part
                for i, part in enumerate(parts):
                    part.export(str(collider_dir / f"collider_{i:03d}.obj"))
        except ImportError:
            raise RuntimeError(
                "CoACD not found. Install:\n"
                "  pip install coacd\n"
                "  OR download from github.com/SarahWeiii/coacd"
            )

    log.info(f"Collider meshes: {collider_dir}")
    return collider_dir


def _decompose_vhacd(mesh_path: Path, output_dir: Path) -> Path:
    """Convex decomposition via V-HACD."""
    vhacd = shutil.which("vhacd") or shutil.which("TestVHACD")
    collider_dir = output_dir / "colliders"
    collider_dir.mkdir(exist_ok=True)

    if not vhacd:
        raise RuntimeError(
            "V-HACD not found. Install from: github.com/kmammou/v-hacd"
        )

    output_mesh = collider_dir / "colliders.obj"
    cmd = [vhacd, str(mesh_path), "-o", str(output_mesh)]
    log.info("Running V-HACD convex decomposition")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"V-HACD failed:\n{result.stderr}")

    return collider_dir


def _generate_unity_metadata(collider_dir: Path, output_dir: Path) -> None:
    """Generate Unity import script and metadata."""
    collider_files = sorted(collider_dir.glob("*.obj"))

    metadata = {
        "collider_count": len(collider_files),
        "collider_files": [f.name for f in collider_files],
        "unity_import_script": "setup_physics.cs",
    }

    # Write metadata
    with open(output_dir / "physics_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    # Generate Unity C# setup script
    unity_script = _generate_unity_csharp(collider_files)
    with open(output_dir / "setup_physics.cs", "w") as f:
        f.write(unity_script)

    log.info(f"Generated Unity metadata + setup script")


def _generate_unity_csharp(collider_files: list[Path]) -> str:
    """Generate C# script for Unity that adds MeshColliders."""
    file_list = "\n".join(
        f'            colliderMeshes.Add(Resources.Load<Mesh>("colliders/{f.stem}"));'
        for f in collider_files
    )
    return f"""using UnityEngine;
using System.Collections.Generic;

/// <summary>
/// SplatCraft auto-generated physics setup.
/// Attach this to your VRChat prop/asset root.
/// </summary>
public class SplatCraftPhysics : MonoBehaviour
{{
    [Header("Collider Settings")]
    public PhysicMaterial physicsMaterial;
    public bool isTrigger = false;

    [Header("Collider Meshes")]
    public List<Mesh> colliderMeshes = new List<Mesh>();

    void Start()
    {{
        SetupColliders();
    }}

    void SetupColliders()
    {{
        // Auto-loaded collider meshes
{file_list}

        foreach (var mesh in colliderMeshes)
        {{
            if (mesh == null) continue;
            var go = new GameObject($"collider_{{mesh.name}}");
            go.transform.SetParent(transform);
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = Quaternion.identity;

            var mc = go.AddComponent<MeshCollider>();
            mc.sharedMesh = mesh;
            mc.convex = true;
            mc.isTrigger = isTrigger;

            if (physicsMaterial != null)
                mc.material = physicsMaterial;
        }}

        Debug.Log($"[SplatCraft] Added {{colliderMeshes.Count}} convex colliders");
    }}
}}
"""
