"""
测试数据模型
"""

import pytest
from datetime import datetime
from src.models import (
    VideoInfo,
    VideoDownload,
    TranscriptSegment,
    TranscriptResult,
    FilterResult,
    ContentSafetyResult,
    BloggerProfile,
    StyleRule,
    Persona,
    SkillExample,
    Skill,
    SkillScore,
    GenerationProgress,
    Config,
)


class TestVideoInfo:
    """测试VideoInfo模型"""

    def test_create_video_info(self):
        """测试创建VideoInfo"""
        info = VideoInfo(
            aweme_id="test123",
            title="测试视频",
            desc="这是描述",
            video_url="https://example.com/video.mp4",
            duration=60.0,
            publish_time=datetime.now(),
            author="测试博主",
        )
        assert info.aweme_id == "test123"
        assert info.title == "测试视频"
        assert info.author == "测试博主"


class TestTranscriptResult:
    """测试TranscriptResult模型"""

    def test_create_transcript_result(self):
        """测试创建TranscriptResult"""
        segments = [
            TranscriptSegment(start=0.0, end=2.5, text="你好"),
            TranscriptSegment(start=2.5, end=5.0, text="世界"),
        ]
        result = TranscriptResult(
            text="你好世界",
            segments=segments,
            language="zh",
        )
        assert result.text == "你好世界"
        assert len(result.segments) == 2
        assert result.language == "zh"


class TestBloggerProfile:
    """测试BloggerProfile模型"""

    def test_create_blogger_profile(self):
        """测试创建BloggerProfile"""
        profile = BloggerProfile(
            content_field="科技",
            core_topics=["AI", "编程", "创业"],
            expression_style="理性分析",
            tone_characteristic="犀利",
            persona_tags=["技术博主", "干货分享"],
            common_phrases=["听懂扣1", "记得点赞收藏"],
            target_audience="程序员",
        )
        assert profile.content_field == "科技"
        assert len(profile.core_topics) == 3
        assert "AI" in profile.core_topics


class TestSkill:
    """测试Skill模型"""

    def test_create_skill(self):
        """测试创建Skill"""
        persona = Persona(style="理性分析", tone="犀利", tags=["科技", "AI"])
        examples = [
            SkillExample(user="什么是AI?", assistant="AI就是..."),
        ]
        skill = Skill(
            name="科技博主AI",
            description="模仿科技博主说话",
            persona=persona,
            triggers=["科技", "AI"],
            system_prompt="你是一个科技博主...",
            examples=examples,
        )
        assert skill.name == "科技博主AI"
        assert len(skill.triggers) == 2
        assert len(skill.examples) == 1


class TestSkillScore:
    """测试SkillScore模型"""

    def test_overall_score(self):
        """测试总体评分计算"""
        score = SkillScore(
            purity=0.9,
            consistency=0.8,
            style=0.85,
            usability=0.9,
            reason="测试评分",
        )
        assert score.overall == pytest.approx(0.8625)


class TestConfig:
    """测试Config模型"""

    def test_default_values(self):
        """测试默认值"""
        config = Config(volc_ark_api_key="test-key")
        assert config.max_videos == 10
        assert config.min_videos_required == 5
        assert config.max_chars_per_video == 1000
        assert config.output_dir == "./output"
        assert config.volc_ark_api_key == "test-key"

    def test_custom_values(self):
        """测试自定义值"""
        config = Config(
            volc_ark_api_key="test-key",
            max_videos=20,
            min_videos_required=3,
            output_dir="./myoutput",
        )
        assert config.max_videos == 20
        assert config.min_videos_required == 3
        assert config.output_dir == "./myoutput"


class TestGenerationProgress:
    """测试GenerationProgress模型"""

    def test_to_dict(self):
        """测试to_dict方法"""
        progress = GenerationProgress(
            stage="下载",
            current=2,
            total=10,
            message="下载中...",
        )
        d = progress.to_dict()
        assert d["percentage"] == 20
        assert d["stage"] == "下载"
        assert d["message"] == "下载中..."
        assert "elapsed_seconds" in d
