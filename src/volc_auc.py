import base64
import json
import os
import time
import uuid
from typing import Any, Dict, Optional

import requests


class VolcAUCClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openspeech.bytedance.com",
        resource_id: str = "volc.seedasr.auc",
        model_name: str = "bigmodel",
        audio_format: str = "mp3",
        audio_codec: str = "raw",
        audio_rate: int = 16000,
        audio_bits: int = 16,
        audio_channel: int = 1,
        timeout_seconds: int = 120,
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip().rstrip("/")
        self.resource_id = (resource_id or "").strip()
        self.model_name = (model_name or "").strip() or "bigmodel"
        self.audio_format = (audio_format or "mp3").strip()
        self.audio_codec = (audio_codec or "raw").strip()
        self.audio_rate = int(audio_rate or 16000)
        self.audio_bits = int(audio_bits or 16)
        self.audio_channel = int(audio_channel or 1)
        self.timeout_seconds = timeout_seconds

    def submit_task(self, audio_url: str = "", audio_path: str = "") -> tuple[str, str]:
        if not (self.api_key or "").strip():
            raise RuntimeError("AUC缺少 x-api-key")
        if not (audio_url or "").strip() and not (audio_path or "").strip():
            raise RuntimeError("AUC标准版submit需要 audio.url 或 audio.data")

        url = f"{self.base_url}/api/v3/auc/bigmodel/submit"
        task_id = str(uuid.uuid4())

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": task_id,
            "X-Api-Sequence": "-1",
        }

        audio: Dict[str, Any]
        if (audio_url or "").strip():
            audio = {
                "url": audio_url,
                "format": self.audio_format,
                "codec": self.audio_codec,
                "rate": self.audio_rate,
                "bits": self.audio_bits,
                "channel": self.audio_channel,
            }
        else:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(audio_path)
            with open(audio_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            audio = {
                "data": b64,
                "format": self.audio_format,
                "codec": self.audio_codec,
                "rate": self.audio_rate,
                "bits": self.audio_bits,
                "channel": self.audio_channel,
            }

        payload: Dict[str, Any] = {
            "user": {"uid": "douyin"},
            "audio": audio,
            "request": {
                "model_name": self.model_name,
                "enable_itn": True,
                "enable_punc": False,
                "enable_ddc": False,
                "enable_speaker_info": False,
                "enable_channel_split": False,
                "show_utterances": False,
                "vad_segment": False,
                "sensitive_words_filter": "",
            },
        }

        session = requests.Session()
        session.trust_env = False
        proxies = {"http": None, "https": None}
        resp = session.post(url, data=json.dumps(payload), headers=headers, proxies=proxies, timeout=self.timeout_seconds)

        status_code = resp.headers.get("X-Api-Status-Code")
        message = resp.headers.get("X-Api-Message", "")
        logid = resp.headers.get("X-Tt-Logid", "")
        if status_code and status_code != "20000000":
            detail = f"AUC提交失败: {status_code} {message}".strip()
            if logid:
                detail = f"{detail} (X-Tt-Logid={logid})"
            detail = f"{detail} (resource_id={self.resource_id})"
            raise RuntimeError(detail)

        return task_id, logid

    def query_task(self, task_id: str, x_tt_logid: str) -> tuple[str, str, Dict[str, Any]]:
        url = f"{self.base_url}/api/v3/auc/bigmodel/query"

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Request-Id": task_id,
        }
        if x_tt_logid:
            headers["X-Tt-Logid"] = x_tt_logid

        session = requests.Session()
        session.trust_env = False
        proxies = {"http": None, "https": None}
        resp = session.post(url, data=json.dumps({}), headers=headers, proxies=proxies, timeout=self.timeout_seconds)

        status_code = resp.headers.get("X-Api-Status-Code", "")
        message = resp.headers.get("X-Api-Message", "")
        logid = resp.headers.get("X-Tt-Logid", "")

        resp.raise_for_status()
        try:
            payload = resp.json()
        except Exception:
            payload = {"text": resp.text}

        if logid and not x_tt_logid:
            x_tt_logid = logid

        return status_code, message, payload

    def recognize(
        self,
        audio_url: str = "",
        audio_path: str = "",
        poll_interval_seconds: float = 1.0,
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        start = time.time()
        task_id, logid = self.submit_task(audio_url=audio_url, audio_path=audio_path)
        while True:
            code, message, payload = self.query_task(task_id, logid)
            if code == "20000000":
                return payload
            if code and code not in ["20000001", "20000002"]:
                detail = f"AUC查询失败: {code} {message}".strip()
                if logid:
                    detail = f"{detail} (X-Tt-Logid={logid})"
                detail = f"{detail} (resource_id={self.resource_id})"
                raise RuntimeError(detail)
            if time.time() - start > timeout_seconds:
                raise TimeoutError("AUC转写查询超时")
            time.sleep(poll_interval_seconds)


def extract_text_and_segments(payload: Dict[str, Any]) -> tuple[str, list[dict]]:
    if not isinstance(payload, dict):
        return "", []

    def get_first_dict(d: Dict[str, Any], keys: list[str]) -> Optional[Dict[str, Any]]:
        for k in keys:
            v = d.get(k)
            if isinstance(v, dict):
                return v
        return None

    def get_first_list(d: Dict[str, Any], keys: list[str]) -> Optional[list]:
        for k in keys:
            v = d.get(k)
            if isinstance(v, list):
                return v
        return None

    container = get_first_dict(payload, ["result", "data"]) or payload
    text = ""
    if isinstance(payload.get("text"), str):
        text = payload["text"]
    elif isinstance(container.get("text"), str):
        text = container["text"]

    segs = (
        get_first_list(payload, ["utterances", "segments"])
        or get_first_list(container, ["utterances", "segments"])
        or []
    )

    segments: list[dict] = []
    if isinstance(segs, list):
        for seg in segs:
            if not isinstance(seg, dict):
                continue
            raw_text = (
                seg.get("text")
                or seg.get("utterance")
                or seg.get("sentence")
                or seg.get("asr_text")
                or ""
            )
            start = seg.get("start", seg.get("start_time", 0.0))
            end = seg.get("end", seg.get("end_time", 0.0))

            try:
                start_f = float(start or 0.0)
                end_f = float(end or 0.0)
                if start_f > 1000 or end_f > 1000:
                    start_f = start_f / 1000.0
                    end_f = end_f / 1000.0
            except Exception:
                start_f = 0.0
                end_f = 0.0

            segments.append({"start": start_f, "end": end_f, "text": str(raw_text).strip()})

    if not text and segments:
        text = "\n".join([s["text"] for s in segments if s.get("text")])

    return str(text or "").strip(), segments


def safe_json_dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)

