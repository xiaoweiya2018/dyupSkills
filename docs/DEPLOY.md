# 部署手册

## 环境要求

### 系统要求
- Python 3.9+
- ffmpeg（必须安装并添加到PATH）
- 网络连接（访问OpenAI API）

### 依赖软件
1. **ffmpeg** - 音频提取必需
   - Windows: 下载ffmpeg并将bin目录添加到PATH
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`

2. **Python包** - 见 `requirements.txt`

---

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

### 4. 验证ffmpeg
```bash
ffmpeg -version
```
如果输出版本信息，说明安装成功。

---

## 运行方式

### 方式一：Web界面（推荐）

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

启动后，浏览器会自动打开 `http://localhost:8501`

### 方式二：命令行

```bash
# 基本用法
python main.py -i https://www.douyin.com/user/xxxxxxxxxx -k your-openai-api-key

# 指定输出目录
python main.py -i xxxxxxx -k yyyy -o ./myoutput -c ./mycache

# 使用环境变量
export OPENAI_API_KEY=your-key
python main.py -i https://www.douyin.com/user/xxxxxxxxxx
```

**命令行参数:**
```
-i, --input      博主链接或ID (必填)
-k, --api-key    OpenAI API Key
-u, --base-url   OpenAI Base URL (可选)
-o, --output-dir 输出目录 (默认: ./output)
-c, --cache-dir  缓存目录 (默认: ./cache)
-m, --max-videos 最大视频数 (默认: 10)
--min-videos     最少合格视频数 (默认: 5)
--log-level      日志级别 (默认: INFO)
```

---

## 配置说明

### 配置方式
1. **Web界面** - 在侧边栏填写配置后点击"保存配置"
2. **环境变量**
   ```bash
   export OPENAI_API_KEY=your-api-key
   export OPENAI_BASE_URL=https://your-proxy-url/v1  # 可选
   ```
3. **配置文件** - 配置保存在 `.env.json`

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `openai_api_key` | OpenAI API Key | 必须 |
| `openai_base_url` | 自定义API地址（代理用） | None |
| `max_videos` | 最大抓取视频数 | 10 |
| `min_videos_required` | 最少合格视频才能生成 | 5 |
| `max_chars_per_video` | 单视频最大字符数 | 1000 |
| `max_total_chars` | 总字符数限制 | 5000 |
| `output_dir` | 输出目录 | `./output` |
| `cache_dir` | 缓存目录 | `./cache` |

---

## 目录结构

```
抖音博主数字永生/
├── src/                    # 源代码
│   ├── __init__.py
│   ├── models.py          # 数据模型
│   ├── downloader.py      # 视频下载
│   ├── audio.py           # 音频提取
│   ├── transcriber.py     # 语音转写
│   ├── filter.py          # 数据过滤
│   ├── safety.py          # 内容安全
│   ├── prompts.py         # Prompt模板
│   ├── ai_generator.py    # AI生成
│   ├── exporter.py        # 结果导出
│   ├── storage.py         # 存储管理
│   └── engine.py          # 主引擎
├── tests/                  # 单元测试
├── docs/                   # 文档
│   ├── API.md             # API文档
│   └── DEPLOY.md          # 部署手册
├── app.py                 # Streamlit Web入口
├── main.py                # 命令行入口
├── requirements.txt       # 依赖列表
├── pyproject.toml         # poetry配置
├── start.bat              # Windows启动脚本
├── start.sh               # Linux/macOS启动脚本
├── .gitignore
└── README.md
```

---

## 输出说明

生成完成后，会在输出目录生成以下文件：

```
output/
├── history.json                  # 历史记录
├── BloggerName_bloggerid_timestamp_full.json
│                                # 完整结果（包含所有中间数据）
├── BloggerName_bloggerid_timestamp_skill.json
│                                # 仅Skill JSON（可直接导入OpenClaw）
├── BloggerName_bloggerid_timestamp.md
│                                # Markdown可读文档
└── BloggerName_bloggerid_timestamp_system.txt
                                 # 纯System Prompt文本
```

---

## 成本估算

| 步骤 | 成本（美元） |
|------|-------------|
| Whisper转写 (10个视频，平均1分钟/个) | ~ $0.09 |
| GPT-4 博主画像 | ~ $0.01-0.05 |
| GPT-4 风格规则 | ~ $0.01-0.05 |
| GPT-4 Skill生成 | ~ $0.05-0.15 |
| GPT-4 评分 | ~ $0.01-0.03 |
| **总计** | **~ $0.17-0.37** |

> 10个视频全流程大约 **0.2-0.4美元**，价格仅供参考，实际以OpenAI收费为准。

---

## 故障排查

### 问题1: `ffmpeg: command not found`
**解决:** 安装ffmpeg并添加到PATH

### 问题2: 下载视频失败
**可能原因:**
- 抖音反爬，需要cookie
- 网络问题

**解决:**
yt-dlp可能需要配置cookie。可以通过浏览器开发者工具获取cookie。

### 问题3: OpenAI API报错
**检查:**
1. API Key是否正确
2. 余额是否充足
3. 网络是否能访问OpenAI

如果使用代理，需要配置 `openai_base_url`

### 问题4: 生成失败，提示"合格视频不足"
**解决:**
- 博主可能大部分视频都是纯音乐
- 换一个博主试试
- 可以尝试降低 `min_videos_required`

### 问题5: Streamlit端口被占用
**解决:**
```bash
streamlit run app.py --server.port 8502
```

---

## 监控与日志

- Web UI运行日志: `app.log`
- 命令行运行日志: `main.log`
- 日志自动轮转，单个文件最大10MB

---

## 性能优化建议

1. **缓存利用** - 已下载的视频和转写结果会缓存，重复生成不会重复收费
2. **控制视频数量** - 推荐5-10个视频足够，更多视频增加成本但提升有限
3. **代理加速** - 如果网络慢，使用代理或自定义API地址
4. **清理缓存** - 定期删除 `cache/` 目录释放空间

---

## 合规声明

> 本工具仅用于个人学习与研究用途。
> 用户基于本工具生成的内容所产生的一切法律责任，由用户本人承担，与本工具开发者无关。
> 用户需确保不侵犯任何第三方（包括但不限于内容创作者、平台方）的合法权益。
