from __future__ import annotations

from typing import Optional

from .llm_adapter import LLMAdapter
from . import project_store


async def maybe_refresh_memory_summary(
    *,
    project: project_store.Project,
    adapter: LLMAdapter,
    model: str,
    recent_chapters_keep: int = 3,
    max_context_chars: int = 8000,
    refresh_every_n_chapters: int = 4,
    max_memory_chars: int = 2000,
) -> project_store.Project:
    """
    生成/刷新“长期记忆摘要”，用来避免截断上下文后遗忘关键人物与事件。

    触发策略（尽量少打断用户体验）：
    - 还没有 memory_summary：生成一次
    - 否则，当章节数达到 refresh_every_n_chapters 的倍数，或上下文明显超长时刷新
    """

    total_len = len(project.original_text or "") + sum(len(c.content or "") for c in project.chapters)
    has_memory = bool(project.memory_summary)

    should_refresh = False
    if not has_memory:
        should_refresh = True
    else:
        if len(project.chapters) % max(refresh_every_n_chapters, 1) == 0:
            should_refresh = True
        elif total_len > max_context_chars * 1.2:
            should_refresh = True

    if not should_refresh:
        return project

    recent_chapters_keep = max(0, min(recent_chapters_keep, len(project.chapters)))
    old_chapters = project.chapters[: len(project.chapters) - recent_chapters_keep]
    if not old_chapters:
        old_chapters = project.chapters

    story_excerpt = project.original_text + "\n\n" + "\n\n".join(
        c.content or "" for c in old_chapters
    )

    # 压缩：避免摘要输入过长（同时尽量覆盖“需要记住”的旧部分）
    story_excerpt = story_excerpt[: max_context_chars * 2]

    system_prompt = (
        "你是一名资深小说编辑。你需要从给定的小说内容中提取“长期记忆”，"
        "用于后续续写时保持人物关系、世界设定和关键事件不被遗忘。"
    )
    user_prompt = (
        "请阅读以下文本，提取并总结：\n"
        "1）关键人物与关系：用要点列出人物/称呼与其关系（尽量不编造）。\n"
        "2）世界观/规则/设定：用要点列出重要设定与约束。\n"
        "3）关键事件与未解矛盾：按时间顺序列出发生过的重大事件，以及目前仍悬而未决的矛盾/目标。\n\n"
        "要求：\n"
        "- 输出只包含上述三部分，不要额外解释。\n"
        f"- 总长度控制在不超过 {max_memory_chars} 中文字符。\n"
        "- 不要复述全文，重点放在“要记住的事实”。\n\n"
        f"【待提取文本】\n{story_excerpt}"
    )

    memory_text = await adapter.generate_text(
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_tokens=700,
        temperature=0.2,
    )

    memory_text = memory_text.strip()[:max_memory_chars]
    updated = project_store.set_project_memory_summary(
        project.id,
        memory_summary=memory_text,
    )
    return updated or project

