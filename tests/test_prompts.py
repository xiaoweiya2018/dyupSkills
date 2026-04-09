"""
测试Prompt模板
"""

from src.prompts import Prompts


class TestPrompts:
    """测试Prompts"""

    def test_blogger_profile_extraction(self):
        """测试博主画像Prompt"""
        prompt = Prompts.blogger_profile_extraction("这是测试内容")
        assert "专业的内容分析专家" in prompt
        assert "这是测试内容" in prompt
        assert "content_field" in prompt
        assert "core_topics" in prompt

    def test_style_modeling(self):
        """测试风格建模Prompt"""
        prompt = Prompts.style_modeling("转写内容", '{"content_field": "科技"}')
        assert "模仿该博主的说话方式" in prompt
        assert "转写内容" in prompt
        assert "speech_structure" in prompt
        assert "typical_sentences" in prompt

    def test_skill_generation(self):
        """测试Skill生成Prompt"""
        prompt = Prompts.skill_generation(
            '{"content_field": "科技"}',
            '{"style": "理性"}',
            "内容摘要",
        )
        assert "OpenClaw Skill设计专家" in prompt
        assert "system_prompt" in prompt
        assert "examples" in prompt
        assert "优先模仿语气" in prompt

    def test_truncate_transcripts(self):
        """测试截断文本"""
        texts = ["第一段", "第二段", "第三段"]
        result = Prompts.truncate_transcripts(texts, 10)
        assert "第一段" in result
        sep_len = len("\n\n---\n\n")
        assert len(result) <= 10 + sep_len * (len(texts) - 1)

    def test_truncate_transcripts_large(self):
        """测试截断大文本"""
        texts = ["a" * 100 for _ in range(10)]
        result = Prompts.truncate_transcripts(texts, 250)
        assert len(result) <= 250 + len("\n\n---\n\n") * 2

    def test_content_safety_check(self):
        """测试内容安全检测Prompt"""
        prompt = Prompts.content_safety_check("测试文本")
        assert "risk" in prompt
        assert "攻击性语言" in prompt

    def test_skill_evaluation(self):
        """测试Skill评分Prompt"""
        prompt = Prompts.skill_evaluation("{}")
        assert "纯度" in prompt
        assert "风格还原度" in prompt
        assert "purity" in prompt
