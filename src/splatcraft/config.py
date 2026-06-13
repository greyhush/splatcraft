"""Configuration for SplatCraft pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from splatcraft.utils.vrchat import Platform, PerformanceRank


class OutputMode(Enum):
    SPLAT = "splat"        # .ply for VRChatGaussianSplatting (no mesh needed)
    MESH = "mesh"          # .obj/.fbx with physics colliders
    BOTH = "both"          # Both splat and mesh


class TrainBackend(Enum):
    NERFSTUDIO = "nerfstudio"   # nerfstudio + gsplat (recommended)
    OPENSPLAT = "opensplat"     # OpenSplat (C++, cross-platform)
    ORIGINAL = "original"       # Original reference implementation


@dataclass
class PipelineConfig:
    """Full pipeline configuration."""
    # Input
    input_dir: Path = field(default_factory=lambda: Path("input"))
    output_dir: Path = field(default_factory=lambda: Path("output"))

    # Output mode
    output_mode: OutputMode = OutputMode.BOTH

    # Training
    backend: TrainBackend = TrainBackend.NERFSTUDIO
    max_iterations: int = 30_000
    resolution: int = 1  # 1=full, 2=half, 4=quarter

    # Mesh extraction
    extract_high_poly: bool = False  # SuGaR: True=1M verts, False=200k

    # Optimization
    target_platform: Platform = Platform.PC
    target_rank: PerformanceRank = PerformanceRank.GOOD
    texture_size: int = 2048

    # Physics
    generate_colliders: bool = True
    collider_method: str = "coacd"  # "coacd" or "vhacd"

    # Paths (auto-populated)
    work_dir: Path = field(default_factory=lambda: Path(".splatcraft_work"))

    def intermediate_dir(self, stage: str) -> Path:
        """Get intermediate output directory for a stage."""
        d = self.work_dir / stage
        d.mkdir(parents=True, exist_ok=True)
        return d
