"""
主引擎 - 整合完整生成流程
"""

import os
import asyncio
from typing import Optional, List, Tuple, Callable
from datetime import datetime
from loguru import logger
from .models import (
    Config,
    VideoInfo,
    VideoDownload,
    TranscriptResult,
    GenerationResult,
    GenerationProgress,
    BloggerProfile,
    StyleRule,
    Skill,
    SkillScore,
    FilterResult,
)
from .douyincrawler_local import DouyinCrawlerLocalDownloader
from .audio import AudioExtractor
from .transcriber import DoubaoTranscriber
from .filter import DataFilter
from .safety import ContentSafetyChecker
from .ai_generator import AIGenerator
from .exporter import Exporter
from .storage import Storage
from .volc_ark import ArkClient


class GenerationEngine:
    """生成引擎"""

    def __init__(self, config: Config):
        self.config = config
        self._init_clients()
        self._init_modules()
        logger.info("生成引擎初始化完成")

    def _init_clients(self):
        self.client = ArkClient(
            api_key=self.config.volc_ark_api_key,
            base_url=self.config.volc_ark_base_url,
        )

    def _init_modules(self):
        """初始化各个模块"""
        cache_dir = os.path.join(self.config.cache_dir, "videos")
        self.downloader = DouyinCrawlerLocalDownloader(
            cache_dir=cache_dir,
            max_videos=self.config.max_videos,
            cookie=getattr(self.config, "douyincrawler_cookie", "") or "",
            user_agent=getattr(self.config, "douyincrawler_user_agent", "") or "",
            task_type=getattr(self.config, "douyincrawler_task_type", "post") or "post",
        )
        self.audio_extractor = AudioExtractor(
            cache_dir=os.path.join(self.config.cache_dir, "audio"),
        )
        self.transcriber = DoubaoTranscriber(
            api_key=self.config.volc_auc_api_key,
            base_url=self.config.volc_auc_base_url,
            resource_id=self.config.volc_auc_resource_id,
            model_name=self.config.volc_auc_model_name,
            audio_url_prefix=self.config.volc_auc_audio_url_prefix,
            audio_format=self.config.volc_auc_audio_format,
            audio_codec=self.config.volc_auc_audio_codec,
            audio_rate=self.config.volc_auc_audio_rate,
            audio_bits=self.config.volc_auc_audio_bits,
            audio_channel=self.config.volc_auc_audio_channel,
        )
        self.data_filter = DataFilter()
        self.safety_checker = ContentSafetyChecker(self.client, model=self.config.volc_chat_model)
        self.ai_generator = AIGenerator(self.client, model=self.config.volc_chat_model)
        self.exporter = Exporter(self.config.output_dir)
        self.storage = Storage(self.config.output_dir)

    def _unique_skill_name(self, blogger_name: str) -> str:
        base = f"博主-{(blogger_name or '').strip() or 'unknown'}"
        try:
            history = self.storage.load_history()
            names: set[str] = set()
            for h in history:
                if h.result_data and isinstance(h.result_data, dict):
                    skill = h.result_data.get("skill") or {}
                    if isinstance(skill, dict):
                        n = (skill.get("name") or "").strip()
                        if n:
                            names.add(n)
            if base not in names:
                return base
            i = 1
            while True:
                candidate = f"{base}{i}"
                if candidate not in names:
                    return candidate
                i += 1
        except Exception:
            return base

    async def generate(
        self,
        input_url: str,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> Optional[GenerationResult]:
        """完整生成流程"""
        start_time = datetime.now()
        logger.info(f"开始生成: {input_url}")

        blogger_id = self.downloader.extract_user_id(input_url)
        version = self.storage.get_next_version(blogger_id)

        def update_progress(
            stage: str,
            current: int,
            total: int,
            message: str,
            sub_current: int = 0,
            sub_total: int = 0,
        ):
            progress = GenerationProgress(
                stage=stage,
                current=current,
                total=total,
                sub_current=sub_current,
                sub_total=sub_total,
                message=message,
            )
            if progress_callback:
                progress_callback(progress)

        try:
            overall_current = 0
            overall_total = 1
            update_progress("初始化", overall_current, overall_total, "正在初始化...")
            update_progress("获取视频列表", overall_current, overall_total, "正在获取视频列表...", 0, 1)

            if input_url.strip().endswith(".txt") and os.path.exists(input_url):
                videos = await self.downloader.get_videos_from_file(input_url, blogger_id)
                blogger_name = os.path.basename(input_url).replace(".txt", "")
            else:
                videos = await self.downloader.get_user_videos(input_url)
                blogger_name = videos[0].author if videos else blogger_id

            if not videos:
                logger.error("未获取到任何视频")
                return None
            logger.info(f"获取到 {len(videos)} 个视频")

            overall_total = 1 + len(videos) + len(videos) + len(videos) + 1 + 1 + 4 + 1
            overall_current = 1
            update_progress("获取视频列表", overall_current, overall_total, f"获取到 {len(videos)} 个视频", 1, 1)

            update_progress("下载视频", overall_current, overall_total, "准备下载视频...", 0, len(videos))
            downloaded_all: List[Optional[VideoDownload]] = []
            for i, v in enumerate(videos):
                update_progress(
                    "下载视频",
                    overall_current,
                    overall_total,
                    f"正在下载: {v.aweme_id}",
                    i,
                    len(videos),
                )
                r = await self.downloader.download_video(v)
                downloaded_all.append(r)
                overall_current += 1
                update_progress(
                    "下载视频",
                    overall_current,
                    overall_total,
                    f"下载完成: {v.aweme_id}" if r else f"下载失败/跳过: {v.aweme_id}",
                    i + 1,
                    len(videos),
                )

            downloaded = [x for x in downloaded_all if x]
            if not downloaded:
                logger.error("下载失败，没有可用视频")
                return None
            logger.info(f"下载完成: {len(downloaded)}/{len(videos)}")

            update_progress("提取音频", overall_current, overall_total, "准备提取音频...", 0, len(videos))
            for i, item in enumerate(downloaded_all):
                if not item:
                    overall_current += 1
                    update_progress(
                        "提取音频",
                        overall_current,
                        overall_total,
                        f"跳过：对应视频未下载成功 ({i+1}/{len(videos)})",
                        i + 1,
                        len(videos),
                    )
                    continue
                update_progress(
                    "提取音频",
                    overall_current,
                    overall_total,
                    f"正在提取: {item.video_info.aweme_id}",
                    i,
                    len(videos),
                )
                self.audio_extractor.extract_audio(item)
                overall_current += 1
                update_progress(
                    "提取音频",
                    overall_current,
                    overall_total,
                    f"提取完成: {item.video_info.aweme_id}",
                    i + 1,
                    len(videos),
                )

            audio_list = [v.audio_path for v in downloaded if v.audio_path]
            logger.info(f"音频提取完成: {len(audio_list)}/{len(downloaded)}")

            update_progress("语音转写", overall_current, overall_total, "准备语音转写...", 0, len(videos))
            transcripts: List[Tuple[str, TranscriptResult]] = []
            for i, item in enumerate(downloaded_all):
                if not item or not item.audio_path:
                    overall_current += 1
                    update_progress(
                        "语音转写",
                        overall_current,
                        overall_total,
                        f"跳过：缺少音频 ({i+1}/{len(videos)})",
                        i + 1,
                        len(videos),
                    )
                    continue
                audio_path = item.audio_path
                update_progress(
                    "语音转写",
                    overall_current,
                    overall_total,
                    f"正在转写: {item.video_info.aweme_id}",
                    i,
                    len(videos),
                )
                cache_dir = os.path.dirname(audio_path)
                transcript_path = os.path.join(cache_dir, f"{item.video_info.aweme_id}.json")

                cached = self.transcriber.load_transcript(transcript_path)
                if cached:
                    transcript = cached
                    update_progress(
                        "语音转写",
                        overall_current,
                        overall_total,
                        f"命中缓存: {item.video_info.aweme_id}",
                        i,
                        len(videos),
                    )
                else:
                    transcript = self.transcriber.transcribe(audio_path)
                    if transcript:
                        self.transcriber.save_transcript(transcript, transcript_path)

                if transcript:
                    transcripts.append((item.video_info.aweme_id, transcript))
                    msg = f"转写完成: {item.video_info.aweme_id}"
                else:
                    msg = f"转写失败/空结果: {item.video_info.aweme_id}"
                overall_current += 1
                update_progress(
                    "语音转写",
                    overall_current,
                    overall_total,
                    msg,
                    i + 1,
                    len(videos),
                )

            logger.info(f"转写完成: {len(transcripts)}/{len(audio_list)}")

            overall_current += 1
            update_progress("数据过滤", overall_current, overall_total, "正在过滤不合格视频...", 0, 1)
            kept, filter_results = self.data_filter.filter_all(transcripts)
            if len(kept) < self.config.min_videos_required:
                logger.error(f"合格视频不足: {len(kept)} < {self.config.min_videos_required}")
                return None
            kept_texts = self.data_filter.get_kept_transcripts(kept)
            logger.info(f"过滤完成: {len(kept)} 保留")

            overall_current += 1
            update_progress("内容安全检测", overall_current, overall_total, "正在进行内容安全检测...", 0, 1)
            safety_results = self.safety_checker.check_multiple(kept_texts)
            if self.safety_checker.has_risk(safety_results):
                risk_summary = self.safety_checker.get_risk_summary(safety_results)
                logger.warning(f"检测到内容风险:\n{risk_summary}")

            overall_current += 1
            update_progress("AI分析生成", overall_current, overall_total, "正在生成博主画像...", 1, 4)
            profile = self.ai_generator.generate_blogger_profile(
                kept_texts,
                self.config.max_total_chars,
            )
            if not profile:
                return None

            overall_current += 1
            update_progress("AI分析生成", overall_current, overall_total, "正在生成风格规则...", 2, 4)
            style_rules = self.ai_generator.generate_style_rules(
                kept_texts,
                profile,
                self.config.max_total_chars,
            )
            if not style_rules:
                return None

            overall_current += 1
            update_progress("AI分析生成", overall_current, overall_total, "正在生成Skill...", 3, 4)
            skill = self.ai_generator.generate_skill(
                profile,
                style_rules,
                kept_texts,
                self.config.max_total_chars,
            )
            if not skill:
                return None

            try:
                unique_name = self._unique_skill_name(blogger_name)
                skill = skill.model_copy(update={"name": unique_name})
            except Exception:
                pass

            overall_current += 1
            update_progress("AI分析生成", overall_current, overall_total, "正在评分...", 4, 4)
            score = self.ai_generator.evaluate_skill(skill)
            if not score:
                return None

            result = GenerationResult(
                blogger_id=blogger_id,
                blogger_name=blogger_name,
                input_url=input_url,
                videos_processed=len(videos),
                videos_kept=len(kept),
                profile=profile,
                style_rules=style_rules,
                skill=skill,
                score=score,
                version=version,
            )

            overall_current += 1
            update_progress("导出", overall_current, overall_total, "正在导出结果...", 0, 1)
            export_paths = self.exporter.export_all(result)
            self.storage.add_to_history(result, export_paths["skill_md"])

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"生成完成! 耗时 {elapsed:.1f}s, 总体评分: {score.overall:.2f}")

            update_progress("完成", overall_total, overall_total, f"完成! 总体评分: {score.overall:.2f}", 1, 1)
            return result

        except Exception as e:
            logger.exception(f"生成过程异常: {e}")
            return None

    def check_dependencies(self) -> Tuple[bool, str]:
        """检查依赖是否满足"""
        ffmpeg_ok, ffmpeg_msg = self.downloader.check_ffmpeg()
        if not ffmpeg_ok:
            return False, ffmpeg_msg

        if not (self.config.volc_ark_api_key or "").strip():
            return False, "未配置火山方舟 API Key"
        if not (self.config.volc_chat_model or "").strip():
            return False, "未配置火山方舟模型名称（例如 doubao-seed-2-0-lite-260215）"
        if not (self.config.volc_auc_api_key or "").strip():
            return False, "未配置AUC x-api-key"
        return True, "所有依赖检查通过"




    def chat_with_skill(self, skill: Skill, user_message: str) -> Optional[str]:
        """与Skill对话测试"""
        return self.ai_generator.chat_with_skill(skill, user_message)

    def chat_with_skill_stream(self, skill: Skill, user_message: str):
        return self.ai_generator.chat_with_skill_stream(skill, user_message)
