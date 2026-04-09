import json
import os
from typing import Any, Dict, Iterable, List, Optional

import requests


class ArkClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip().rstrip("/")

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
        }

    def chat_completions(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        timeout_seconds: int = 180,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        session = requests.Session()
        session.trust_env = False
        proxies = {"http": None, "https": None}

        last_err: Optional[Exception] = None
        for attempt in range(3):
            try:
                resp = session.post(
                    url,
                    headers=self._headers(),
                    json=payload,
                    proxies=proxies,
                    timeout=timeout_seconds,
                )
                break
            except requests.exceptions.ReadTimeout as e:
                last_err = e
                if attempt < 2:
                    timeout_seconds = int(timeout_seconds * 1.5)
                    continue
                raise RuntimeError(f"Ark请求超时: {e}")
            except requests.exceptions.RequestException as e:
                raise RuntimeError(f"Ark请求失败: {e}")
        else:
            raise RuntimeError(f"Ark请求失败: {last_err}")

        if resp.status_code >= 400:
            try:
                data = resp.json()
                err = (data or {}).get("error") or {}
                msg = err.get("message") or resp.text
            except Exception:
                msg = resp.text
            raise RuntimeError(f"Ark请求失败 HTTP {resp.status_code}: {str(msg)[:300]}")
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        msg = (choices[0] or {}).get("message") or {}
        return (msg.get("content") or "").strip()

    def chat_completions_stream(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        timeout_seconds: int = 180,
    ) -> Iterable[str]:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        session = requests.Session()
        session.trust_env = False
        proxies = {"http": None, "https": None}

        resp = session.post(
            url,
            headers=self._headers(),
            json=payload,
            proxies=proxies,
            timeout=timeout_seconds,
            stream=True,
        )
        resp.encoding = "utf-8"
        if resp.status_code >= 400:
            try:
                data = resp.json()
                err = (data or {}).get("error") or {}
                msg = err.get("message") or resp.text
            except Exception:
                msg = resp.text
            raise RuntimeError(f"Ark请求失败 HTTP {resp.status_code}: {str(msg)[:300]}")

        for raw in resp.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line[5:].strip()
            if line == "[DONE]":
                break
            try:
                data = json.loads(line)
            except Exception:
                continue
            choices = data.get("choices") or []
            if not choices:
                continue
            c0 = choices[0] or {}
            delta = c0.get("delta") or {}
            piece = delta.get("content")
            if piece is None:
                msg = c0.get("message") or {}
                piece = msg.get("content")
            if piece:
                yield str(piece)

    def audio_transcriptions(
        self,
        model: str,
        audio_path: str,
        response_format: str = "verbose_json",
        timeout_seconds: int = 300,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/audio/transcriptions"
        if not os.path.exists(audio_path):
            raise FileNotFoundError(audio_path)
            
        session = requests.Session()
        session.trust_env = False
        proxies = {"http": None, "https": None}
        
        with open(audio_path, "rb") as f:
            files = {"file": (os.path.basename(audio_path), f)}
            data = {"model": model, "response_format": response_format}
            resp = session.post(url, headers=self._headers(), data=data, files=files, proxies=proxies, timeout=timeout_seconds)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {"text": resp.text}


def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None

