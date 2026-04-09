"""
AI内容整合与Skill生成模块
"""

import json
import re
from typing import Iterable, Optional, List
from loguru import logger
from .models import (
    BloggerProfile,
    StyleRule,
    Skill,
    Persona,
    SkillExample,
    SkillScore,
)
from .prompts import Prompts
from .volc_ark import ArkClient


class AIGenerator:
    """AI生成器"""

    def __init__(self, client: ArkClient, model: str = "Doubao-Seed-2.0-lite"):
        self.client = client
        self.model = model

    def generate_blogger_profile(
        self,
        transcripts: List[str],
        max_total_chars: int = 5000,
    ) -> Optional[BloggerProfile]:
        """生成博主画像"""
        combined = Prompts.truncate_transcripts(transcripts, max_total_chars)
        prompt = Prompts.blogger_profile_extraction(combined)

        try:
            content = self.client.chat_completions(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout_seconds=180,
            )
        except Exception as e:
            logger.error(f"生成博主画像失败: {e}")
            return None

        if not content:
            return None

        try:
            data = json.loads(self._extract_json(content))
            profile = BloggerProfile(**data)
            logger.info(f"生成博主画像完成: {profile.content_field}")
            return profile
        except Exception as e:
            logger.error(f"解析博主画像失败: {e}, content: {content[:200]}")
            return None

    def generate_style_rules(
        self,
        transcripts: List[str],
        profile: BloggerProfile,
        max_total_chars: int = 5000,
    ) -> Optional[StyleRule]:
        """生成风格规则"""
        combined = Prompts.truncate_transcripts(transcripts, max_total_chars)
        profile_json = json.dumps(profile.model_dump(), ensure_ascii=False, indent=2)
        prompt = Prompts.style_modeling(combined, profile_json)

        try:
            content = self.client.chat_completions(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                timeout_seconds=180,
            )
        except Exception as e:
            logger.error(f"生成风格规则失败: {e}")
            return None

        if not content:
            return None

        try:
            data = json.loads(self._extract_json(content))
            style_rule = StyleRule(**data)
            logger.info(f"生成风格规则完成: {style_rule.emotion_intensity}")
            return style_rule
        except Exception as e:
            logger.error(f"解析风格规则失败: {e}")
            return None

    def generate_skill(
        self,
        profile: BloggerProfile,
        style_rules: StyleRule,
        transcripts: List[str],
        max_total_chars: int = 5000,
    ) -> Optional[Skill]:
        """生成Skill"""
        combined = Prompts.truncate_transcripts(transcripts, max_total_chars)
        profile_json = json.dumps(profile.model_dump(), ensure_ascii=False, indent=2)
        style_json = json.dumps(style_rules.model_dump(), ensure_ascii=False, indent=2)
        prompt = Prompts.skill_generation(profile_json, style_json, combined)

        try:
            content = self.client.chat_completions(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                timeout_seconds=300,
            )
        except Exception as e:
            logger.error(f"生成Skill失败: {e}")
            return None

        if not content:
            return None

        try:
            data = json.loads(self._extract_json(content))
            persona = Persona(**data["persona"])
            examples = [SkillExample(**ex) for ex in data["examples"]]
            skill = Skill(
                name=data["name"],
                description=data["description"],
                persona=persona,
                triggers=data["triggers"],
                system_prompt=data["system_prompt"],
                examples=examples,
            )
            logger.info(f"生成Skill完成: {skill.name}")
            return skill
        except Exception as e:
            logger.error(f"解析Skill失败: {e}")
            return None

    def evaluate_skill(self, skill: Skill) -> Optional[SkillScore]:
        """评估Skill质量"""
        skill_json = json.dumps(skill.model_dump(), ensure_ascii=False, indent=2)
        prompt = Prompts.skill_evaluation(skill_json)

        try:
            content = self.client.chat_completions(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                timeout_seconds=180,
            )
        except Exception as e:
            logger.error(f"Skill评分失败: {e}")
            return None

        if not content:
            return None

        try:
            data = json.loads(self._extract_json(content))
            score = SkillScore(**data)
            logger.info(f"Skill评分完成: 总体 {score.overall:.2f}")
            return score
        except Exception as e:
            logger.error(f"解析评分结果失败: {e}")
            return None

    def chat_with_skill(self, skill: Skill, user_message: str) -> Optional[str]:
        """与Skill对话测试"""
        messages = [
            {"role": "system", "content": skill.system_prompt},
        ]

        for ex in skill.examples:
            messages.append({"role": "user", "content": ex.user})
            messages.append({"role": "assistant", "content": ex.assistant})

        messages.append({"role": "user", "content": user_message})

        try:
            content = self.client.chat_completions(
                model=self.model,
                messages=messages,
                temperature=0.7,
                timeout_seconds=180,
            )
        except Exception as e:
            logger.error(f"Skill对话失败: {e}")
            return None

        return content

    def chat_with_skill_stream(self, skill: Skill, user_message: str) -> Iterable[str]:
        messages = [
            {"role": "system", "content": skill.system_prompt},
        ]

        for ex in skill.examples:
            messages.append({"role": "user", "content": ex.user})
            messages.append({"role": "assistant", "content": ex.assistant})

        messages.append({"role": "user", "content": user_message})

        return self.client.chat_completions_stream(
            model=self.model,
            messages=messages,
            temperature=0.7,
            timeout_seconds=180,
        )

    def _extract_json(self, text: str) -> str:
        """提取JSON内容"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0)
        return text
