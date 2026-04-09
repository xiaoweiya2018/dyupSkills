"""
测试数据过滤模块
"""

import pytest
from src.filter import DataFilter
from src.models import TranscriptResult, TranscriptSegment


class TestDataFilter:
    """测试DataFilter"""

    def test_filter_short_text(self):
        """测试过滤短文本"""
        filter = DataFilter(min_text_length=50)
        transcript = TranscriptResult(
            text="短文本",
            segments=[],
        )
        result = filter.filter_video("test1", transcript)
        assert not result.kept
        assert "文本过短" in result.reason

    def test_keep_normal_text(self):
        """测试保留正常文本"""
        filter = DataFilter(min_text_length=50)
        long_text = "这是一段足够长的文本" * 10
        transcript = TranscriptResult(
            text=long_text,
            segments=[],
        )
        result = filter.filter_video("test1", transcript)
        assert result.kept
        assert "通过检查" in result.reason

    def test_filter_empty_text(self):
        """测试过滤空文本"""
        filter = DataFilter()
        transcript = TranscriptResult(
            text="",
            segments=[],
        )
        result = filter.filter_video("test1", transcript)
        assert not result.kept
        assert "转写结果为空" in result.reason

    def test_filter_all(self):
        """测试批量过滤"""
        filter = DataFilter(min_text_length=50)
        transcripts = [
            ("short", TranscriptResult(text="短", segments=[])),
            ("long1", TranscriptResult(text="足够长的文本" * 10, segments=[])),
            ("long2", TranscriptResult(text="足够长的文本" * 10, segments=[])),
            ("empty", TranscriptResult(text="", segments=[])),
        ]
        kept, results = filter.filter_all(transcripts)
        assert len(kept) == 2
        assert len(results) == 4
        kept_ids = [t[0] for t in kept]
        assert "long1" in kept_ids
        assert "long2" in kept_ids
        assert "short" not in kept_ids

    def test_get_kept_transcripts(self):
        """测试获取保留文本"""
        filter = DataFilter(min_text_length=1)
        transcripts = [
            ("id1", TranscriptResult(text="文本1", segments=[])),
            ("id2", TranscriptResult(text="文本2", segments=[])),
        ]
        kept, _ = filter.filter_all(transcripts)
        texts = filter.get_kept_transcripts(kept)
        assert len(texts) == 2
        assert "文本1" in texts
        assert "文本2" in texts

    def test_filter_by_length(self):
        """测试按总长度过滤"""
        texts = ["a" * 100, "b" * 100, "c" * 100]
        result = DataFilter.filter_by_length(texts, 250)
        assert len(result) == 2
        assert sum(len(t) for t in result) == 200

    def test_filter_by_length_single(self):
        """测试单条超过总长度"""
        texts = ["a" * 300, "b" * 100]
        result = DataFilter.filter_by_length(texts, 250)
        assert len(result) == 1
        assert len(result[0]) == 300
