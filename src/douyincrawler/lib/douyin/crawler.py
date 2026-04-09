import os
from threading import Lock

import ujson as json
from loguru import logger

from ...utils.text import quit, save_json
from .client import DouyinClient
from .parser import DataParser
from .request import Request
from .target import TargetHandler
from .types import DouyinURL, FieldName


class Douyin:
    def __init__(
        self,
        target: str = "",
        limit: int = 0,
        type: str = "post",
        down_path: str = "下载",
        cookie: str = "",
        user_agent: str = "",
        filters: dict = None,
        on_new_items: callable = None,
    ):
        self.target = target
        self.limit = limit
        self.type = type
        self.filters = filters or {}
        self.on_new_items = on_new_items

        self.down_path = os.path.join(".", down_path)
        if not os.path.exists(self.down_path):
            os.makedirs(self.down_path)

        self.has_more = True
        self.results_old = []
        self.results = []
        self.lock = Lock()

        self.request = Request(cookie, user_agent)
        self.client = DouyinClient(self.request)

        self.id = ""
        self.url = ""
        self.title = ""
        self.info = {}
        self.render_data = {}
        self.aria2_conf = ""

    def run(self):
        self._get_target_info()

        if self.type in ["following", "follower"]:
            self.get_awemes_list()
        elif self.type in ["post", "favorite", "collection", "search", "music", "hashtag", "mix"]:
            self.get_awemes_list()
        elif self.type == "aweme":
            self.get_aweme_detail()
        else:
            quit(f"获取目标类型错误, type: {self.type}")

    def get_target_id(self):
        handler = TargetHandler(self.request, self.target, self.type, self.down_path)
        handler.parse_target_id()
        self.id = handler.id
        self.url = handler.url
        self.type = handler.type

    def _get_target_info(self):
        handler = TargetHandler(self.request, self.target, self.type, self.down_path)
        handler.parse_target_id()

        self.id = handler.id
        self.url = handler.url
        self.type = handler.type

        self.title, self.down_path, self.aria2_conf, self.info, self.render_data = handler.fetch_target_info()

        if self.type == "post":
            json_path = f"{self.down_path}.json"
            if os.path.exists(json_path) and not self.results_old:
                with open(json_path, "r", encoding="utf-8") as f:
                    self.results_old = json.load(f)

    def get_aweme_detail(self):
        if self.render_data.get("aweme"):
            aweme_detail = self.render_data["aweme"]["detail"]
        else:
            aweme_detail = self.client.fetch_aweme_detail(self.id)

        with self.lock:
            new_items, self.has_more = DataParser.parse_awemes(
                [aweme_detail],
                self.results,
                self.results_old,
                self.limit,
                self.has_more,
                self.type,
                self.down_path,
            )
            if new_items and self.on_new_items:
                self.on_new_items(new_items, self.type)

        self.save()

    def get_awemes_list(self):
        max_cursor = 0
        logid = ""
        retry = 0
        max_retry = 10

        while self.has_more:
            try:
                items_list, max_cursor, logid, self.has_more = self.client.fetch_awemes_list(
                    self.type, self.id, max_cursor, logid, self.filters
                )
                if items_list:
                    retry = 0
            except Exception as e:
                retry += 1
                logger.error(f"采集请求出错: {e}... 进行第{retry}次重试")
                if retry >= max_retry:
                    logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    logger.error(f"✗ 已达到最大重试次数({max_retry}次)，停止任务")
                    logger.error(f"  当前已采集: {len(self.results)} 条数据")
                    logger.error("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    self.has_more = False
                continue

            if items_list:
                with self.lock:
                    if self.type in ["post", "favorite", "collection", "search", "music", "hashtag", "mix"]:
                        new_items, self.has_more = DataParser.parse_awemes(
                            items_list,
                            self.results,
                            self.results_old,
                            self.limit,
                            self.has_more,
                            self.type,
                            self.down_path,
                        )
                        if new_items and self.on_new_items:
                            self.on_new_items(new_items, self.type)
                    elif self.type in ["following", "follower"]:
                        self.has_more = DataParser.parse_users(items_list, self.results, self.limit, self.has_more)
                    else:
                        quit(f"类型错误，type：{self.type}")
            elif self.has_more:
                retry += 1
                logger.error(f"采集未完成，但请求结果为空... 进行第{retry}次重试")
                if retry >= max_retry:
                    logger.error(f"已达到最大重试次数({max_retry}次)，停止任务")
                    self.has_more = False

        self.save()

    def save(self):
        if not self.results:
            logger.info("本次采集结果为空")
            return

        logger.success(f"采集完成，本次共采集到 {len(self.results)} 条结果")

        if self.type == "post":
            self.results.sort(key=lambda item: item["id"], reverse=True)
        save_json(self.down_path, self.results)
        self._save_aria2_config()

    def _save_aria2_config(self):
        lines = []

        if self.type in ["following", "follower"]:
            lines = [
                f"{DouyinURL.USER}/{line.get(FieldName.SEC_UID, 'None')}\n"
                for line in self.results
                if line.get(FieldName.SEC_UID)
            ]
        else:
            for line in self.results:
                desc = line.get("desc") or "无标题"
                filename = f'{line["id"]}_{desc}'

                if self.type == "mix":
                    filename = f"第{line['no']}集_{filename}"

                if isinstance(line["download_addr"], list):
                    if self.type == "aweme":
                        down_path = self.down_path.replace(line["id"], filename)
                    else:
                        down_path = os.path.join(self.down_path, filename)

                    for index, addr in enumerate(line["download_addr"]):
                        lines.append(f'{addr}\n dir={down_path}\n out={line["id"]}_{index + 1}.jpeg\n')
                elif isinstance(line["download_addr"], str):
                    lines.append(f'{line["download_addr"]}\n dir={self.down_path}\n out={filename}.mp4\n')
                else:
                    logger.error("下载地址错误")

        if lines:
            with open(self.aria2_conf, "w", encoding="utf-8") as f:
                f.writelines(lines)

