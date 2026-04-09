# 作品类型
class AwemeType:
    VIDEO = 4
    IMAGE = 68
    LIVE = 101
    VIDEO_MAX = 66
    VIDEO_SPECIAL = [69, 107]


class APIConfig:
    DEFAULT_COUNT = 18
    USER_SEARCH_COUNT = 10
    FOLLOW_COUNT = 20


class APIEndpoint:
    AWEME_DETAIL = "/aweme/v1/web/aweme/detail/"
    AWEME_POST = "/aweme/v1/web/aweme/post/"
    AWEME_FAVORITE = "/aweme/v1/web/aweme/favorite/"
    AWEME_COLLECTION = "/aweme/v1/web/aweme/listcollection/"
    MUSIC_AWEME = "/aweme/v1/web/music/aweme/"
    CHALLENGE_AWEME = "/aweme/v1/web/challenge/aweme/"
    MIX_AWEME = "/aweme/v1/web/mix/aweme/"
    SEARCH_ITEM = "/aweme/v1/web/search/item/"
    SEARCH_GENERAL = "/aweme/v1/web/general/search/single/"
    DISCOVER_SEARCH = "/aweme/v1/web/discover/search/"
    USER_FOLLOWING = "/aweme/v1/web/user/following/list/"
    USER_FOLLOWER = "/aweme/v1/web/user/follower/list/"


class DouyinURL:
    BASE = "https://www.douyin.com"
    USER = f"{BASE}/user"
    AWEME = f"{BASE}/note"
    MIX = f"{BASE}/collection"
    SEARCH = f"{BASE}/search"
    USER_SELF = f"{USER}/self"


class FieldName:
    MAX_CURSOR = "max_cursor"
    CURSOR = "cursor"
    MIN_TIME = "min_time"
    AWEME_LIST = "aweme_list"
    USER_LIST = "user_list"
    DATA = "data"
    FOLLOWINGS = "followings"
    FOLLOWERS = "followers"
    SEC_UID = "sec_uid"
    AWEME_ID = "aweme_id"


class CookieField:
    MS_TOKEN = "msToken"
    DY_SWIDTH = "dy_swidth"
    DY_SHEIGHT = "dy_sheight"
    DEVICE_WEB_CPU_CORE = "device_web_cpu_core"
    DEVICE_WEB_MEMORY_SIZE = "device_web_memory_size"
    S_V_WEB_ID = "s_v_web_id"


class RequestParams:
    BASE = {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
    }

    EXTENDED = {
        "update_version_code": "170400",
        "pc_client_type": "1",
        "version_code": "190500",
        "version_name": "19.5.0",
        "cookie_enabled": "true",
        "screen_width": "2560",
        "screen_height": "1440",
        "browser_language": "zh-CN",
        "browser_platform": "Win32",
        "browser_name": "Chrome",
        "browser_version": "126.0.0.0",
        "browser_online": "true",
        "engine_name": "Blink",
        "engine_version": "126.0.0.0",
        "os_name": "Windows",
        "os_version": "10",
        "cpu_core_num": "24",
        "device_memory": "8",
        "platform": "PC",
        "downlink": "10",
        "effective_type": "4g",
        "round_trip_time": "50",
    }


class RequestHeaders:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"

    DEFAULT = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "priority": "u=1, i",
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "User-Agent": USER_AGENT,
        "referer": f"{DouyinURL.BASE}/",
    }


USER_ID_PREFIX = "MS4wLjABAAAA"


class SignMethod:
    DETAIL = "sign_datail"
    REPLY = "sign_reply"


class TokenConfig:
    MS_TOKEN_LENGTH = 120
    MS_TOKEN_CHARS = "ABCDEFGHIGKLMNOPQRSTUVWXYZabcdefghigklmnopqrstuvwxyz0123456789="
    WEBID_MIN = 1000000000000000000
    WEBID_MAX = 9999999999999999999

