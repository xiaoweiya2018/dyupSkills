"""
视频抓取模块 - 基于yt-dlp
"""

import os
import asyncio
import json
import subprocess
import time
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from loguru import logger
from .models import VideoInfo, VideoDownload

import yt_dlp


class VideoDownloader:
    """抖音视频下载器"""

    def __init__(
        self,
        cache_dir: str,
        max_videos: int = 10,
        cookie_file: Optional[str] = None,
        cookies_from_browser: Optional[str] = None,
        disable_proxy: bool = True,
    ):
        self.cache_dir = cache_dir
        self.max_videos = max_videos
        self.cookie_file = cookie_file
        self.cookies_from_browser = cookies_from_browser
        self.disable_proxy = disable_proxy
        os.makedirs(cache_dir, exist_ok=True)

    def _cookiefile_for_ytdlp(self) -> Optional[str]:
        if (self.cookies_from_browser or "").strip():
            return None

        cookie_file = (self.cookie_file or "").strip()
        if not cookie_file:
            return None
        if not os.path.exists(cookie_file):
            logger.warning(f"cookie文件不存在: {cookie_file}")
            return None

        if not cookie_file.lower().endswith(".json"):
            return cookie_file

        out_dir = os.path.join(self.cache_dir, "_cookies")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "douyin_cookies.txt")

        try:
            with open(cookie_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.warning("cookie JSON格式不符合预期：需要是数组")
                return None

            lines: list[str] = []
            lines.append("# Netscape HTTP Cookie File")
            lines.append("# This file was generated automatically from JSON cookies.")
            lines.append("")

            now = int(time.time())
            written = 0
            for c in data:
                if not isinstance(c, dict):
                    continue
                name = str(c.get("name", "")).strip()
                value = str(c.get("value", "")).strip().replace("\t", " ").replace("\n", " ")
                domain = str(c.get("domain", "")).strip()
                path = str(c.get("path", "/")).strip() or "/"
                if not name or not domain:
                    continue

                secure = "TRUE" if bool(c.get("secure", False)) else "FALSE"
                include_subdomains = "TRUE" if domain.startswith(".") else "FALSE"

                exp = c.get("expirationDate", c.get("expires", c.get("expiry", 0)))
                try:
                    exp_int = int(float(exp)) if exp else 0
                except Exception:
                    exp_int = 0
                if exp_int == 0:
                    exp_int = now + 31536000
                elif exp_int < now - 60:
                    continue

                lines.append(f"{domain}\t{include_subdomains}\t{path}\t{secure}\t{exp_int}\t{name}\t{value}")
                written += 1

            if len(lines) <= 3:
                logger.warning("cookie JSON转换后为空：可能不是浏览器cookie导出文件，或缺少 douyin.com 域条目")
                return None

            with open(out_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(f"已将cookie JSON转换为Netscape格式: {out_path} (cookies={written})")
            return out_path
        except Exception as e:
            logger.warning(f"cookie JSON转换失败: {e}")
            return None

    def _apply_common_ydl_opts(self, ydl_opts: dict) -> dict:
        if self.disable_proxy:
            ydl_opts["proxy"] = ""
        browser = (self.cookies_from_browser or "").strip()
        if browser:
            ydl_opts["cookiesfrombrowser"] = (browser,)
        return ydl_opts

    def extract_user_id(self, url: str) -> str:
        """从URL中提取用户ID"""
        if "douyin.com" not in url:
            return url.strip()

        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if path.startswith("user/"):
            return path.split("/")[1]

        return url.strip()

    async def get_user_videos(self, url_or_id: str) -> List[VideoInfo]:
        """获取用户最近视频列表"""
        logger.info(f"开始获取用户视频: {url_or_id}")

        if "douyin.com" in url_or_id:
            url = url_or_id
        else:
            url = f"https://www.douyin.com/user/{url_or_id}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "playlistend": self.max_videos,
            "ignoreerrors": True,
            "no_check_certificate": True,
            "extractor_args": {
                "douyin": {
                    "player_encoding": ["UTF-8"],
                }
            }
        }
        ydl_opts = self._apply_common_ydl_opts(ydl_opts)

        cookiefile = self._cookiefile_for_ytdlp()
        if cookiefile:
            ydl_opts["cookiefile"] = cookiefile
            logger.info(f"使用cookie文件: {cookiefile}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
            except Exception as e:
                logger.error(f"获取视频列表失败: {e}")
                return []

        if not info or "entries" not in info:
            logger.warning("未找到视频列表")
            return []

        videos: List[VideoInfo] = []
        entries = [e for e in info["entries"] if e is not None][:self.max_videos]

        for entry in entries:
            try:
                video = VideoInfo(
                    aweme_id=entry.get("id", ""),
                    title=entry.get("title", ""),
                    desc=entry.get("description", ""),
                    video_url=entry.get("url", entry.get("webpage_url", "")),
                    duration=entry.get("duration", 0),
                    publish_time=None,
                    author=info.get("uploader", "unknown"),
                )
                videos.append(video)
            except Exception as e:
                logger.warning(f"解析视频信息失败: {e}")
                continue

        logger.info(f"获取到 {len(videos)} 个视频")
        return videos

    async def download_video(self, video: VideoInfo) -> Optional[VideoDownload]:
        """下载单个视频"""
        video_dir = os.path.join(self.cache_dir, video.author.replace(" ", "_"))
        os.makedirs(video_dir, exist_ok=True)

        output_path = os.path.join(video_dir, f"{video.aweme_id}.mp4")

        if os.path.exists(output_path):
            logger.info(f"视频已存在，跳过下载: {output_path}")
            return VideoDownload(
                video_info=video,
                file_path=output_path,
                downloaded=True,
            )

        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": True,
            "no_check_certificate": True,
        }
        ydl_opts = self._apply_common_ydl_opts(ydl_opts)

        cookiefile = self._cookiefile_for_ytdlp()
        if cookiefile:
            ydl_opts["cookiefile"] = cookiefile

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                await asyncio.to_thread(ydl.download, [video.video_url])
        except Exception as e:
            logger.error(f"下载视频失败 {video.aweme_id}: {e}")
            return None

        if not os.path.exists(output_path):
            logger.error(f"下载完成但文件不存在: {output_path}")
            return None

        logger.info(f"下载完成: {output_path}")
        return VideoDownload(
            video_info=video,
            file_path=output_path,
            downloaded=True,
        )

    async def download_all(self, videos: List[VideoInfo]) -> List[VideoDownload]:
        """批量下载视频"""
        results: List[VideoDownload] = []

        for video in videos:
            result = await self.download_video(video)
            if result:
                results.append(result)

        return results

    def check_ffmpeg(self) -> Tuple[bool, str]:
        """检查ffmpeg是否可用"""
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            if result.returncode == 0:
                return True, "ffmpeg 可用"
            return False, "ffmpeg 不可用"
        except FileNotFoundError:
            return False, "未找到ffmpeg，请先安装ffmpeg"
        except Exception as e:
            return False, str(e)

    async def get_videos_from_file(self, file_path: str, author: str = "unknown") -> List[VideoInfo]:
        """从文本文件读取视频链接列表

        文件格式：每行一个视频URL
        """
        logger.info(f"从文件读取视频列表: {file_path}")

        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return []

        videos: List[VideoInfo] = []

        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        for i, url in enumerate(lines[:self.max_videos]):
            try:
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "ignoreerrors": True,
                    "no_check_certificate": True,
                }
                ydl_opts = self._apply_common_ydl_opts(ydl_opts)

                cookiefile = self._cookiefile_for_ytdlp()
                if cookiefile:
                    ydl_opts["cookiefile"] = cookiefile

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = await asyncio.to_thread(ydl.extract_info, url, download=False)

                if not info:
                    logger.warning(f"获取视频信息失败: {url}")
                    continue

                video = VideoInfo(
                    aweme_id=info.get("id", f"video_{i}"),
                    title=info.get("title", ""),
                    desc=info.get("description", ""),
                    video_url=url,
                    duration=info.get("duration", 0),
                    publish_time=None,
                    author=author,
                )
                videos.append(video)
                logger.info(f"添加视频: {video.title[:50]}...")

            except Exception as e:
                logger.warning(f"解析视频失败 {url}: {e}")
                continue

        logger.info(f"从文件读取到 {len(videos)} 个视频")
        return videos
