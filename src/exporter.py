"""
导出模块 - 生成 OpenClaw SKILL.md
"""

import os
import datetime
import hashlib
import re
from loguru import logger
from .models import GenerationResult, Skill


class Exporter:
    """导出器"""

    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
        self.skills_root = os.path.join(self.workspace_root, "skills")
        os.makedirs(self.skills_root, exist_ok=True)

    def _slugify_skill_id(self, raw: str, fallback_seed: str) -> str:
        s = (raw or "").strip().lower()
        s = s.replace("_", "-").replace(" ", "-")
        s = re.sub(r"[^a-z0-9\-]+", "-", s)
        s = re.sub(r"-{2,}", "-", s).strip("-")
        if s:
            return s
        h = hashlib.sha1((fallback_seed or "").encode("utf-8")).hexdigest()[:8]
        return f"skill-{h}"

    def _yaml_quote(self, value: str) -> str:
        v = value if value is not None else ""
        v = str(v)
        if v == "":
            return '""'
        if any(ch in v for ch in [":", "\n", '"', "'", "{", "}", "[", "]", "#"]):
            v = v.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{v}"'
        return v

    def _skill_id_for_result(self, result: GenerationResult) -> str:
        name_part = (result.blogger_name or "").strip()
        seed = f"{name_part}|{result.blogger_id}"
        slug = self._slugify_skill_id(name_part, seed)
        if slug.startswith("skill-"):
            slug = f"name-{slug[6:]}"
        return f"blogger-{slug}-v{result.version}"

    def get_skill_dir(self, result: GenerationResult) -> str:
        skill_id = self._skill_id_for_result(result)
        return os.path.join(self.skills_root, skill_id)

    def get_skill_md_path(self, result: GenerationResult) -> str:
        return os.path.join(self.get_skill_dir(result), "SKILL.md")

    def export_skill_md(self, result: GenerationResult) -> str:
        skill_dir = self.get_skill_dir(result)
        os.makedirs(skill_dir, exist_ok=True)
        output_path = os.path.join(skill_dir, "SKILL.md")
        content = self._generate_skill_md(result)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"导出SKILL.md: {output_path}")
        return output_path

    def export_all(self, result: GenerationResult) -> dict[str, str]:
        skill_md = self.export_skill_md(result)
        return {"skill_md": skill_md, "skill_dir": os.path.dirname(skill_md)}

    def _generate_skill_md(self, result: GenerationResult) -> str:
        skill = result.skill
        skill_id = self._skill_id_for_result(result)
        created_at = result.created_at.strftime("%Y-%m-%d %H:%M:%S")

        frontmatter = "\n".join([
            "---",
            f"name: {self._yaml_quote(skill_id)}",
            f"description: {self._yaml_quote(skill.description)}",
            "version: 1.0.0",
            "user-invocable: true",
            "disable-model-invocation: false",
            f'metadata: {{"blogger_id": {self._yaml_quote(result.blogger_id)}, "blogger_name": {self._yaml_quote(result.blogger_name)}, "created_at": {self._yaml_quote(created_at)}}}',
            "---",
            "",
        ])

        lines: list[str] = []
        lines.append(frontmatter)
        lines.append(f"# {skill.name}")
        lines.append("")
        lines.append("## 功能说明")
        lines.append(skill.description or "")
        lines.append("")
        lines.append("## 触发")
        if skill.triggers:
            for t in skill.triggers:
                lines.append(f"- {t}")
        else:
            lines.append("- （无）")
        lines.append("")
        lines.append("## Persona")
        lines.append(f"- style: {skill.persona.style}")
        lines.append(f"- tone: {skill.persona.tone}")
        lines.append(f"- tags: {', '.join(skill.persona.tags)}" if skill.persona.tags else "- tags: （无）")
        lines.append("")
        lines.append("## System Prompt")
        lines.append("```text")
        lines.append(skill.system_prompt or "")
        lines.append("```")
        lines.append("")
        lines.append("## 示例")
        if skill.examples:
            for i, ex in enumerate(skill.examples, 1):
                lines.append(f"### 示例 {i}")
                lines.append(f"**用户**: {ex.user}")
                lines.append("")
                lines.append(f"**助理**: {ex.assistant}")
                lines.append("")
        else:
            lines.append("（无）")
            lines.append("")
        return "\n".join(lines)
