import os
import random
from urllib.parse import quote

import exejs
import requests
from loguru import logger

from ..cookies import CookieManager
from .types import APIEndpoint, CookieField, DouyinURL, RequestHeaders, RequestParams, SignMethod, TokenConfig


def _load_sign_script():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    js_file = os.path.join(current_dir, "js", "douyin.js")
    with open(js_file, "r", encoding="utf-8") as f:
        return exejs.compile(f.read())


class Request(object):
    HOST = DouyinURL.BASE
    SIGN = _load_sign_script()

    def __init__(self, cookie: str = "", UA: str = ""):
        self.PARAMS = RequestParams.BASE.copy()
        self.HEADERS = RequestHeaders.DEFAULT.copy()
        self.WEBID = ""
        self.COOKIES = CookieManager.cookies_str_to_dict(cookie) if cookie else {}

        if UA:
            version = UA.split(" Chrome/")[1].split(" ")[0]
            _version = version.split(".")[0]
            self.HEADERS.update(
                {
                    "User-Agent": UA,
                    "sec-ch-ua": f'"Chromium";v="{_version}", "Not(A:Brand";v="24", "Google Chrome";v="{_version}"',
                }
            )
            self.PARAMS.update(
                {
                    "browser_version": version,
                    "engine_version": version,
                }
            )

    def get_sign(self, uri: str, params: dict) -> dict:
        query = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
        call_name = SignMethod.DETAIL
        if "reply" in uri:
            call_name = SignMethod.REPLY
        return self.SIGN.call(call_name, query, self.HEADERS.get("User-Agent"))

    def get_params(self, params: dict) -> dict:
        params[CookieField.MS_TOKEN] = self.get_ms_token()
        params["screen_width"] = self.COOKIES.get(CookieField.DY_SWIDTH, 2560)
        params["screen_height"] = self.COOKIES.get(CookieField.DY_SHEIGHT, 1440)
        params["cpu_core_num"] = self.COOKIES.get(CookieField.DEVICE_WEB_CPU_CORE, 24)
        params["device_memory"] = self.COOKIES.get(CookieField.DEVICE_WEB_MEMORY_SIZE, 8)
        params["verifyFp"] = self.COOKIES.get(CookieField.S_V_WEB_ID, None)
        params["fp"] = self.COOKIES.get(CookieField.S_V_WEB_ID, None)
        params["webid"] = self.get_webid()
        return params

    def get_webid(self):
        if not self.WEBID:
            self.WEBID = str(random.randint(TokenConfig.WEBID_MIN, TokenConfig.WEBID_MAX))
        return self.WEBID

    def get_ms_token(self, randomlength=None):
        ms_token = self.COOKIES.get(CookieField.MS_TOKEN, None)
        if not ms_token:
            if randomlength is None:
                randomlength = TokenConfig.MS_TOKEN_LENGTH
            ms_token = ""
            base_str = TokenConfig.MS_TOKEN_CHARS
            length = len(base_str) - 1
            for _ in range(randomlength):
                ms_token += base_str[random.randint(0, length)]
        return ms_token

    def getHTML(self, url) -> str:
        headers = self.HEADERS.copy()
        headers["sec-fetch-dest"] = "document"
        response = requests.get(url, headers=headers, cookies=self.COOKIES, timeout=10)
        if response.status_code != 200 or response.text == "":
            logger.error(f"HTML请求失败, url: {url}, header: {headers}")
            return ""
        return response.text

    def getJSON(self, uri: str, params: dict, data: dict = None):
        url = f"{self.HOST}{uri}"
        params.update(self.PARAMS)
        if uri in [APIEndpoint.AWEME_DETAIL, APIEndpoint.MUSIC_AWEME, APIEndpoint.USER_FOLLOWER]:
            params["a_bogus"] = self.get_sign(uri, params)

        if data:
            response = requests.post(
                url,
                params=params,
                data=data,
                headers=self.HEADERS,
                cookies=self.COOKIES,
                timeout=20,
            )
        else:
            response = requests.get(
                url, params=params, headers=self.HEADERS, cookies=self.COOKIES, timeout=20
            )

        if (
            response.status_code != 200
            or response.text == ""
            or response.json().get("status_code", 0) != 0
        ):
            logger.error(
                f"JSON请求失败：url: {url},  params: {params}, code: {response.status_code}, body: {response.text}"
            )
            return {}

        return response.json()

