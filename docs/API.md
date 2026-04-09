# API 文档

## 模块概述

本项目采用模块化设计，核心模块如下：

| 模块 | 功能 | 位置 |
|------|------|------|
| `models` | 数据模型定义 | `src/models.py` |
| `downloader` | 视频抓取 | `src/downloader.py` |
| `audio` | 音频提取 | `src/audio.py` |
| `transcriber` | 语音转写 | `src/transcriber.py` |
| `filter` | 数据过滤 | `src/filter.py` |
| `safety` | 内容安全检测 | `src/safety.py` |
| `prompts` | Prompt模板 | `src/prompts.py` |
| `ai_generator` | AI生成 | `src/ai_generator.py` |
| `exporter` | 结果导出 | `src/exporter.py` |
| `storage` | 存储管理 | `src/storage.py` |
| `engine` | 主引擎 | `src/engine.py` |

---

## 数据模型

### `VideoInfo`
视频信息

```python
class VideoInfo(BaseModel):
    aweme_id: str          # 视频ID
    title: str             # 标题
    desc: str              # 描述
    video_url: str         # 视频URL
    duration: float        # 时长（秒）
    publish_time: datetime # 发布时间
    author: str            # 作者名称
```

### `TranscriptResult`
转写结果

```python
class TranscriptResult(BaseModel):
    text: str                    # 完整文本
    segments: List[TranscriptSegment] # 分段
    language: Optional[str]     # 语言
```

### `BloggerProfile`
博主画像

```python
class BloggerProfile(BaseModel):
    content_field: str          # 内容领域
    core_topics: List[str]      # 核心主题（3-5个）
    expression_style: str       # 表达风格
    tone_characteristic: str   # 语气特点
    persona_tags: List[str]    # 人设标签（3-5个）
    common_phrases: List[str]  # 常用表达/口头禅
    target_audience: str       # 目标受众
```

### `Skill`
OpenClaw Skill结构

```python
class Skill(BaseModel):
    name: str                    # Skill名称
    description: str             # 描述
    persona: Persona             # 人设
    triggers: List[str]          # 触发词
    system_prompt: str           # 系统提示词
    examples: List[SkillExample] # 对话示例
```

### `GenerationResult`
完整生成结果

```python
class GenerationResult(BaseModel):
    blogger_id: str
    blogger_name: str
    input_url: str
    videos_processed: int
    videos_kept: int
    profile: BloggerProfile
    style_rules: StyleRule
    skill: Skill
    score: SkillScore
    created_at: datetime
    version: int
```

### `Config`
配置

```python
class Config(BaseModel):
    openai_api_key: str
    openai_base_url: Optional[str] = None
    max_videos: int = 10
    min_videos_required: int = 5
    max_chars_per_video: int = 1000
    max_total_chars: int = 5000
    output_dir: str = "./output"
    cache_dir: str = "./cache"
    log_level: str = "INFO"
```

---

## 核心类

### `GenerationEngine`
主引擎，整合完整流程

```python
class GenerationEngine:
    def __init__(self, config: Config)
        # 初始化引擎

    async def generate(
        self,
        input_url: str,
        progress_callback: Optional[Callable[[GenerationProgress], None]] = None,
    ) -> Optional[GenerationResult]:
        """
        完整生成流程

        Args:
            input_url: 博主链接或ID
            progress_callback: 进度回调函数

        Returns:
            生成结果，失败返回None
        """

    def check_dependencies(self) -> Tuple[bool, str]:
        """
        检查依赖是否满足

        Returns:
            (是否OK, 消息)
        """

    def chat_with_skill(self, skill: Skill, user_message: str) -> Optional[str]:
        """
        与Skill对话测试

        Args:
            skill: Skill对象
            user_message: 用户消息

        Returns:
            AI回复，失败返回None
        """
```

### `VideoDownloader`
视频下载器

```python
class VideoDownloader:
    def __init__(self, cache_dir: str, max_videos: int = 10)

    def extract_user_id(self, url: str) -> str:
        """从URL提取用户ID"""

    async def get_user_videos(self, url_or_id: str) -> List[VideoInfo]:
        """获取用户最近视频列表"""

    async def download_video(self, video: VideoInfo) -> Optional[VideoDownload]:
        """下载单个视频"""

    async def download_all(self, videos: List[VideoInfo]) -> List[VideoDownload]:
        """批量下载视频"""

    def check_ffmpeg(self) -> Tuple[bool, str]:
        """检查ffmpeg是否可用"""
```

### `DataFilter`
数据过滤器

```python
class DataFilter:
    def __init__(
        self,
        min_text_length: int = 50,
        max_text_length: int = 5000,
        enable_speaker_check: bool = False,
    )

    def filter_video(
        self,
        video_id: str,
        transcript: TranscriptResult,
    ) -> FilterResult:
        """过滤单个视频"""

    def filter_all(
        self,
        transcripts: List[Tuple[str, TranscriptResult]],
    ) -> Tuple[List[Tuple[str, TranscriptResult]], List[FilterResult]]:
        """批量过滤"""

    def get_kept_transcripts(
        self,
        kept: List[Tuple[str, TranscriptResult]],
    ) -> List[str]:
        """获取保留的转写文本列表"""
```

### `AIGenerator`
AI生成器

```python
class AIGenerator:
    def __init__(self, client: OpenAI, model: str = "gpt-4")

    def generate_blogger_profile(
        self,
        transcripts: List[str],
        max_total_chars: int = 5000,
    ) -> Optional[BloggerProfile]:
        """生成博主画像"""

    def generate_style_rules(
        self,
        transcripts: List[str],
        profile: BloggerProfile,
        max_total_chars: int = 5000,
    ) -> Optional[StyleRule]:
        """生成风格规则"""

    def generate_skill(
        self,
        profile: BloggerProfile,
        style_rules: StyleRule,
        transcripts: List[str],
        max_total_chars: int = 5000,
    ) -> Optional[Skill]:
        """生成Skill"""

    def evaluate_skill(self, skill: Skill) -> Optional[SkillScore]:
        """评估Skill质量"""

    def chat_with_skill(self, skill: Skill, user_message: str) -> Optional[str]:
        """与Skill对话测试"""
```

### `Storage`
存储管理器

```python
class Storage:
    def __init__(self, output_dir: str, history_file: str = "history.json")

    def load_history(self) -> List[GenerationHistory]:
        """加载历史记录"""

    def save_history(self, history: List[GenerationHistory]) -> bool:
        """保存历史记录"""

    def add_to_history(
        self,
        result: GenerationResult,
        skill_json_path: str,
    ) -> GenerationHistory:
        """添加到历史记录"""

    def get_by_blogger_id(self, blogger_id: str) -> List[GenerationHistory]:
        """获取博主的所有历史"""

    def delete_history(self, history_id: str) -> bool:
        """删除历史记录"""

    def save_config(self, config: Config, path: str = ".env.json") -> bool:
        """保存配置"""

    def load_config(self, path: str = ".env.json") -> Optional[Config]:
        """加载配置"""

    def load_result(self, json_path: str) -> Optional[GenerationResult]:
        """加载生成结果"""

    def get_next_version(self, blogger_id: str) -> int:
        """获取下一个版本号"""
```

### `Exporter`
导出器

```python
class Exporter:
    def __init__(self, output_dir: str)

    def export_json(self, result: GenerationResult, filename: Optional[str] = None) -> str:
        """导出完整JSON"""

    def export_skill_json(self, skill: Skill, output_path: str) -> str:
        """只导出Skill JSON（用于OpenClaw导入）"""

    def export_markdown(self, result: GenerationResult, filename: Optional[str] = None) -> str:
        """导出Markdown可读文档"""

    def export_prompt(self, result: GenerationResult, filename: Optional[str] = None) -> str:
        """导出纯System Prompt"""

    def export_all(self, result: GenerationResult) -> dict[str, str]:
        """导出所有格式，返回路径字典"""
```

---

## 工作流程

```
输入博主URL/ID
    ↓
获取视频列表 (yt-dlp)
    ↓
批量下载视频
    ↓
提取音频 (ffmpeg)
    ↓
Whisper转写
    ↓
数据过滤（短文本、空文本）
    ↓
内容安全检测（关键词 + GPT）
    ↓
Step 1: 生成博主画像 (GPT-4)
    ↓
Step 2: 生成风格规则 (GPT-4)
    ↓
Step 3: 生成Skill (GPT-4)
    ↓
Step 4: Skill评分 (GPT-4)
    ↓
导出多种格式
    ↓
保存到历史
    ↓
完成
```

---

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 获取视频列表失败 | 返回None，生成失败 |
| 下载视频部分失败 | 继续使用成功下载的 |
| 转写部分失败 | 继续使用成功转写的 |
| 合格视频不足 | 返回None，生成失败 |
| AI生成任意步骤失败 | 返回None，生成失败 |
| 检测到内容风险 | 继续生成，但标记风险 |

---

## 性能指标

- 单视频处理: ≤ 2分钟
- 10视频全流程: ≤ 10分钟
- 接口响应: 流式生成，实时进度

---

## 安全考虑

1. API Key存储在本地配置，不上传到任何服务器
2. 所有处理在本地完成
3. 内容安全检测：关键词过滤 + LLM审核
4. 只标记风险，不阻止生成（由用户判断）
