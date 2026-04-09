import asyncio
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from loguru import logger

from .douyincrawler import Douyin
from .douyincrawler.lib.cookies import CookieManager
from .models import VideoDownload, VideoInfo


class DouyinCrawlerLocalDownloader:
    def __init__(
        self,
        cache_dir: str,
        max_videos: int,
        cookie: str,
        user_agent: str = "",
        task_type: str = "post",
        request_timeout_seconds: int = 60,
    ):
        self.cache_dir = cache_dir
        self.max_videos = max_videos
        self.cookie = cookie
        self.user_agent = user_agent or ""
        self.task_type = task_type or "post"
        self.request_timeout_seconds = request_timeout_seconds
        os.makedirs(cache_dir, exist_ok=True)

    def extract_user_id(self, url: str) -> str:
        if "douyin.com" not in url:
            return url.strip()
        try:
            parts = url.split("douyin.com", 1)[1]
            parts = parts.split("?", 1)[0]
            parts = parts.strip("/")
            if parts.startswith("user/"):
                return parts.split("/", 1)[1].strip()
        except Exception:
            return url.strip()
        return url.strip()

    async def get_user_videos(self, url_or_id: str) -> List[VideoInfo]:
        if "douyin.com" in url_or_id:
            target = url_or_id
        else:
            target = f"https://www.douyin.com/user/{url_or_id}"

        items = await asyncio.to_thread(self._crawl, target, self.task_type, self.max_videos)
        videos = self._items_to_videos(items)
        logger.info(f"DouyinCrawler 采集到 {len(videos)} 个视频")
        return videos[: self.max_videos]

    async def get_videos_from_file(self, file_path: str, author: str = "unknown") -> List[VideoInfo]:
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        videos: List[VideoInfo] = []
        for url in lines[: self.max_videos]:
            try:
                items = await asyncio.to_thread(self._crawl, url, "aweme", 1)
                parsed = self._items_to_videos(items)
                if parsed:
                    v = parsed[0]
                    if author != "unknown" and (v.author or "unknown") == "unknown":
                        v = v.model_copy(update={"author": author})
                    videos.append(v)
            except Exception as e:
                logger.warning(f"解析视频失败 {url}: {e}")
                continue

        logger.info(f"从文件读取到 {len(videos)} 个视频")
        return videos

    async def download_video(self, video: VideoInfo) -> Optional[VideoDownload]:
        author_dir = os.path.join(self.cache_dir, video.author.replace(" ", "_") or "unknown")
        os.makedirs(author_dir, exist_ok=True)
        output_path = os.path.join(author_dir, f"{video.aweme_id}.mp4")

        if os.path.exists(output_path):
            logger.info(f"视频已存在，跳过下载: {output_path}")
            return VideoDownload(video_info=video, file_path=output_path, downloaded=True)

        url = (video.video_url or "").strip()
        if not url or not url.startswith("http"):
            logger.error(f"缺少下载地址: {video.aweme_id}")
            return None

        headers = {"User-Agent": self.user_agent or "Mozilla/5.0", "Referer": "https://www.douyin.com/"}
        last_err: Optional[Exception] = None
        for attempt in range(3):
            timeout = aiohttp.ClientTimeout(
                total=self.request_timeout_seconds,
                connect=10,
                sock_read=30,
            )
            try:
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.get(url, allow_redirects=True) as resp:
                        if resp.status >= 400:
                            logger.error(
                                f"下载失败 {video.aweme_id}: HTTP {resp.status} url={resp.url}"
                            )
                            return None
                        with open(output_path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(1024 * 256):
                                if chunk:
                                    f.write(chunk)
                last_err = None
                break
            except Exception as e:
                last_err = e
                try:
                    if os.path.exists(output_path):
                        os.remove(output_path)
                except Exception:
                    pass
                if attempt < 2:
                    await asyncio.sleep(1.0 * (attempt + 1))
                continue

        if last_err is not None:
            logger.error(f"下载失败 {video.aweme_id}: {repr(last_err)}")
            return None

        if not os.path.exists(output_path) or os.path.getsize(output_path) <= 0:
            logger.error(f"下载完成但文件无效: {output_path}")
            return None

        logger.info(f"下载完成: {output_path}")
        return VideoDownload(video_info=video, file_path=output_path, downloaded=True)

    async def download_all(self, videos: List[VideoInfo]) -> List[VideoDownload]:
        results: List[VideoDownload] = []
        for v in videos:
            r = await self.download_video(v)
            if r:
                results.append(r)
        return results

    def check_ffmpeg(self) -> Tuple[bool, str]:
        try:
            result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
            if result.returncode == 0:
                return True, "ffmpeg 可用"
            return False, "ffmpeg 不可用"
        except FileNotFoundError:
            return False, "未找到ffmpeg，请先安装ffmpeg"
        except Exception as e:
            return False, str(e)

    def _crawl(self, target: str, task_type: str, limit: int) -> List[Dict[str, Any]]:
        if not CookieManager.validate_cookie(self.cookie or ""):
            raise Exception("抖音Cookie无效或为空：请在WebUI侧边栏粘贴浏览器Cookie完整内容（至少包含 sessionid 或 ttwid）")
        douyin = Douyin(
            target=target,
            limit=int(limit) if limit and limit > 0 else 0,
            type=task_type,
            down_path=os.path.join(self.cache_dir, "_douyincrawler"),
            cookie=self.cookie or "",
            user_agent=self.user_agent or "",
        )
        douyin.run()
        if isinstance(douyin.results, list):
            return [x for x in douyin.results if isinstance(x, dict)]
        return []

    def _items_to_videos(self, items: List[Dict[str, Any]]) -> List[VideoInfo]:
        videos: List[VideoInfo] = []
        for item in items:
            aweme_type = item.get("type", 4)
            if aweme_type == 68:
                continue
            download_addr = item.get("download_addr")
            if not isinstance(download_addr, str) or not download_addr.strip():
                continue

            duration = item.get("duration", 0) or 0
            try:
                duration_f = float(duration)
                if duration_f > 1000:
                    duration_f = duration_f / 1000.0
            except Exception:
                duration_f = 0.0

            aweme_id = str(item.get("id", "")).strip()
            if not aweme_id:
                continue

            videos.append(
                VideoInfo(
                    aweme_id=aweme_id,
                    title="",
                    desc=str(item.get("desc", "") or ""),
                    video_url=download_addr.strip(),
                    duration=duration_f,
                    publish_time=None,
                    author=str(item.get("author_nickname", "") or "unknown"),
                )
            )
        return videos

