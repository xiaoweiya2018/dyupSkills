"""
存储与历史管理模块
"""

import os
import json
import uuid
from typing import Optional, List
from datetime import datetime
from loguru import logger
from .models import GenerationResult, GenerationHistory, Config


class Storage:
    """存储管理器"""

    def __init__(self, output_dir: str, history_file: str = "history.json"):
        self.output_dir = output_dir
        self.history_path = os.path.join(output_dir, history_file)
        os.makedirs(output_dir, exist_ok=True)

    def load_history(self) -> List[GenerationHistory]:
        """加载历史记录"""
        if not os.path.exists(self.history_path):
            return []

        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            history = [GenerationHistory(**item) for item in data]
            history.sort(key=lambda x: x.created_at, reverse=True)
            return history
        except Exception as e:
            logger.error(f"加载历史记录失败: {e}")
            return []

    def save_history(self, history: List[GenerationHistory]) -> bool:
        """保存历史记录"""
        try:
            data = [item.model_dump() for item in history]
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"保存历史记录失败: {e}")
            return False

    def add_to_history(self, result: GenerationResult, skill_path: str) -> GenerationHistory:
        """添加到历史记录"""
        history_item = GenerationHistory(
            id=str(uuid.uuid4())[:8],
            blogger_name=result.blogger_name,
            blogger_id=result.blogger_id,
            created_at=result.created_at,
            version=result.version,
            overall_score=result.score.overall,
            skill_path=skill_path,
            skill_json_path=skill_path if (skill_path or "").endswith(".json") else "",
            result_data=result.model_dump(),
            status="completed",
        )

        history = self.load_history()
        history.insert(0, history_item)

        if len(history) > 100:
            history = history[:100]

        self.save_history(history)
        logger.info(f"添加历史记录: {history_item.id} - {history_item.blogger_name}")
        return history_item

    def get_by_blogger_id(self, blogger_id: str) -> List[GenerationHistory]:
        """获取博主的所有历史"""
        history = self.load_history()
        return [h for h in history if h.blogger_id == blogger_id]

    def delete_history(self, history_id: str) -> bool:
        """删除历史记录"""
        history = self.load_history()
        original_len = len(history)
        history = [h for h in history if h.id != history_id]
        if len(history) == original_len:
            return False
        self.save_history(history)
        return True

    def save_config(self, config: Config, path: str = ".env.json") -> bool:
        """保存配置"""
        try:
            data = config.model_dump()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def load_config(self, path: str = ".env.json") -> Optional[Config]:
        """加载配置"""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Config(**data)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return None

    def load_result(self, json_path: str) -> Optional[GenerationResult]:
        """加载生成结果"""
        if not os.path.exists(json_path):
            return None
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return GenerationResult(**data)
        except Exception as e:
            logger.error(f"加载生成结果失败: {e}")
            return None

    def get_next_version(self, blogger_id: str) -> int:
        """获取下一个版本号"""
        history = self.get_by_blogger_id(blogger_id)
        if not history:
            return 1
        versions = [h.version for h in history]
        return max(versions) + 1
