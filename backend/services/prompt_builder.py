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


def _build_goal_block(
    mode: ModeType,
    next_chapter_index: int,
    total_chapters: Optional[int] = None,
    is_final_chapter: bool = False,
) -> str:
    progress_desc = f"第 {next_chapter_index} 章"
    if total_chapters is not None and total_chapters > 0:
        progress_desc += f"（本次共 {total_chapters} 章）"

    if is_final_chapter or mode == "ending":
        return f"""
- 现在请你创作「故事的最终结局章节」（{progress_desc} 或尾声）。
- 在本章内完整收束故事的主要矛盾和人物关系。
- 不要再为后续章节刻意铺垫，本章结束后可以视为整部故事已经结束。
""".strip()

    return f"""
- 现在请你续写「{progress_desc}」的内容，而不是总结。
- 本章需要自然承接上述剧情，继续推动故事发展。
- 保持人物行为和事件逻辑自洽，不要突然引入完全无关的新设定（除非非常必要）。
- 本章不需要结束整部故事，可以适度埋下伏笔。
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


def _build_tone_block(tone: Optional[str]) -> str:
    if not tone:
        return ""

    tone_list = [t.strip() for t in tone.split(",") if t.strip()]
    tone_prompts = {
        "dramatic": "情节跌宕起伏，增强戏剧张力，多设置转折和冲突",
        "foreshadow": "注意埋下伏笔，为后续剧情做铺垫，设置悬念",
        "smooth": "按正常节奏平稳推进故事，保持叙事流畅",
        "accelerate": "加快故事推进速度，尽快推进核心冲突发展",
    }

    instructions = [tone_prompts.get(t, "") for t in tone_list]
    instructions = [i for i in instructions if i]
    if not instructions:
        return ""
    return f"# 叙事节奏指引\n本章要求：{'；'.join(instructions)}。"


def _build_protagonist_team_block(protagonist_team: Optional[str]) -> str:
    if not protagonist_team:
        return ""

    names = [n.strip() for n in protagonist_team.split(",") if n.strip()]
    if not names:
        return ""
    names_text = "、".join(names)
    return (
        "# 主角团聚焦要求\n"
        f"- 主角团成员：{names_text}。\n"
        "- 本章叙事需围绕主角团展开，关键推进尽量与其行动、关系变化相关。\n"
        "- 同时要加入有存在感的配角/龙套（如路人、同事、店家、同学、邻里等），"
        "通过互动与环境细节增强生活感，不要只让主角自说自话。\n"
        "- 配角可短暂出场，但应对场景气氛、信息传递或冲突推进产生具体作用。"
    )


def build_story_prompts(
    *,
    project: Project,
    context: ContextResult,
    style: StyleConfig,
    mode: ModeType,
    next_chapter_index: int,
    user_note: Optional[str] = None,
    tone: Optional[str] = None,
    protagonist_team: Optional[str] = None,
    total_chapters: Optional[int] = None,
    is_final_chapter: bool = False,
) -> PromptBuildResult:
    system_prompt = _build_system_prompt()
    context_block = _build_context_block(context)
    goal_block = _build_goal_block(mode, next_chapter_index, total_chapters, is_final_chapter)
    style_block = _build_style_block(style, mode)
    user_note_block = _build_user_note_block(user_note)
    tone_block = _build_tone_block(tone)
    protagonist_team_block = _build_protagonist_team_block(protagonist_team)

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
    if tone_block:
        user_prompt_parts.extend(["", tone_block])
    if protagonist_team_block:
        user_prompt_parts.extend(["", protagonist_team_block])
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
        "total_chapters": total_chapters,
        "tone": tone,
        "protagonist_team": protagonist_team,
        "is_final_chapter": is_final_chapter,
    }

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "meta": meta,
    }


def build_humanize_prompts(*, chapter_text: str, style_name: str, tone: Optional[str] = None) -> PromptBuildResult:
    """
    对已生成章节进行二次润色，降低模板化和“AI 腔”。
    必须保留事实与剧情，不得改动关键设定。
    """
    system_prompt = """
你是一名资深中文小说编辑，擅长在不改变剧情事实的前提下润色文本，让表达更自然、更像人类作者手写稿。

# 硬性要求
- 只输出润色后的小说正文，不要解释。
- 不改变人物、事件、时间顺序、核心设定，不新增关键剧情点。
- 降低模板化表达与总结腔，避免说教、口号式结尾。
- 减少抽象判断，多用可感知细节（动作、神态、环境、对话节奏）。
- 句式长短交替，允许适度留白，不要所有段落都“完美闭环”。
- 不得输出违法违规内容。
    """.strip()

    tone_block = _build_tone_block(tone)
    tone_hint = f"\n\n{tone_block}" if tone_block else ""
    user_prompt = (
        f"# 润色目标\n"
        f"- 风格倾向：{style_name}\n"
        f"- 任务：只改表达，不改剧情事实。\n"
        f"{tone_hint}\n\n"
        f"# 待润色正文\n"
        f"{chapter_text.strip()}"
    ).strip()

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "meta": {"task": "humanize_chapter", "style_name": style_name, "tone": tone},
    }

