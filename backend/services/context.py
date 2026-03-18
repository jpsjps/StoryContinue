from typing import TypedDict, List
from datetime import datetime


class Chapter(TypedDict):
    id: str
    index: int
    type: str  # "normal" | "ending"
    style_id: str
    model: str
    content: str
    created_at: datetime


class Project(TypedDict):
    id: str
    title: str
    original_text: str
    chapters: List[Chapter]
    # 可选：长期记忆摘要，替代丢弃旧内容带来的遗忘
    memory_summary: str
    created_at: datetime
    updated_at: datetime


class ContextResult(TypedDict):
    truncated_story: str
    context_summary: str


def build_context(project: Project, max_context_chars: int = 8000) -> ContextResult:
    """
    Very simple context strategy:
    - If total length within limit: use full original + all chapters
    - Else:
      * Keep recent few chapters in full
      * Keep head and middle slices from earlier content
    """

    original = project.get("original_text", "")
    chapters = sorted(project.get("chapters", []), key=lambda c: c["index"])

    memory_summary = project.get("memory_summary", "") or ""

    if not chapters:
        if len(original) <= max_context_chars:
            return {"truncated_story": original, "context_summary": ""}

        head = original[:3000]
        mid_start = max(len(original) // 2 - 500, 0)
        mid = original[mid_start : mid_start + 1000]
        truncated = f"【故事开头节选】\n{head}\n\n【故事中段节选】\n{mid}"
        summary = "原文篇幅较长，这里只保留了故事的开端和中段节选供参考。"
        return {"truncated_story": truncated, "context_summary": summary}

    chapters_text = "\n\n".join(c["content"] for c in chapters)
    full = f"{original}\n\n{chapters_text}"

    if len(full) <= max_context_chars:
        # 不需要截断时，不额外塞摘要，避免重复占用上下文
        return {"truncated_story": full, "context_summary": ""}

    m = 3
    recent = chapters[-m:]
    recent_text = "\n\n".join(c["content"] for c in recent)

    old_text = f"{original}\n\n" + "\n\n".join(c["content"] for c in chapters[:-m])
    head = old_text[:2000]
    mid_start = max(len(old_text) // 2 - 500, 0)
    mid = old_text[mid_start : mid_start + 1000]
    partial_old = f"【故事开头与中段节选】\n{head}\n\n{mid}"

    truncated = f"{partial_old}\n\n【最近章节全文】\n{recent_text}"

    if memory_summary:
        # 强制“长期记忆”优先：更能避免模型遗忘关键人物/事件
        return {
            "truncated_story": truncated,
            "context_summary": memory_summary[:2000],
        }

    summary = (
        "原文和前期章节较长，这里只保留了故事的开端节选和最近几章的全文。"
        "续写时请兼顾开端设定与最近剧情的发展。"
    )
    return {"truncated_story": truncated, "context_summary": summary}

