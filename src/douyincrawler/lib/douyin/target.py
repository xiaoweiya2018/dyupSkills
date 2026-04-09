import os
import re
from urllib.parse import parse_qs, quote, unquote, urlparse

import ujson as json
from loguru import logger

from ...utils.text import quit, sanitize_filename, url_redirect
from .types import USER_ID_PREFIX, DouyinURL


class TargetHandler:
    def __init__(self, request, target: str, type: str, down_path: str):
        self.request = request
        self.target = target
        self.type = type
        self.down_path = down_path
        self.id = ""
        self.url = ""
        self.title = ""
        self.info = {}
        self.render_data = {}

    def parse_target_id(self):
        if self.target:
            target = self.target.strip()
            hostname = urlparse(target).hostname

            if hostname and hostname.endswith("douyin.com"):
                self._parse_url(target, hostname)
            else:
                self._parse_non_url(target)
        else:
            self.id = self._get_self_uid()
            self.url = DouyinURL.USER_SELF

    def _parse_url(self, target: str, hostname: str):
        if hostname == "v.douyin.com":
            target = url_redirect(target)

        path = unquote(urlparse(target).path.strip("/"))
        path_parts = path.split("/")

        if len(path_parts) < 2:
            self.type = "aweme"
            self.id = path_parts[-1] if path_parts else ""
            self.url = target
        else:
            _type = path_parts[-2]
            self.id = path_parts[-1]
            self.url = target

            if _type in ["video", "note"]:
                self.type = "aweme"
                self.url = f"{DouyinURL.AWEME}/{self.id}"
            elif _type in ["music", "hashtag"]:
                self.type = _type
            elif _type == "collection":
                self.type = "mix"
            elif _type == "search":
                self.id = unquote(self.id)
                search_type = parse_qs(urlparse(target).query).get("type")
                if search_type is None or search_type[0] in ["video", "general"]:
                    self.type = "search"
                else:
                    self.type = search_type[0]

    def _parse_non_url(self, target: str):
        self.id = target

        if self.type in ["search"]:
            self.url = f"{DouyinURL.SEARCH}/{quote(self.id)}"
        elif self.type in ["aweme", "music", "hashtag", "mix"] and self.id.isdigit():
            if self.type == "aweme":
                self.url = f"{DouyinURL.AWEME}/{self.id}"
            elif self.type == "mix":
                self.url = f"{DouyinURL.MIX}/{self.id}"
            else:
                self.url = f"{DouyinURL.BASE}/{self.type}/{self.id}"
        elif self.type in ["post", "favorite", "collection", "following", "follower"] and self.id.startswith(
            USER_ID_PREFIX
        ):
            self.url = f"{DouyinURL.USER}/{self.id}"
        else:
            quit(f"[{self.id}]目标输入错误，请检查参数")

    def _get_self_uid(self) -> str:
        url = DouyinURL.USER_SELF
        text = self.request.getHTML(url)
        if text == "":
            quit(f"获取UID请求失败, url: {url}")

        pattern = r'secUid\\":\\"([-\w]+)\\"'
        match = re.search(pattern, text)
        if match:
            return match.group(1)
        quit(f"获取UID请求失败, url: {url}")

    def fetch_target_info(self) -> tuple[str, str]:
        if self.type == "search":
            self.title = self.id
        elif self.type == "aweme":
            self.title = self.id
        elif self.type in ["post", "favorite", "collection", "following", "follower"]:
            self.title = self.id
        else:
            try:
                self._fetch_from_html()
            except Exception as e:
                self.title = self.id
                self.info = {}
                self.render_data = {}
                logger.warning(f"目标信息HTML解析失败，已降级为仅使用ID继续采集: {e}")

        down_path = os.path.join(self.down_path, sanitize_filename(f"{self.type}_{self.title}"))
        aria2_conf = f"{down_path}.txt"
        return self.title, down_path, aria2_conf, self.info, self.render_data

    def _fetch_from_html(self):
        text = self.request.getHTML(self.url)
        pattern = r'self\.__pace_f\.push\(\[1,"\d:\[\S+?({[\s\S]*?)\]\\n"\]\)'
        render_data_list = re.findall(pattern, text)

        if not render_data_list:
            quit(f"提取目标信息失败，可能是cookie无效。url: {self.url}")

        render_data = render_data_list[-1].replace('\\"', '"').replace("\\\\", "\\")
        self.render_data = json.loads(render_data)

        if self.type == "mix":
            self.info = self.render_data["aweme"]["detail"]["mixInfo"]
            self.title = self.info["mixName"]
        elif self.type == "music":
            self.info = self.render_data["musicDetail"]
            self.title = self.info["title"]
        elif self.type == "hashtag":
            self.info = self.render_data["topicDetail"]
            self.title = self.info["chaName"]
        elif self.type == "aweme":
            self.info = self.render_data["aweme"]["detail"]
            self.title = self.id
        elif self.type in ["post", "favorite", "collection", "following", "follower"]:
            self.info = self.render_data["user"]["user"]
            self.title = self.info["nickname"]
        else:
            quit(f"获取目标信息请求失败, type: {self.type}")

