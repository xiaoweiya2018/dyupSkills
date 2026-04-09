# 部署手册（最新）

本项目已从 OpenAI/yt-dlp 方案切换为“内置 DouyinCrawler + 火山 OpenSpeech AUC + 火山方舟（Doubao）”，输出格式为 OpenClaw 的 `SKILL.md`。

## 环境要求

### 系统要求
- Python 3.10+
- ffmpeg（必须安装并添加到 PATH）
- 网络连接（访问抖音与火山接口）

### 依赖软件
1. **ffmpeg**（音频提取必需）
   - Windows：下载 ffmpeg 并将 `bin` 目录加入 PATH
   - macOS：`brew install ffmpeg`
   - Ubuntu/Debian：`sudo apt install ffmpeg`
2. **Python 依赖**：见 `requirements.txt`

## 安装步骤

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd 抖音博主数字永生
```

### 2. 创建虚拟环境（推荐）
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 验证 ffmpeg
```bash
ffmpeg -version
```

## 运行方式

### 方式一：Web 界面（推荐）

**Windows:**
```bat
start.bat
```

**Linux/macOS:**
```bash
chmod +x start.sh
./start.sh
```

**手动启动:**
```bash
streamlit run app.py
```

启动后浏览器访问 `http://localhost:8501`

### 方式二：命令行（CLI）

```bash
python main.py --input https://www.douyin.com/user/xxxxxxxxxx ^
  --ark-api-key <VOLC_ARK_API_KEY> ^
  --auc-api-key <VOLC_AUC_API_KEY> ^
  --douyin-cookie "<DOUYIN_COOKIE>"
```

常用参数说明：
```
--input              博主主页链接（必填）
--ark-api-key         火山方舟 API Key（也可用环境变量 VOLC_ARK_API_KEY）
--chat-model          方舟模型名（默认 doubao-seed-2-0-lite-260215）
--auc-api-key         AUC x-api-key（也可用环境变量 VOLC_AUC_API_KEY）
--douyin-cookie       抖音 Cookie（也可用环境变量 DOUYIN_COOKIE）
--douyin-user-agent   抖音 User-Agent（可选）
--max-videos          最大抓取视频数（默认 10）
--min-videos          最少合格视频数（默认 5）
--output-dir          输出目录（默认 ./output）
--cache-dir           缓存目录（默认 ./cache）
```

## 配置说明

### 配置方式
1. **Web 界面**：在侧边栏填写配置后点击“保存配置”
2. **环境变量（可选）**
   ```bash
   export VOLC_ARK_API_KEY=...
   export VOLC_AUC_API_KEY=...
   export DOUYIN_COOKIE=...
   ```
3. **配置文件**：配置保存在 `.env.json`

### 配置项（核心）
| 配置项 | 说明 |
|---|---|
| `volc_ark_api_key` | 火山方舟 API Key |
| `volc_chat_model` | 方舟模型名（默认已内置） |
| `volc_auc_api_key` | AUC x-api-key |
| `douyincrawler_cookie` | 抖音 Cookie（必须） |
| `douyincrawler_user_agent` | 抖音 UA（可选） |
| `max_videos` | 最大抓取视频数 |
| `min_videos_required` | 最少合格视频数 |
| `output_dir` / `cache_dir` | 输出/缓存目录 |

说明：WebUI 中部分 Base URL / Resource ID / Model Name 已内置默认值，不需要用户填写。

## 目录结构（简化）
```text
抖音博主数字永生/
├── src/                 # 核心代码
├── docs/                # 文档
├── skills/              # 生成的 Skill（SKILL.md）
├── output/              # history.json 等状态文件
├── cache/               # 视频/音频/转写缓存（默认）
├── app.py               # Streamlit WebUI
├── main.py              # 命令行入口
├── start.bat / start.sh # 启动脚本
└── README.md
```

## 输出说明

生成完成后主要产物为：
```text
skills/
└── blogger-<博主名slug>-v<version>/
    └── SKILL.md
```

运行状态与历史记录：
```text
output/
└── history.json
```

缓存目录（可随时删除以释放空间，下次会重新下载/转写）：
```text
cache/
├── videos/
└── audio/
```

## 故障排查

### 问题 1：`ffmpeg: command not found`
安装 ffmpeg 并加入 PATH 后重试。

### 问题 2：提示抖音 Cookie 无效/为空
在 WebUI 侧边栏粘贴浏览器 `Cookie:` 的完整内容（建议从抖音网页任意请求的 Request Headers 复制）。

### 问题 3：AUC 报错（授权/资源不匹配）
确认使用的是 AUC 标准版的 `x-api-key`，并确认资源已开通。出现 `X-Tt-Logid` 时可用于控制台定位。

### 问题 4：方舟接口 404 / 模型无权限
确认模型名（例如 `doubao-seed-2-0-lite-260215`）已在控制台开通可用。

### 问题 5：生成过程中网络超时
可能与本机代理/TUN 有关，可关闭全局代理后重试，或在网络更稳定环境运行。

## 日志

- Web UI 日志：`app.log`
- CLI 日志：`main.log`

## 合规声明

本工具仅用于个人学习与研究用途。用户使用本工具产生的一切法律责任由用户本人承担，并需确保不侵犯任何第三方合法权益。
