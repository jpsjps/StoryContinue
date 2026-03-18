from typing import TypedDict, Optional, Literal, Dict

from .context import Project, ContextResult

ModeType = Literal["chapter", "ending"]


class StyleConfig(TypedDict):
    id: str
    name: str
    style_prompt: str


class PromptBuildResult(TypedDict):
    system_prompt: str
    user_prompt: str
    meta: Dict[str, object]


def _build_system_prompt() -> str:
    return """
你是一名专业的网络小说作者，擅长根据已有剧情进行连贯的续写。

# 写作要求（通用）
- 保持人物性格、世界观和叙事逻辑的一致性。
- 文字风格贴近原文，尽量自然流畅，不要突然改变文风。
- 控制节奏：既不要一句话就解决所有冲突，也不要无意义拖长。
- 不要重复大段抄写原文内容，只需自然衔接即可。
- 禁止输出违反相关法律法规的内容，避免过度暴力、血腥、色情等。

# 输出格式
- 只输出小说正文内容，不要解释创作过程，不要加入「作者说」「系统提示」等额外说明。
- 不要输出标题、小结或点评，除非明确要求。
""".strip()


def _build_context_block(context: ContextResult) -> str:
    parts = []
    if context["context_summary"]:
        parts.append("【长期记忆/上下文摘要】\n" + context["context_summary"].strip() + "\n")
    parts.append("【原文与已续写内容（节选）】")
    parts.append(context["truncated_story"])
    return "\n".join(parts)


def _build_goal_block(mode: ModeType, next_chapter_index: int) -> str:
    if mode == "chapter":
        return f"""
- 现在请你续写「第 {next_chapter_index} 章」的内容，而不是总结。
- 本章需要自然承接上述剧情，继续推动故事发展。
- 保持人物行为和事件逻辑自洽，不要突然引入完全无关的新设定（除非非常必要）。
- 本章不需要结束整部故事，可以适度埋下伏笔。
""".strip()
    return f"""
- 现在请你创作「故事的最终结局章节」（第 {next_chapter_index} 章或尾声）。
- 在本章内完整收束故事的主要矛盾和人物关系。
- 不要再为后续章节刻意铺垫，本章结束后可以视为整部故事已经结束。
""".strip()


def _build_style_block(style: StyleConfig, mode: ModeType) -> str:
    if mode == "ending":
        extra = "\n- 本章必须清晰体现上述结局风格，让读者在结尾时明显感受到这种氛围。"
    else:
        extra = "\n- 本章可以为这种结局风格埋下伏笔，但不要过早结束故事。"
    return f"结局/风格设定：{style['name']}\n{style['style_prompt']}{extra}"


def _build_user_note_block(user_note: Optional[str]) -> str:
    if not user_note:
        return ""
    return f"# 用户补充说明（请优先考虑）\n{user_note.strip()}"


def build_story_prompts(
    *,
    project: Project,
    context: ContextResult,
    style: StyleConfig,
    mode: ModeType,
    next_chapter_index: int,
    user_note: Optional[str] = None,
) -> PromptBuildResult:
    system_prompt = _build_system_prompt()
    context_block = _build_context_block(context)
    goal_block = _build_goal_block(mode, next_chapter_index)
    style_block = _build_style_block(style, mode)
    user_note_block = _build_user_note_block(user_note)

    user_prompt_parts = [
        "# 故事背景与已发生剧情（请充分理解）",
        context_block,
        "",
        "# 本次写作目标",
        goal_block,
        "",
        "# 结局风格指引",
        style_block,
    ]
    if user_note_block:
        user_prompt_parts.extend(["", user_note_block])

    user_prompt = "\n".join(p for p in user_prompt_parts if p.strip())

    meta = {
        "project_id": project["id"],
        "project_title": project["title"],
        "mode": mode,
        "style_id": style["id"],
        "style_name": style["name"],
        "chapter_index": next_chapter_index,
    }

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "meta": meta,
    }

