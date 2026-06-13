"""Basic tests for SplatCraft."""
import pytest
from pathlib import Path

from splatcraft.config import PipelineConfig, OutputMode
from splatcraft.utils.vrchat import (
    validate_for_vrchat, Platform, PerformanceRank, get_target_triangles,
)


class TestConfig:
    def test_default_config(self):
        cfg = PipelineConfig()
        assert cfg.output_mode == OutputMode.BOTH
        assert cfg.max_iterations == 30000

    def test_intermediate_dir(self, tmp_path):
        cfg = PipelineConfig(work_dir=tmp_path / "work")
        d = cfg.intermediate_dir("test_stage")
        assert d.exists()
        assert d.name == "test_stage"


class TestVRChatValidation:
    def test_excellent_pc(self):
        result = validate_for_vrchat(
            triangles=30000, materials=4, bones=75,
            platform=Platform.PC, target_rank=PerformanceRank.EXCELLENT,
        )
        assert result.passes
        assert result.rank == PerformanceRank.EXCELLENT

    def test_exceeds_excellent(self):
        result = validate_for_vrchat(
            triangles=50000, materials=4, bones=75,
            platform=Platform.PC, target_rank=PerformanceRank.EXCELLENT,
        )
        assert not result.passes
        assert len(result.issues) > 0

    def test_quest_limits(self):
        result = validate_for_vrchat(
            triangles=8000, materials=3, bones=75,
            platform=Platform.QUEST, target_rank=PerformanceRank.GOOD,
        )
        assert result.passes

    def test_target_triangles(self):
        assert get_target_triangles(Platform.PC, PerformanceRank.GOOD) == 70_000
        assert get_target_triangles(Platform.QUEST, PerformanceRank.EXCELLENT) == 7_500


class TestGPU:
    def test_detect_gpu(self):
        from splatcraft.utils.gpu import detect_gpu
        # Just verify it runs without crashing
        gpu = detect_gpu()
        # May or may not find GPU depending on environment
