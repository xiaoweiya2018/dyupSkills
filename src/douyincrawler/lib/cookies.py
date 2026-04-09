from typing import Dict

import requests
from loguru import logger


class CookieManager:
    @staticmethod
    def validate_cookie(cookie: str) -> bool:
        if not cookie or not cookie.strip():
            logger.debug("Cookie为空")
            return False

        required_fields = ["sessionid", "ttwid"]
        cookie_lower = cookie.lower()
        has_required_field = any(field in cookie_lower for field in required_fields)
        if not has_required_field:
            logger.warning(f"Cookie缺少必要字段，至少需要包含: {', '.join(required_fields)}")
            return False

        if "=" not in cookie:
            logger.warning("Cookie格式不正确，缺少键值对分隔符")
            return False

        return True

    @staticmethod
    def cookies_str_to_dict(cookie_string: str) -> Dict[str, str]:
        if not cookie_string or not cookie_string.strip():
            return {}

        cookies = cookie_string.strip().replace("; ", ";").split(";")
        cookie_dict: Dict[str, str] = {}

        for cookie in cookies:
            cookie = cookie.strip()
            if not cookie or cookie == "douyin.com":
                continue
            if "=" not in cookie:
                logger.debug(f"跳过无效的Cookie片段: {cookie}")
                continue

            try:
                key, value = cookie.split("=", 1)
                key = key.strip()
                value = value.strip().rstrip(";")
                if key and value:
                    cookie_dict[key] = value
            except ValueError as e:
                logger.debug(f"解析Cookie片段失败: {cookie}, 错误: {e}")
                continue

        return cookie_dict

    @staticmethod
    def cookies_dict_to_str(cookie_dict: Dict[str, str]) -> str:
        if not cookie_dict:
            return ""
        valid_items = [(k, v) for k, v in cookie_dict.items() if k and v]
        return "; ".join([f"{key}={value}" for key, value in valid_items])

    @staticmethod
    def test_cookie_validity(cookie: str) -> bool:
        if not cookie or not cookie.strip():
            logger.debug("Cookie为空，无法验证")
            return False

        try:
            url = "https://sso.douyin.com/check_login/"
            cookie_dict = CookieManager.cookies_str_to_dict(cookie)
            if not cookie_dict:
                logger.warning("Cookie解析失败，无法验证")
                return False

            response = requests.get(url, cookies=cookie_dict, timeout=10)
            if response.status_code != 200:
                logger.warning(f"Cookie验证请求失败，状态码: {response.status_code}")
                return False

            result = response.json()
            if result.get("has_login") is True:
                logger.success("Cookie验证成功，用户已登录")
                return True
            logger.warning("Cookie验证失败，用户未登录")
            return False

        except requests.exceptions.Timeout:
            logger.error("Cookie验证请求超时")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Cookie验证网络请求失败: {e}")
            return False
        except ValueError as e:
            logger.error(f"Cookie验证响应解析失败: {e}")
            return False
        except Exception as e:
            logger.error(f"Cookie验证失败，未知错误: {e}")
            return False

