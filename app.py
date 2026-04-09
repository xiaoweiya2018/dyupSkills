"""
Streamlit Web UI - 抖音博主数字永生
"""

import asyncio
import streamlit as st
import os
from typing import Optional
from loguru import logger

from src.models import Config, GenerationResult, GenerationProgress
from src.engine import GenerationEngine
from src.storage import Storage
from src.exporter import Exporter

logger.add("app.log", rotation="10 MB", level="INFO")

DEFAULT_VOLC_ARK_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
DEFAULT_VOLC_AUC_BASE_URL = "https://openspeech.bytedance.com"
DEFAULT_VOLC_AUC_RESOURCE_ID = "volc.seedasr.auc"
DEFAULT_VOLC_AUC_MODEL_NAME = "bigmodel"
DEFAULT_VOLC_AUC_AUDIO_URL_PREFIX = ""


def apply_hidden_defaults(config: Optional[Config]) -> Optional[Config]:
    if config is None:
        return None
    try:
        return config.model_copy(update={
            "volc_ark_base_url": DEFAULT_VOLC_ARK_BASE_URL,
            "volc_auc_base_url": DEFAULT_VOLC_AUC_BASE_URL,
            "volc_auc_resource_id": DEFAULT_VOLC_AUC_RESOURCE_ID,
            "volc_auc_model_name": DEFAULT_VOLC_AUC_MODEL_NAME,
            "volc_auc_audio_url_prefix": DEFAULT_VOLC_AUC_AUDIO_URL_PREFIX,
        })
    except Exception:
        return config


def rerun():
    fn = getattr(st, "rerun", None)
    if callable(fn):
        fn()
        return
    fn = getattr(st, "experimental_rerun", None)
    if callable(fn):
        fn()
        return
    raise RuntimeError("当前 Streamlit 版本不支持 rerun")

st.set_page_config(
    page_title="抖音博主数字永生",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

def init_session_state():
    """初始化session state"""
    if "engine" not in st.session_state:
        st.session_state.engine = None
    if "result" not in st.session_state:
        st.session_state.result = None
    if "config" not in st.session_state:
        st.session_state.config = None
    if "generating" not in st.session_state:
        st.session_state.generating = False
    if "generation_running" not in st.session_state:
        st.session_state.generation_running = False
    if "pending_input_url" not in st.session_state:
        st.session_state.pending_input_url = None
    if "progress" not in st.session_state:
        st.session_state.progress = None
    if "progress_logs" not in st.session_state:
        st.session_state.progress_logs = []
    if "page" not in st.session_state:
        st.session_state.page = "✨ 生成新Skill"
    if "next_page" not in st.session_state:
        st.session_state.next_page = None
    if "clear_test_message" not in st.session_state:
        st.session_state.clear_test_message = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def load_config() -> Optional[Config]:
    """加载配置"""
    storage = Storage("./output")
    config = storage.load_config()
    if config:
        return apply_hidden_defaults(config)

    return Config(
    )

def normalize_config(value) -> Optional[Config]:
    if value is None:
        return None
    if isinstance(value, Config):
        return value
    if hasattr(value, "model_dump"):
        try:
            return Config(**value.model_dump())
        except Exception:
            return None
    if isinstance(value, dict):
        try:
            return Config(**value)
        except Exception:
            return None
    return None


def render_sidebar():
    """渲染侧边栏"""
    st.session_state.config = normalize_config(st.session_state.config)
    st.session_state.config = apply_hidden_defaults(st.session_state.config)
    cfg = st.session_state.config
    with st.sidebar:
        st.title("⚙️ 配置")

        volc_api_key = st.text_input(
            "火山方舟 API Key",
            value=getattr(cfg, "volc_ark_api_key", "") if cfg else "",
            type="password",
            help="火山方舟控制台获取的 API Key（ARK_API_KEY）",
        )

        auc_app_key = st.text_input(
            "AUC x-api-key",
            value=getattr(cfg, "volc_auc_api_key", "") if cfg else "",
            type="password",
            help="按最新示例，这里是请求头里的 x-api-key",
        )

        volc_chat_model = st.text_input(
            "LLM Model",
            value=getattr(cfg, "volc_chat_model", "doubao-seed-2-0-lite-260215") if cfg else "doubao-seed-2-0-lite-260215",
            help="填写火山方舟支持的模型名称，例如：doubao-seed-2-0-lite-260215",
        )

        max_videos = st.slider(
            "最大视频数",
            min_value=5,
            max_value=20,
            value=10,
            help="最多抓取多少个视频",
        )

        min_required = st.slider(
            "最少合格视频",
            min_value=3,
            max_value=10,
            value=5,
            help="生成需要的最少合格视频数量",
        )

        output_dir = st.text_input(
            "输出目录",
            value="./output",
        )

        cache_dir = st.text_input(
            "缓存目录",
            value="./cache",
        )

        douyincrawler_cookie = st.text_area(
            "抖音 Cookie",
            value=getattr(cfg, "douyincrawler_cookie", "") if cfg else "",
            height=120,
            help="从浏览器开发者工具 Network 任意请求的 Request Headers 里复制 Cookie: 的完整内容。需要包含 sessionid/ttwid/__ac_nonce 等关键字段。",
        )

        douyincrawler_user_agent = st.text_input(
            "抖音 User-Agent (可选)",
            value=getattr(cfg, "douyincrawler_user_agent", "") if cfg else "",
            help="建议与获取 Cookie 的浏览器一致（例如 Chrome 的 UA）。留空则使用内置默认。",
        )

        if st.button("保存配置"):
            config = Config(
                volc_ark_api_key=volc_api_key.strip(),
                volc_ark_base_url=DEFAULT_VOLC_ARK_BASE_URL,
                volc_chat_model=volc_chat_model.strip(),
                volc_auc_api_key=auc_app_key.strip(),
                volc_auc_base_url=DEFAULT_VOLC_AUC_BASE_URL,
                volc_auc_resource_id=DEFAULT_VOLC_AUC_RESOURCE_ID,
                volc_auc_model_name=DEFAULT_VOLC_AUC_MODEL_NAME,
                volc_auc_audio_url_prefix=DEFAULT_VOLC_AUC_AUDIO_URL_PREFIX,
                max_videos=max_videos,
                min_videos_required=min_required,
                output_dir=output_dir,
                cache_dir=cache_dir,
                douyin_source="douyincrawler",
                douyincrawler_cookie=douyincrawler_cookie.strip(),
                douyincrawler_user_agent=douyincrawler_user_agent.strip(),
            )
            storage = Storage(output_dir)
            storage.save_config(config)
            st.session_state.config = config
            st.success("配置已保存!")
            if volc_api_key:
                engine = GenerationEngine(config)
                st.session_state.engine = engine
                ok, msg = engine.check_dependencies()
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


def progress_callback(progress: GenerationProgress):
    """进度回调"""
    p = progress.to_dict()
    st.session_state.progress = p
    line = f"[{p.get('percentage', 0)}%] {p.get('stage', '')}: {p.get('message', '')}"
    logs = st.session_state.progress_logs or []
    if not logs or logs[-1] != line:
        logs.append(line)
        st.session_state.progress_logs = logs[-200:]


async def run_generation(input_url: str):
    """运行生成"""
    engine = st.session_state.engine
    if not engine:
        st.error("请先在侧边栏配置并保存!")
        return

    ok, msg = engine.check_dependencies()
    if not ok:
        st.error(msg)
        return

    overall_bar = st.progress(0.0)
    sub_bar = st.empty()
    info_box = st.empty()
    logs_box = st.empty()

    def ui_progress_callback(progress: GenerationProgress):
        progress_callback(progress)
        p = st.session_state.progress or {}
        overall_bar.progress((p.get("percentage", 0) or 0) / 100)
        if (p.get("sub_total", 0) or 0) > 0:
            sub_bar.progress((p.get("sub_percentage", 0) or 0) / 100)
        else:
            sub_bar.empty()
        info_box.info(f"{p.get('stage', '')}: {p.get('message', '')} ({p.get('percentage', 0)}%)")
        logs = st.session_state.progress_logs or []
        logs_box.code("\n".join(logs[-10:]), language="text")

    with st.spinner("生成中..."):
        result = await engine.generate(input_url, ui_progress_callback)

    st.session_state.result = result
    st.session_state.generating = False
    st.session_state.generation_running = False
    st.session_state.pending_input_url = None

    if result:
        st.success(f"生成完成! 总体评分: {result.score.overall:.2f}")
        exporter = Exporter(st.session_state.config.output_dir)
        skill_md = exporter.get_skill_md_path(result)
        st.info(f"SKILL.md 已生成: {skill_md}")
    else:
        st.error("生成失败，请检查日志")


def render_result(result: GenerationResult):
    """渲染生成结果"""
    st.header(f"🎯 {result.skill.name}")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("基本信息")
        st.markdown(f"""
- **博主**: {result.blogger_name}
- **博主ID**: {result.blogger_id}
- **处理视频**: {result.videos_processed} → 保留 {result.videos_kept}
- **生成时间**: {result.created_at.strftime('%Y-%m-%d %H:%M')}
- **版本**: v{result.version}
        """)

    with col2:
        st.subheader("评分")
        score = result.score
        st.markdown(f"""
| 维度 | 得分 |
|------|------|
| 纯度 | {score.purity:.2f} |
| 可信度 | {score.consistency:.2f} |
| 风格还原度 | {score.style:.2f} |
| 可用性 | {score.usability:.2f} |
| **总体** | **{score.overall:.2f}** |
        """)

    st.subheader("博主画像")
    profile = result.profile
    st.markdown(f"""
- **内容领域**: {profile.content_field}
- **核心主题**: {', '.join(profile.core_topics)}
- **表达风格**: {profile.expression_style}
- **语气特点**: {profile.tone_characteristic}
- **人设标签**: {', '.join(profile.persona_tags)}
- **目标受众**: {profile.target_audience}
    """)

    with st.expander("查看完整 System Prompt"):
        st.code(result.skill.system_prompt, language="text")

    st.subheader("对话示例")
    for i, ex in enumerate(result.skill.examples, 1):
        with st.expander(f"示例 {i}: {ex.user[:30]}..."):
            st.markdown(f"**用户:** {ex.user}")
            st.markdown(f"**助理:** {ex.assistant}")

    st.subheader("💬 在线测试")
    if st.session_state.clear_test_message:
        st.session_state.test_message = ""
        st.session_state.clear_test_message = False
    test_message = st.text_input("输入问题测试这个Skill:", key="test_message")
    if st.button("发送", key="send_test") and test_message:
        placeholder = st.empty()
        answer = ""
        with st.spinner("生成中..."):
            try:
                for delta in st.session_state.engine.chat_with_skill_stream(result.skill, test_message):
                    answer += delta
                    placeholder.markdown(answer)
            except Exception:
                answer = st.session_state.engine.chat_with_skill(result.skill, test_message) or ""
                placeholder.markdown(answer)
        if answer:
            st.session_state.chat_history.append((test_message, answer))
            st.session_state.clear_test_message = True
            rerun()

    if st.session_state.chat_history:
        st.divider()
        for user, assistant in st.session_state.chat_history:
            st.markdown(f"**👤 用户:** {user}")
            st.markdown(f"**🤖 AI:** {assistant}")
            st.divider()

        if st.button("清空对话"):
            st.session_state.chat_history = []
            rerun()


def render_history():
    """渲染历史记录"""
    st.header("📜 历史记录")

    if not st.session_state.config:
        st.warning("请先配置")
        return

    storage = Storage(st.session_state.config.output_dir)
    history = storage.load_history()

    if not history:
        st.info("暂无历史记录")
        return

    for item in history:
        with st.expander(f"{item.blogger_name} v{item.version} - 评分: {item.overall_score:.2f}"):
            skill_path = item.skill_path or item.skill_json_path
            st.markdown(f"""
- **ID**: {item.id}
- **博主ID**: {item.blogger_id}
- **创建时间**: {item.created_at.strftime('%Y-%m-%d %H:%M')}
- **文件**: {skill_path}
            """)

            if st.button("加载", key=f"load_{item.id}"):
                if item.result_data:
                    try:
                        result = GenerationResult(**item.result_data)
                        st.session_state.result = result
                        st.session_state.next_page = "✨ 生成新Skill"
                        st.session_state.chat_history = []
                        st.success("已加载")
                        rerun()
                    except Exception:
                        st.error("历史记录中的 result_data 无法解析")
                elif (item.skill_json_path or "").endswith("_skill.json"):
                    result = storage.load_result(item.skill_json_path.replace("_skill.json", "_full.json"))
                    if result:
                        st.session_state.result = result
                        st.session_state.next_page = "✨ 生成新Skill"
                        st.session_state.chat_history = []
                        st.success("已加载")
                        rerun()
                    else:
                        st.error("无法加载完整结果")
                else:
                    st.error("该历史记录没有可加载的结果数据")

            if st.button("删除", key=f"delete_{item.id}"):
                storage.delete_history(item.id)
                st.success("已删除")
                rerun()


def main():
    """主入口"""
    init_session_state()

    st.title("🧠 抖音博主数字永生")
    st.markdown("""
将抖音博主视频自动转化为可对话的AI Skill，实现"数字永生"。

> **产品定位**: 抖音博主内容 → OpenClaw Skill 自动生成工具
""")

    if not st.session_state.config:
        config = load_config()
        st.session_state.config = config

    render_sidebar()

    if st.session_state.progress and st.session_state.generating:
        p = st.session_state.progress
        st.progress(p["percentage"] / 100)
        st.info(f"{p['stage']}: {p['message']} ({p['percentage']}%)")
        if p.get("sub_total", 0) > 0:
            st.progress(p.get("sub_percentage", 0) / 100)
        with st.expander("查看详细进度日志", expanded=False):
            for line in st.session_state.progress_logs[-10:]:
                st.write(line)

    if st.session_state.next_page:
        st.session_state.page = st.session_state.next_page
        st.session_state.next_page = None

    page = st.radio(
        "导航",
        ["✨ 生成新Skill", "📜 历史记录", "ℹ️ 关于"],
        horizontal=True,
        key="page",
    )

    if (
        st.session_state.page == "✨ 生成新Skill"
        and st.session_state.generating
        and st.session_state.pending_input_url
        and not st.session_state.generation_running
    ):
        st.session_state.generation_running = True
        asyncio.run(run_generation(st.session_state.pending_input_url))

    if page == "✨ 生成新Skill":
        input_url = st.text_input(
            "输入博主链接",
            placeholder="https://www.douyin.com/user/MS4wLj...",
            help="粘贴抖音博主主页链接",
        )

        if not st.session_state.engine and st.session_state.config:
            if st.session_state.config.volc_ark_api_key:
                engine = GenerationEngine(st.session_state.config)
                st.session_state.engine = engine

        if st.button("开始生成", disabled=st.session_state.generating):
            if not input_url:
                st.error("请输入博主链接")
                return
            if not st.session_state.engine:
                st.error("请先配置并保存")
                return

            st.session_state.generating = True
            st.session_state.result = None
            st.session_state.chat_history = []
            st.session_state.progress = None
            st.session_state.progress_logs = []
            st.session_state.pending_input_url = input_url
            st.session_state.generation_running = False
            rerun()

        if st.session_state.result:
            st.divider()
            render_result(st.session_state.result)

    if page == "📜 历史记录":
        render_history()

    if page == "ℹ️ 关于":
        st.subheader("关于")
        st.markdown("""
## 这是什么

把抖音博主的公开视频内容，自动提取为一个可对话的 OpenClaw Skill，用于“像该博主一样说话 + 输出有价值内容”的对话模拟。

## 生成流程（端到端）

1. **采集视频列表**：通过内置 DouyinCrawler（Cookie + 签名请求）拉取作品列表与下载地址  
2. **下载视频**：将 mp4 下载到本地缓存目录  
3. **提取音频**：使用 ffmpeg 从视频中提取音频  
4. **语音转写**：使用 OpenSpeech AUC 标准版 submit/query 将音频转为文本（支持本地音频 data 提交或公网 url 提交）  
5. **数据过滤**：过滤纯音乐、短文本、低质量样本，保证“宁可少，也要纯”  
6. **内容安全检测**：关键词规则 + LLM 检测风险并给出原因  
7. **AI生成**：生成博主画像、风格规则、Skill，并对 Skill 质量打分  
8. **导出技能**：输出为 `skills/<skill-id>/SKILL.md`（YAML Frontmatter + Markdown 正文）

## 产物与目录

- Skill 输出：`<工作区>/skills/<skill-id>/SKILL.md`  
- 缓存目录：`<cache_dir>/videos`、`<cache_dir>/audio`（用于断点续跑与复用转写缓存）  
- 历史记录：`<output_dir>/history.json`（包含 `result_data`，用于历史“一键加载即展示”）

## 关键配置

- 抖音 Cookie：用于 DouyinCrawler 访问作品列表与下载地址  
- AUC x-api-key / Resource ID：用于语音转写  
- 火山方舟 API Key / Model：用于画像、风格、Skill 与评分生成

## 使用建议

- 优先选择单人讲述型视频作为样本来源，效果最好  
- 如果网络环境有全局代理/TUN，可能影响外部接口访问，可在系统层面确认网络连通性  
- 生成内容仅用于学习研究与内部测试，避免用于侵权与不当用途

## 合规声明

本工具仅用于个人学习与研究用途。用户使用本工具产生的内容与行为应自行承担责任，并确保不侵犯任何第三方合法权益。
        """)


if __name__ == "__main__":
    main()
