"""
内容安全检测模块 - GPT + 关键词规则
"""

import json
import re
from typing import Optional, List
from loguru import logger
from .models import ContentSafetyResult
from .prompts import Prompts
from .volc_ark import ArkClient


class ContentSafetyChecker:
    """内容安全检测器"""

    BAD_WORDS = [
        "脏话", "侮辱", "歧视", "仇恨", "暴力", "恐怖", "色情", "低俗",
        "赌博", "毒品", "违法", "颠覆", "分裂", "煽动", "造谣",
    ]

    def __init__(self, client: ArkClient, model: str = "Doubao-Seed-2.0-lite"):
        self.client = client
        self.model = model

    def check_by_keywords(self, text: str) -> tuple[bool, str, str]:
        """关键词规则检测"""
        text_lower = text.lower()
        for word in self.BAD_WORDS:
            if word in text_lower:
                return True, f"关键词:{word}", f"检测到敏感关键词: {word}"
        return False, "", ""

    def check_by_llm(self, text: str) -> Optional[ContentSafetyResult]:
        """LLM内容检测"""
        prompt = Prompts.content_safety_check(text)

        try:
            content = self.client.chat_completions(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )
        except Exception as e:
            logger.error(f"内容安全检测失败: {e}")
            return None

        if not content:
            return None

        try:
            data = json.loads(self._extract_json(content))
            return ContentSafetyResult(**data)
        except Exception as e:
            logger.error(f"解析安全检测结果失败: {e}")
            return None

    def check(self, text: str) -> ContentSafetyResult:
        """组合检测: 关键词 + LLM"""
        has_risk, risk_type, reason = self.check_by_keywords(text)
        if has_risk:
            return ContentSafetyResult(
                risk=True,
                type=risk_type,
                reason=reason,
            )

        result = self.check_by_llm(text)
        if result is None:
            return ContentSafetyResult(risk=False)

        return result

    def check_multiple(self, texts: List[str]) -> List[ContentSafetyResult]:
        """批量检测"""
        results: List[ContentSafetyResult] = []
        for text in texts:
            results.append(self.check(text))
        return results

    def has_risk(self, results: List[ContentSafetyResult]) -> bool:
        """是否存在风险"""
        return any(r.risk for r in results)

    def get_risk_summary(self, results: List[ContentSafetyResult]) -> str:
        """获取风险摘要"""
        risks = [f"{i+1}. {r.type}: {r.reason}" for i, r in enumerate(results) if r.risk]
        return "\n".join(risks)

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
