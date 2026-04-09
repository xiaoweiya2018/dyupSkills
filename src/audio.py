"""
音频处理模块 - 基于ffmpeg
"""

import os
import subprocess
from typing import Optional
from loguru import logger
from .models import VideoDownload


class AudioExtractor:
    """音频提取器"""

    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def extract_audio(self, video_download: VideoDownload) -> Optional[str]:
        """从视频中提取音频"""
        if not video_download.downloaded:
            logger.warning(f"视频未下载，跳过音频提取: {video_download.video_info.aweme_id}")
            return None

        video_path = video_download.file_path
        author = video_download.video_info.author.replace(" ", "_")
        video_id = video_download.video_info.aweme_id
        audio_path = os.path.join(self.cache_dir, author, f"{video_id}.mp3")

        os.makedirs(os.path.dirname(audio_path), exist_ok=True)

        if os.path.exists(audio_path):
            logger.info(f"音频已存在，跳过提取: {audio_path}")
            video_download.audio_path = audio_path
            return audio_path

        cmd = [
            "ffmpeg",
            "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "libmp3lame",
            "-q:a", "2",
            audio_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode != 0:
                logger.error(f"音频提取失败: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"音频提取异常: {e}")
            return None

        if not os.path.exists(audio_path):
            logger.error(f"音频提取完成但文件不存在: {audio_path}")
            return None

        file_size = os.path.getsize(audio_path)
        if file_size < 1000:
            logger.warning(f"提取的音频文件过小: {file_size} bytes")
            os.remove(audio_path)
            return None

        logger.info(f"音频提取完成: {audio_path} ({file_size} bytes)")
        video_download.audio_path = audio_path
        return audio_path

    def extract_all(self, videos: list[VideoDownload]) -> list[str]:
        """批量提取音频"""
        results: list[str] = []
        for video in videos:
            audio_path = self.extract_audio(video)
            if audio_path:
                results.append(audio_path)
        return results

    def get_audio_duration(self, audio_path: str) -> Optional[float]:
        """获取音频时长"""
        if not os.path.exists(audio_path):
            return None

        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
        except Exception:
            pass

        return None
