"""
数据模型定义 - 基于Pydantic
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    """视频信息"""
    aweme_id: str
    title: str
    desc: str
    video_url: str
    duration: float
    publish_time: Optional[datetime] = None
    author: str


class VideoDownload(BaseModel):
    """已下载视频"""
    video_info: VideoInfo
    file_path: str
    audio_path: Optional[str] = None
    downloaded: bool = False


class TranscriptSegment(BaseModel):
    """转写片段"""
    start: float
    end: float
    text: str


class TranscriptResult(BaseModel):
    """转写结果"""
    text: str
    segments: List[TranscriptSegment]
    language: Optional[str] = None


class FilterResult(BaseModel):
    """过滤结果"""
    video_id: str
    kept: bool
    reason: str
    confidence: float = 1.0


class ContentSafetyResult(BaseModel):
    """内容安全检测结果"""
    risk: bool
    type: str = ""
    reason: str = ""


class BloggerProfile(BaseModel):
    """博主画像"""
    content_field: str
    core_topics: List[str]
    expression_style: str
    tone_characteristic: str
    persona_tags: List[str]
    common_phrases: List[str]
    target_audience: str


class StyleRule(BaseModel):
    """风格规则"""
    speech_structure: str
    language_features: str
    emotion_intensity: str
    uses_rhetoric: bool
    typical_sentences: List[str]


class SkillExample(BaseModel):
    """Skill对话示例"""
    user: str
    assistant: str


class Persona(BaseModel):
    """Skill人设"""
    style: str
    tone: str
    tags: List[str]


class Skill(BaseModel):
    """OpenClaw Skill结构"""
    name: str
    description: str
    persona: Persona
    triggers: List[str]
    system_prompt: str
    examples: List[SkillExample]


class SkillScore(BaseModel):
    """Skill评分"""
    purity: float
    consistency: float
    style: float
    usability: float
    reason: str

    @property
    def overall(self) -> float:
        """总体评分"""
        return (self.purity + self.consistency + self.style + self.usability) / 4


class GenerationProgress(BaseModel):
    """生成进度"""
    stage: str
    current: int
    total: int
    sub_current: int = 0
    sub_total: int = 0
    message: str
    started_at: datetime = Field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "current": self.current,
            "total": self.total,
            "percentage": int(self.current / self.total * 100) if self.total > 0 else 0,
            "sub_current": self.sub_current,
            "sub_total": self.sub_total,
            "sub_percentage": int(self.sub_current / self.sub_total * 100) if self.sub_total > 0 else 0,
            "message": self.message,
            "elapsed_seconds": (datetime.now() - self.started_at).total_seconds()
        }


class GenerationResult(BaseModel):
    """生成结果"""
    blogger_id: str
    blogger_name: str
    input_url: str
    videos_processed: int
    videos_kept: int
    profile: BloggerProfile
    style_rules: StyleRule
    skill: Skill
    score: SkillScore
    created_at: datetime = Field(default_factory=datetime.now)
    version: int = 1


class Config(BaseModel):
    """配置"""
    volc_ark_api_key: str = ""
    volc_ark_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    volc_chat_model: str = "doubao-seed-2-0-lite-260215"
    volc_auc_api_key: str = ""
    volc_auc_base_url: str = "https://openspeech.bytedance.com"
    volc_auc_resource_id: str = "volc.seedasr.auc"
    volc_auc_model_name: str = "bigmodel"
    volc_auc_audio_format: str = "mp3"
    volc_auc_audio_codec: str = "raw"
    volc_auc_audio_rate: int = 16000
    volc_auc_audio_bits: int = 16
    volc_auc_audio_channel: int = 1
    volc_auc_audio_url_prefix: str = ""
    max_videos: int = 10
    min_videos_required: int = 5
    max_chars_per_video: int = 1000
    max_total_chars: int = 5000
    output_dir: str = "./output"
    cache_dir: str = "./cache"
    log_level: str = "INFO"
    douyin_source: str = "douyincrawler"
    douyin_cookie_file: Optional[str] = None
    douyin_cookies_from_browser: Optional[str] = None
    douyin_disable_proxy: bool = True
    douyincrawler_api_base_url: str = "http://localhost:8000"
    douyincrawler_cookie: str = ""
    douyincrawler_user_agent: str = ""
    douyincrawler_task_type: str = "post"


class GenerationHistory(BaseModel):
    """历史记录项"""
    id: str
    blogger_name: str
    blogger_id: str
    created_at: datetime
    version: int
    overall_score: float
    skill_path: str = ""
    skill_json_path: str = ""
    result_data: Optional[Dict[str, Any]] = None
    status: str
