"""
测试内容安全检测模块
"""

import pytest
from unittest.mock import Mock, patch
from src.safety import ContentSafetyChecker
from src.models import ContentSafetyResult
from src.volc_ark import ArkClient


class TestContentSafetyChecker:
    """测试ContentSafetyChecker"""

    def test_check_by_keywords_found(self):
        """测试关键词检测命中"""
        mock_client = Mock(spec=ArkClient)
        checker = ContentSafetyChecker(mock_client)
        has_risk, risk_type, reason = checker.check_by_keywords("这里有暴力内容")
        assert has_risk
        assert "暴力" in risk_type

    def test_check_by_keywords_not_found(self):
        """测试关键词检测未命中"""
        mock_client = Mock(spec=ArkClient)
        checker = ContentSafetyChecker(mock_client)
        has_risk, risk_type, reason = checker.check_by_keywords("这是正常内容")
        assert not has_risk

    def test_has_risk(self):
        """测试是否存在风险"""
        mock_client = Mock(spec=ArkClient)
        checker = ContentSafetyChecker(mock_client)
        results = [
            ContentSafetyResult(risk=False),
            ContentSafetyResult(risk=False),
        ]
        assert not checker.has_risk(results)

        results = [
            ContentSafetyResult(risk=False),
            ContentSafetyResult(risk=True, type="test", reason="test"),
        ]
        assert checker.has_risk(results)

    def test_get_risk_summary(self):
        """测试风险摘要"""
        mock_client = Mock(spec=ArkClient)
        checker = ContentSafetyChecker(mock_client)
        results = [
            ContentSafetyResult(risk=False),
            ContentSafetyResult(risk=True, type="暴力", reason="包含暴力内容"),
        ]
        summary = checker.get_risk_summary(results)
        assert "暴力" in summary
        assert "包含暴力内容" in summary
