"""
测试存储模块
"""

import os
import json
import tempfile
from datetime import datetime
from src.storage import Storage
from src.models import Config, GenerationResult, GenerationHistory
from src.models import BloggerProfile, StyleRule, Skill, Persona, SkillExample, SkillScore


class TestStorage:
    """测试Storage"""

    def test_load_history_empty(self):
        """测试加载空历史"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)
            history = storage.load_history()
            assert isinstance(history, list)
            assert len(history) == 0

    def test_save_and_load_config(self):
        """测试保存和加载配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.json")
            storage = Storage(tmpdir)
            config = Config(
                volc_ark_api_key="test-key-123",
                max_videos=15,
                output_dir="./test_output",
            )
            storage.save_config(config, config_path)
            loaded = storage.load_config(config_path)
            assert loaded is not None
            assert loaded.volc_ark_api_key == "test-key-123"
            assert loaded.max_videos == 15
            assert loaded.output_dir == "./test_output"

    def test_get_next_version_new(self):
        """测试获取新版本号（新博主）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)
            version = storage.get_next_version("new_blogger")
            assert version == 1

    def test_add_to_history(self):
        """测试添加到历史"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)

            profile = BloggerProfile(
                content_field="科技",
                core_topics=["AI"],
                expression_style="理性",
                tone_characteristic="犀利",
                persona_tags=["技术"],
                common_phrases=["test"],
                target_audience="dev",
            )
            style = StyleRule(
                speech_structure="观点+例子",
                language_features="短句",
                emotion_intensity="中",
                uses_rhetoric=True,
                typical_sentences=["test"],
            )
            persona = Persona(style="理性", tone="犀利", tags=["AI"])
            examples = [SkillExample(user="q", assistant="a")]
            skill = Skill(
                name="TestSkill",
                description="desc",
                persona=persona,
                triggers=["test"],
                system_prompt="prompt",
                examples=examples,
            )
            score = SkillScore(
                purity=0.9,
                consistency=0.8,
                style=0.85,
                usability=0.9,
                reason="good",
            )
            result = GenerationResult(
                blogger_id="test_123",
                blogger_name="Test Blogger",
                input_url="https://test.com",
                videos_processed=10,
                videos_kept=8,
                profile=profile,
                style_rules=style,
                skill=skill,
                score=score,
                version=1,
            )

            item = storage.add_to_history(result, "/path/to/skill/SKILL.md")
            assert item.id is not None
            assert item.blogger_id == "test_123"
            assert item.blogger_name == "Test Blogger"

            history = storage.load_history()
            assert len(history) == 1

    def test_delete_history(self):
        """测试删除历史"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = Storage(tmpdir)
            history = storage.load_history()
            assert len(history) == 0

            item = GenerationHistory(
                id="test_id",
                blogger_name="Test",
                blogger_id="t1",
                created_at=datetime.now(),
                version=1,
                overall_score=0.8,
                skill_json_path="/test.json",
                status="completed",
            )
            history.append(item)
            storage.save_history(history)

            assert len(storage.load_history()) == 1
            deleted = storage.delete_history("test_id")
            assert deleted
            assert len(storage.load_history()) == 0
