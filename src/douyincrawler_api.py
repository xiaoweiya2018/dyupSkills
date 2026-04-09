import asyncio
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from loguru import logger

from .models import VideoDownload, VideoInfo


class DouyinCrawlerDownloader:
    def __init__(
        self,
        cache_dir: str,
        max_videos: int,
        api_base_url: str,
        task_type: str = "post",
        poll_interval_seconds: float = 1.0,
        request_timeout_seconds: int = 60,
        task_timeout_seconds: int = 300,
    ):
        self.cache_dir = cache_dir
        self.max_videos = max_videos
        self.api_base_url = api_base_url.rstrip("/")
        self.task_type = task_type
        self.poll_interval_seconds = poll_interval_seconds
        self.request_timeout_seconds = request_timeout_seconds
        self.task_timeout_seconds = task_timeout_seconds
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

        task_id = await self._start_task(self.task_type, target, self.max_videos)
        await self._wait_task(task_id)
        items = await self._get_task_results(task_id)
        videos = self._items_to_videos(items)
        logger.info(f"DouyinCrawler 返回 {len(videos)} 个视频")
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
                task_id = await self._start_task("aweme", url, 1)
                await self._wait_task(task_id)
                items = await self._get_task_results(task_id)
                parsed = self._items_to_videos(items)
                if parsed:
                    videos.append(parsed[0])
            except Exception as e:
                logger.warning(f"解析视频失败 {url}: {e}")
                continue

        if author != "unknown":
            for i, v in enumerate(videos):
                if v.author == "unknown":
                    videos[i] = v.model_copy(update={"author": author})

        logger.info(f"从文件读取到 {len(videos)} 个视频")
        return videos

    async def download_video(self, video: VideoInfo) -> Optional[VideoDownload]:
        author_dir = os.path.join(self.cache_dir, video.author.replace(" ", "_"))
        os.makedirs(author_dir, exist_ok=True)
        output_path = os.path.join(author_dir, f"{video.aweme_id}.mp4")

        if os.path.exists(output_path):
            logger.info(f"视频已存在，跳过下载: {output_path}")
            return VideoDownload(video_info=video, file_path=output_path, downloaded=True)

        url = (video.video_url or "").strip()
        if not url:
            logger.error(f"缺少下载地址: {video.aweme_id}")
            return None

        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.douyin.com/",
        }
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                async with session.get(url, allow_redirects=True) as resp:
                    if resp.status >= 400:
                        logger.error(f"下载失败 {video.aweme_id}: HTTP {resp.status}")
                        return None
                    with open(output_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 256):
                            if chunk:
                                f.write(chunk)
        except Exception as e:
            logger.error(f"下载失败 {video.aweme_id}: {e}")
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

    async def _start_task(self, task_type: str, target: str, limit: int) -> str:
        url = f"{self.api_base_url}/api/task/start"
        payload = {"type": task_type, "target": target, "limit": int(limit)}
        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                data = await self._read_json(resp)
                if resp.status >= 400:
                    raise RuntimeError(f"启动任务失败: HTTP {resp.status}: {data}")
                task_id = str(data.get("task_id", "")).strip()
                if not task_id:
                    raise RuntimeError(f"启动任务失败: 返回缺少 task_id: {data}")
                return task_id

    async def _wait_task(self, task_id: str) -> None:
        url = f"{self.api_base_url}/api/task/status"
        deadline = asyncio.get_event_loop().time() + float(self.task_timeout_seconds)
        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            while True:
                async with session.get(url, params={"task_id": task_id}) as resp:
                    data = await self._read_json(resp)
                    if resp.status >= 400:
                        raise RuntimeError(f"获取任务状态失败: HTTP {resp.status}: {data}")

                if isinstance(data, list) and data:
                    status = str(data[0].get("status", "")).strip()
                    err = data[0].get("error")
                else:
                    status = ""
                    err = None

                if status == "completed":
                    return
                if status == "error":
                    raise RuntimeError(f"采集任务失败: {err or 'unknown error'}")

                if asyncio.get_event_loop().time() > deadline:
                    raise TimeoutError("采集任务等待超时")

                await asyncio.sleep(self.poll_interval_seconds)

    async def _get_task_results(self, task_id: str) -> List[Dict[str, Any]]:
        url = f"{self.api_base_url}/api/task/results/{task_id}"
        timeout = aiohttp.ClientTimeout(total=self.request_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                data = await self._read_json(resp)
                if resp.status >= 400:
                    raise RuntimeError(f"获取任务结果失败: HTTP {resp.status}: {data}")
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict)]
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
            try:
                videos.append(
                    VideoInfo(
                        aweme_id=str(item.get("id", "")).strip(),
                        title="",
                        desc=str(item.get("desc", "") or ""),
                        video_url=download_addr.strip(),
                        duration=duration_f,
                        publish_time=None,
                        author=str(item.get("author_nickname", "") or "unknown"),
                    )
                )
            except Exception:
                continue
        return videos

    async def _read_json(self, resp: aiohttp.ClientResponse) -> Any:
        try:
            return await resp.json(content_type=None)
        except Exception:
            try:
                text = await resp.text()
            except Exception:
                text = ""
            return {"_raw": text}

