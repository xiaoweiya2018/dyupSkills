"""
语音转写模块 - 火山大模型录音文件识别（AUC）
"""

import os
import json
from typing import Optional
from loguru import logger
from .models import TranscriptResult, TranscriptSegment
from .volc_auc import VolcAUCClient, extract_text_and_segments, safe_json_dumps


class DoubaoTranscriber:
    """Doubao语音转写器"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openspeech.bytedance.com",
        resource_id: str = "volc.seedasr.auc",
        model_name: str = "bigmodel",
        audio_url_prefix: str = "",
        audio_format: str = "mp3",
        audio_codec: str = "raw",
        audio_rate: int = 16000,
        audio_bits: int = 16,
        audio_channel: int = 1,
    ):
        self.audio_url_prefix = (audio_url_prefix or "").strip().rstrip("/")
        self.client = VolcAUCClient(
            api_key=api_key,
            base_url=base_url,
            resource_id=resource_id,
            model_name=model_name,
            audio_format=audio_format,
            audio_codec=audio_codec,
            audio_rate=audio_rate,
            audio_bits=audio_bits,
            audio_channel=audio_channel,
        )

    def transcribe(self, audio_path: str) -> Optional[TranscriptResult]:
        """转写单个音频文件"""
        if not os.path.exists(audio_path):
            logger.error(f"音频文件不存在: {audio_path}")
            return None

        file_size = os.path.getsize(audio_path)
        if file_size == 0:
            logger.error(f"音频文件为空: {audio_path}")
            return None

        logger.info(f"开始转写: {audio_path} ({file_size} bytes)")

        try:
            if self.audio_url_prefix:
                audio_url = f"{self.audio_url_prefix}/{os.path.basename(audio_path)}"
                payload = self.client.recognize(audio_url=audio_url)
            else:
                payload = self.client.recognize(audio_path=audio_path)
        except Exception as e:
            logger.error(f"AUC转写失败: {e}")
            return None

        segments: list[TranscriptSegment] = []
        text, raw_segments = extract_text_and_segments(payload)
        if isinstance(raw_segments, list):
            for seg in raw_segments:
                try:
                    segments.append(
                        TranscriptSegment(
                            start=float(seg.get("start", 0.0) or 0.0),
                            end=float(seg.get("end", 0.0) or 0.0),
                            text=str(seg.get("text", "") or "").strip(),
                        )
                    )
                except Exception:
                    continue

        result = TranscriptResult(
            text=text,
            segments=segments,
            language=None,
        )

        logger.info(f"转写完成，文本长度: {len(result.text)}")
        if not result.text:
            logger.warning(f"AUC返回为空: {safe_json_dumps(payload)[:500]}")
        return result

    def save_transcript(self, transcript: TranscriptResult, output_path: str) -> bool:
        """保存转写结果"""
        try:
            data = {
                "text": transcript.text,
                "segments": [
                    {"start": s.start, "end": s.end, "text": s.text}
                    for s in transcript.segments
                ],
                "language": transcript.language,
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存转写结果失败: {e}")
            return False

    def load_transcript(self, input_path: str) -> Optional[TranscriptResult]:
        """加载转写结果"""
        if not os.path.exists(input_path):
            return None

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            segments = [
                TranscriptSegment(
                    start=s["start"],
                    end=s["end"],
                    text=s["text"],
                )
                for s in data.get("segments", [])
            ]

            return TranscriptResult(
                text=data.get("text", ""),
                segments=segments,
                language=data.get("language"),
            )
        except Exception as e:
            logger.error(f"加载转写结果失败: {e}")
            return None
