"""
数据过滤模块 - 宁可少，也要纯
"""

from typing import List, Tuple
from loguru import logger
from .models import FilterResult, TranscriptResult


class DataFilter:
    """数据过滤器"""

    def __init__(
        self,
        min_text_length: int = 50,
        max_text_length: int = 5000,
        enable_speaker_check: bool = False,
    ):
        self.min_text_length = min_text_length
        self.max_text_length = max_text_length
        self.enable_speaker_check = enable_speaker_check

    def filter_video(self, video_id: str, transcript: TranscriptResult) -> FilterResult:
        """过滤单个视频"""
        text_length = len(transcript.text.strip())

        if not transcript.text.strip():
            return FilterResult(
                video_id=video_id,
                kept=False,
                reason="转写结果为空，可能是纯音乐视频",
                confidence=1.0,
            )

        if text_length < self.min_text_length:
            return FilterResult(
                video_id=video_id,
                kept=False,
                reason=f"文本过短 ({text_length} < {self.min_text_length})",
                confidence=1.0,
            )

        if text_length > self.max_text_length:
            logger.warning(f"文本过长 {video_id}: {text_length} chars")

        if self.enable_speaker_check and hasattr(transcript, "segments"):
            unique_speakers = self._count_unique_speakers(transcript)
            if unique_speakers > 1:
                return FilterResult(
                    video_id=video_id,
                    kept=False,
                    reason=f"检测到多个说话人 ({unique_speakers})",
                    confidence=0.9,
                )

        return FilterResult(
            video_id=video_id,
            kept=True,
            reason="通过检查",
            confidence=1.0,
        )

    def filter_all(
        self,
        transcripts: List[Tuple[str, TranscriptResult]],
    ) -> Tuple[List[Tuple[str, TranscriptResult]], List[FilterResult]]:
        """批量过滤"""
        kept: List[Tuple[str, TranscriptResult]] = []
        results: List[FilterResult] = []

        for video_id, transcript in transcripts:
            result = self.filter_video(video_id, transcript)
            results.append(result)
            if result.kept:
                kept.append((video_id, transcript))

        logger.info(f"过滤完成: {len(kept)}/{len(transcripts)} 保留")
        return kept, results

    def _count_unique_speakers(self, transcript: TranscriptResult) -> int:
        """统计唯一说话人数量"""
        speakers = set()
        for seg in transcript.segments:
            if hasattr(seg, "speaker") and seg.speaker:
                speakers.add(seg.speaker)
        return len(speakers)

    def get_kept_transcripts(self, kept: List[Tuple[str, TranscriptResult]]) -> List[str]:
        """获取保留的转写文本列表"""
        return [t[1].text for t in kept]

    @staticmethod
    def filter_by_length(texts: List[str], max_total: int) -> List[str]:
        """按总长度限制过滤"""
        result: List[str] = []
        total = 0
        for text in texts:
            if total + len(text) > max_total and total > 0:
                break
            result.append(text)
            total += len(text)
        return result
