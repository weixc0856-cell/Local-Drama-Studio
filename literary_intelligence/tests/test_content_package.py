from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from literary_intelligence.schemas.content_package import ContentPackage
from literary_intelligence.schemas.export_schemas import export_schemas


def package() -> dict:
    return {
        "work": {
            "work_id": "work_test_short",
            "title": "测试短文本",
            "author": "测试作者",
            "dynasty": "测试朝代",
            "source_id": "src_test_short",
            "source_version": "test fixture",
            "source_license_status": "PASS_STATIC",
        },
        "positioning": {
            "target_text": "白日依山尽",
            "target_locator": "测试文本/首句/第1句",
            "surrounding_context": ["白日依山盡", "長風過野原"],
        },
        "analysis": {
            "text_analysis": ["两个并列的明喻结构"],
            "literary_interpretation": [{
                "statement": "动态意象形成复合描写",
                "claim_refs": ["short_obs_002"],
                "confidence": "medium",
            }],
            "imagery": [{"image": "白日", "meaning": "测试意象", "claim_refs": ["short_obs_002"]}],
            "emotion": ["灵动"],
            "artistic_features": ["对偶"],
            "historical_context": [],
            "uncertainty_notes": ["解释仍待人工审核"],
        },
        "video": {
            "title_options": ["白日依山尽"],
            "opening_hook": "测试夹具：短文本开场。",
            "narration": "白日依山尽。",
            "scene_plan": [{
                "scene_id": "scene_001",
                "duration_seconds": 4.0,
                "visual_source": "assets/test/fixture.png",
                "camera_motion": "slow push-in",
                "visual_prompt": "测试画面",
                "subtitle_ids": ["sub_001"],
            }],
            "visual_prompts": ["测试画面"],
            "subtitle_segments": [{
                "segment_id": "sub_001",
                "text": "白日依山尽",
                "claim_refs": ["short_obs_002"],
                "estimated_duration_seconds": 4.0,
            }],
            "ending": "测试结尾。",
            "platform_metadata": {
                "title": "测试短文本",
                "description": "东方古典文学短视频",
                "tags": ["测试"],
                "ai_disclosure": "AI辅助制作",
            },
        },
        "provenance": {
            "source_refs": ["src_test_short"],
            "claim_refs": ["short_obs_002"],
            "verification_status": "draft",
            "generated_by": "LI-2 test",
            "generation_timestamp": "2026-11-03T00:00:00Z",
            "warnings": ["claims unreviewed"],
        },
    }


def test_valid_content_package() -> None:
    model = ContentPackage.model_validate(package())
    assert model.work.title == "测试短文本"
    assert model.video.scene_plan[0].subtitle_ids == ["sub_001"]


def test_duplicate_scene_rejected() -> None:
    data = deepcopy(package())
    data["video"]["scene_plan"].append(deepcopy(data["video"]["scene_plan"][0]))
    with pytest.raises(ValidationError):
        ContentPackage.model_validate(data)


def test_unknown_subtitle_rejected() -> None:
    data = deepcopy(package())
    data["video"]["scene_plan"][0]["subtitle_ids"] = ["sub_999"]
    with pytest.raises(ValidationError):
        ContentPackage.model_validate(data)


def test_unknown_claim_in_subtitle_rejected() -> None:
    data = deepcopy(package())
    data["video"]["subtitle_segments"][0]["claim_refs"] = ["not_in_provenance"]
    with pytest.raises(ValidationError):
        ContentPackage.model_validate(data)


def test_source_must_be_in_provenance() -> None:
    data = deepcopy(package())
    data["provenance"]["source_refs"] = []
    with pytest.raises(ValidationError):
        ContentPackage.model_validate(data)


def test_content_package_schema_export(tmp_path) -> None:
    written = export_schemas(tmp_path)
    assert any(p.name == "content_package.schema.json" for p in written)
