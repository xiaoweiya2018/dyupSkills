#!/usr/bin/env python3
"""
命令行入口 - 抖音博主数字永生
"""

import asyncio
import argparse
import os
from loguru import logger
from src.models import Config
from src.engine import GenerationEngine
from src.storage import Storage


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="抖音博主数字永生 - 将抖音博主视频自动转化为AI Skill"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="博主链接或ID，例如: https://www.douyin.com/user/xxxxxxxxxx",
    )
    parser.add_argument(
        "--ark-api-key",
        help="火山方舟 API Key（ARK_API_KEY）",
    )
    parser.add_argument(
        "--ark-base-url",
        default="https://ark.cn-beijing.volces.com/api/v3",
        help="火山方舟 Base URL (默认: https://ark.cn-beijing.volces.com/api/v3)",
    )
    parser.add_argument(
        "--chat-model",
        default="doubao-seed-2-0-lite-260215",
        help="火山方舟模型名称（例如 doubao-seed-2-0-lite-260215）",
    )
    parser.add_argument(
        "--auc-api-key",
        default="",
        help="AUC x-api-key（大模型录音文件识别）",
    )
    parser.add_argument(
        "--auc-base-url",
        default="https://openspeech.bytedance.com",
        help="AUC Base URL (默认: https://openspeech.bytedance.com)",
    )
    parser.add_argument(
        "--auc-resource-id",
        default="volc.seedasr.auc",
        help="AUC Resource ID (默认: volc.seedasr.auc)",
    )
    parser.add_argument(
        "--auc-model-name",
        default="bigmodel",
        help="AUC Model Name (默认: bigmodel)",
    )
    parser.add_argument(
        "--auc-audio-url-prefix",
        default="",
        help="AUC 音频公网URL前缀（submit需要audio.url，例如 https://your-cdn/audio ）",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default="./output",
        help="输出目录 (默认: ./output)",
    )
    parser.add_argument(
        "--cache-dir", "-c",
        default="./cache",
        help="缓存目录 (默认: ./cache)",
    )
    parser.add_argument(
        "--max-videos", "-m",
        type=int,
        default=10,
        help="最大视频数 (默认: 10)",
    )
    parser.add_argument(
        "--min-videos",
        type=int,
        default=5,
        help="最少合格视频数 (默认: 5)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )
    parser.add_argument(
        "--douyin-cookie",
        help="抖音 Cookie 字符串（从浏览器开发者工具复制 Cookie: 的完整内容）",
    )
    parser.add_argument(
        "--douyin-user-agent",
        default="",
        help="抖音 User-Agent (可选，建议与 Cookie 所在浏览器一致)",
    )
    parser.add_argument(
        "--douyin-type",
        default="post",
        choices=["post", "aweme", "favorite", "collection", "search", "music", "hashtag", "mix", "following", "follower"],
        help="DouyinCrawler 采集类型 (默认: post)",
    )
    return parser.parse_args()


def get_config(args) -> Config:
    """获取配置"""
    api_key = args.ark_api_key or os.getenv("VOLC_ARK_API_KEY")
    base_url = args.ark_base_url or os.getenv("VOLC_ARK_BASE_URL")

    if not api_key:
        storage = Storage(args.output_dir)
        config = storage.load_config()
        if config:
            return config

    if not api_key:
        raise ValueError("必须提供火山方舟 API Key，可以通过--ark-api-key或环境变量VOLC_ARK_API_KEY设置")

    douyin_cookie = args.douyin_cookie or os.getenv("DOUYIN_COOKIE", "")
    douyin_user_agent = args.douyin_user_agent or os.getenv("DOUYIN_USER_AGENT", "")

    return Config(
        volc_ark_api_key=api_key,
        volc_ark_base_url=base_url,
        volc_chat_model=args.chat_model,
        volc_auc_api_key=args.auc_api_key or os.getenv("VOLC_AUC_API_KEY", ""),
        volc_auc_base_url=args.auc_base_url or os.getenv("VOLC_AUC_BASE_URL", "https://openspeech.bytedance.com"),
        volc_auc_resource_id=args.auc_resource_id or os.getenv("VOLC_AUC_RESOURCE_ID", "volc.seedasr.auc"),
        volc_auc_model_name=args.auc_model_name or os.getenv("VOLC_AUC_MODEL_NAME", "bigmodel"),
        volc_auc_audio_url_prefix=args.auc_audio_url_prefix or os.getenv("VOLC_AUC_AUDIO_URL_PREFIX", ""),
        max_videos=args.max_videos,
        min_videos_required=args.min_videos,
        output_dir=args.output_dir,
        cache_dir=args.cache_dir,
        log_level=args.log_level,
        douyin_source="douyincrawler",
        douyincrawler_cookie=douyin_cookie,
        douyincrawler_user_agent=douyin_user_agent,
        douyincrawler_task_type=args.douyin_type,
    )


def progress_callback(progress):
    """进度回调"""
    p = progress.to_dict()
    logger.info(f"[{p['percentage']}%] {p['stage']}: {p['message']}")


async def main():
    """主函数"""
    args = parse_args()
    logger.add("main.log", rotation="10 MB", level=args.log_level)

    try:
        config = get_config(args)
    except ValueError as e:
        logger.error(e)
        return

    engine = GenerationEngine(config)

    ok, msg = engine.check_dependencies()
    if not ok:
        logger.error(f"依赖检查失败: {msg}")
        return
    logger.info(msg)

    logger.info(f"开始生成: {args.input}")
    result = await engine.generate(args.input, progress_callback)

    if result:
        logger.info(f"生成成功!")
        logger.info(f"博主: {result.blogger_name}")
        logger.info(f"Skill名称: {result.skill.name}")
        logger.info(f"总体评分: {result.score.overall:.2f}")
        logger.info(f"评分理由: {result.score.reason}")
    else:
        logger.error("生成失败")


if __name__ == "__main__":
    asyncio.run(main())
