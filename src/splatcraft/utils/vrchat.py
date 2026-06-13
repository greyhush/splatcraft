"""VRChat performance limits and validation."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Platform(Enum):
    PC = "pc"
    QUEST = "quest"


class PerformanceRank(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    MEDIUM = "medium"
    POOR = "poor"


# VRChat avatar performance limits
# https://docs.vrchat.com/docs/avatar-performance-ranking-system
AVATAR_LIMITS = {
    Platform.PC: {
        PerformanceRank.EXCELLENT: {"triangles": 32_000, "materials": 4, "bones": 75},
        PerformanceRank.GOOD: {"triangles": 70_000, "materials": 8, "bones": 150},
        PerformanceRank.MEDIUM: {"triangles": 70_000, "materials": 16, "bones": 256},
        PerformanceRank.POOR: {"triangles": 70_000, "materials": 32, "bones": 400},
    },
    Platform.QUEST: {
        PerformanceRank.EXCELLENT: {"triangles": 7_500, "materials": 2, "bones": 75},
        PerformanceRank.GOOD: {"triangles": 10_000, "materials": 4, "bones": 150},
        PerformanceRank.MEDIUM: {"triangles": 15_000, "materials": 8, "bones": 200},
        PerformanceRank.POOR: {"triangles": 20_000, "materials": 16, "bones": 256},
    },
}

# World props don't have strict limits but these are reasonable targets
WORLD_PROP_TARGETS = {
    "max_triangles": 100_000,
    "max_materials": 16,
    "max_texture_size": 2048,
}


@dataclass
class ValidationResult:
    platform: Platform
    rank: PerformanceRank
    triangles: int
    materials: int
    passes: bool
    issues: list[str]


def validate_for_vrchat(
    triangles: int,
    materials: int = 1,
    bones: int = 0,
    platform: Platform = Platform.PC,
    target_rank: PerformanceRank = PerformanceRank.GOOD,
) -> ValidationResult:
    """Check if mesh stats meet VRChat performance requirements."""
    limits = AVATAR_LIMITS[platform][target_rank]
    issues = []

    if triangles > limits["triangles"]:
        issues.append(
            f"Triangles {triangles:,} > {limits['triangles']:,} ({target_rank.value}/{platform.value})"
        )
    if materials > limits["materials"]:
        issues.append(
            f"Materials {materials} > {limits['materials']} ({target_rank.value}/{platform.value})"
        )
    if bones > limits["bones"]:
        issues.append(
            f"Bones {bones} > {limits['bones']} ({target_rank.value}/{platform.value})"
        )

    # Determine actual rank
    actual_rank = PerformanceRank.EXCELLENT
    for rank in PerformanceRank:
        rank_limits = AVATAR_LIMITS[platform][rank]
        if (triangles <= rank_limits["triangles"]
                and materials <= rank_limits["materials"]
                and bones <= rank_limits["bones"]):
            actual_rank = rank
            break
    else:
        actual_rank = PerformanceRank.POOR

    return ValidationResult(
        platform=platform,
        rank=actual_rank,
        triangles=triangles,
        materials=materials,
        passes=len(issues) == 0,
        issues=issues,
    )


def get_target_triangles(
    platform: Platform = Platform.PC,
    target_rank: PerformanceRank = PerformanceRank.GOOD,
) -> int:
    """Get target triangle count for given platform/rank."""
    return AVATAR_LIMITS[platform][target_rank]["triangles"]
