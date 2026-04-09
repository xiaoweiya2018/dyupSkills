"""
Prompt模板 - 按照rompt模板.md实现
"""

from typing import List


class Prompts:
    """Prompt模板集合"""

    @staticmethod
    def blogger_profile_extraction(transcripts: str) -> str:
        """Step1: 博主画像提取 Prompt"""
        return f"""你是一个专业的内容分析专家，请基于以下多段视频转写内容，对该抖音博主进行深度分析。

【输入内容】
{transcripts}

请输出以下内容：
1. 内容领域（如：科技 / 情感 / 商业 / 娱乐）
2. 核心主题（列出3-5个）
3. 表达风格（如：理性分析 / 情绪输出 / 幽默 / 教学型）
4. 语气特点（如：犀利 / 平和 / 激进 / 洗脑式）
5. 人设标签（3-5个）
6. 常用表达 / 口头禅（尽量具体）
7. 目标受众（如：年轻人 / 打工人 / 创业者）

要求：
- 必须基于内容推断，不允许编造
- 输出结构清晰
- 用简洁中文表达
- 请以JSON格式输出，key为：
{{
  "content_field": "...",
  "core_topics": [...],
  "expression_style": "...",
  "tone_characteristic": "...",
  "persona_tags": [...],
  "common_phrases": [...],
  "target_audience": "..."
}}
"""

    @staticmethod
    def style_modeling(transcripts: str, profile_json: str) -> str:
        """Step2: 风格建模 Prompt"""
        return f"""你现在需要"模仿该博主的说话方式"。

以下是该博主的视频内容转写：
{transcripts}

以下是博主画像：
{profile_json}

请总结该博主的"表达风格规则"，用于后续AI模仿：

请输出：
1. 说话结构（例如：先抛观点 → 举例 → 总结）
2. 语言特点（是否口语化、是否使用短句、是否重复强调）
3. 情绪强度（低 / 中 / 高）
4. 是否使用修辞（比喻、反问、夸张等）
5. 典型句式（请生成5句"像他会说的话"）

要求：
- 必须高度贴近原内容
- 不要泛泛而谈
- 输出可用于AI模仿
- 请以JSON格式输出，key为：
{{
  "speech_structure": "...",
  "language_features": "...",
  "emotion_intensity": "...",
  "uses_rhetoric": true/false,
  "typical_sentences": [...]
}}
"""

    @staticmethod
    def skill_generation(profile_json: str, style_rules_json: str, transcripts: str) -> str:
        """Step3: Skill生成 Prompt"""
        return f"""你是一个OpenClaw Skill设计专家。

请基于以下信息，生成一个完整的AI Skill，使其能够在对话中"像该博主一样说话，同时提供有价值的内容"。

【输入数据】

博主画像：
{profile_json}

风格规则：
{style_rules_json}

视频内容摘要：
{transcripts}

请输出一个Skill，严格使用以下JSON格式：
{{
  "name": "",
  "description": "",
  "persona": {{
    "style": "",
    "tone": "",
    "tags": []
  }},
  "triggers": [],
  "system_prompt": "",
  "examples": [
    {{
      "user": "",
      "assistant": ""
    }},
    {{
      "user": "",
      "assistant": ""
    }},
    {{
      "user": "",
      "assistant": ""
    }}
  ]
}}

生成要求：
1. Skill名称：
- 简洁、有辨识度
- 体现博主特点

2. description：
- 说明这个Skill能做什么

3. persona：
- 必须体现风格、人设

4. triggers：
- 生成3-5个触发词

5. system_prompt（最重要）：
- 明确规定AI的说话方式
- 必须包含：语气、风格、禁止行为（如：不要胡编）
- 一定要强调：像原博主说话，不要官方化

6. examples：
- 至少3组对话
- 必须"像这个博主说话"
- 不能太官方

重要限制：
- 不要编造不存在的信息
- 保持风格一致
- 优先模仿语气，而不是复述内容
"""

    @staticmethod
    def skill_evaluation(skill_json: str) -> str:
        """Step4: Skill评分 Prompt"""
        return f"""请你评估以下Skill质量：

{skill_json}

从以下维度打分（0-1，分数越高越好）：
1. 纯度（是否像单一人物）
2. 可信度（是否胡编）
3. 风格还原度（是否像原博主）
4. 可用性（是否适合对话）

请输出严格JSON格式：
{{
  "purity": 0.0,
  "consistency": 0.0,
  "style": 0.0,
  "usability": 0.0,
  "reason": ""
}}
"""

    @staticmethod
    def content_safety_check(text: str) -> str:
        """Step5: 内容安全检测 Prompt"""
        return f"""请判断以下内容是否存在风险：

{text}

检测维度：
- 攻击性语言
- 低俗内容
- 不当价值观

请输出严格JSON格式：
{{
  "risk": true/false,
  "type": "",
  "reason": ""
}}
"""

    @staticmethod
    def truncate_transcripts(transcripts: List[str], max_total_chars: int) -> str:
        """截断并合并转写文本"""
        combined = []
        total_length = 0
        for t in transcripts:
            if total_length + len(t) > max_total_chars:
                remaining = max_total_chars - total_length
                if remaining > 100:
                    combined.append(t[:remaining])
                break
            combined.append(t)
            total_length += len(t)
        return "\n\n---\n\n".join(combined)
