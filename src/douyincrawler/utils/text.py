import os
import random
import re
import time
from typing import Union

import requests
import ujson as json
from loguru import logger


def gen_random_str(length: int = 16, lower: bool = False) -> str:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    if lower:
        chars = chars.lower()
    return "".join(random.choice(chars) for _ in range(length))


def get_timestamp(type: str = "ms") -> int:
    if type == "ms":
        return str(int(time.time() * 1000))
    if type == "s":
        return str(int(time.time()))
    raise ValueError("只支持 'ms' 或 's'（毫秒或秒）")


def extract_valid_urls(input_data: Union[str, list]) -> Union[str, list, None]:
    url_pattern = re.compile(r"https?://[^\s]+")

    if isinstance(input_data, str):
        match = url_pattern.search(input_data)
        return match.group(0) if match else input_data
    if isinstance(input_data, list):
        return [extract_valid_urls(item) for item in input_data if item]
    return None


def sanitize_filename(text: str, max_bytes: int = 100, add_ellipsis: bool = True) -> str:
    if not text or not isinstance(text, str):
        return "无标题"

    text = text.strip()
    if not text:
        return "无标题"

    safe_text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    safe_text = re.sub(r"\s+", " ", safe_text).strip()

    if not safe_text:
        return "无标题"

    if len(safe_text.encode("utf-8")) > max_bytes:
        safe_text_bytes = safe_text.encode("utf-8")[:max_bytes]
        safe_text = safe_text_bytes.decode("utf-8", errors="ignore").strip()
        if safe_text and add_ellipsis:
            safe_text = safe_text + "..."

    return safe_text if safe_text else "无标题"


def quit(str: str = ""):
    if str:
        logger.error(str)
    raise Exception(str if str else "程序异常退出")


def url_redirect(url: str) -> str:
    r = requests.head(url, allow_redirects=True)
    return r.url


def save_json(filename: str, data: dict) -> None:
    path = os.path.dirname(filename)
    if path:
        os.makedirs(path, exist_ok=True)

    with open(f"{filename}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

