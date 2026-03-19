from typing import Literal, Optional
import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services import project_store
from ..services.context import build_context
from ..services.prompt_builder import (
    build_story_prompts,
    StyleConfig,
    ModeType,
)
from ..services.llm_adapter import LLMAdapter
from ..services.memory_manager import maybe_refresh_memory_summary
from .. import config as app_config


router = APIRouter()

# request_id -> asyncio.Event：用于中断某次 SSE 续写
_cancel_events: dict[str, asyncio.Event] = {}


class WriteRequest(BaseModel):
    project_id: str
    style_id: str
    mode: Literal["chapter", "ending"] = "chapter"
    max_tokens: Optional[int] = None
    user_note: Optional[str] = None


def _get_style(style_id: str) -> StyleConfig:
    styles: dict[str, StyleConfig] = {
        "happy": {
            "id": "happy",
            "name": "圆满",
            "style_prompt": "结局积极、团圆、矛盾化解、善有善报，可以保留少量遗憾但整体温暖乐观。",
        },
        "tragic": {
            "id": "tragic",
            "name": "悲剧",
            "style_prompt": "充满遗憾与牺牲，强调命运感和不可逆的失去，整体基调偏悲凉。",
        },
        "open": {
            "id": "open",
            "name": "开放式",
            "style_prompt": "保留关键悬念与多种可能，不给出唯一解释，让读者自行想象后续。",
        },
        "mystery": {
            "id": "mystery",
            "name": "悬疑",
            "style_prompt": "重点收束谜题与线索，允许有反转或揭示，但要尽量保证逻辑可追溯；结尾带着仍可咀嚼的余味。",
        },
        "thriller": {
            "id": "thriller",
            "name": "惊悚",
            "style_prompt": "紧张、压迫与不安感贯穿；保留适度悬念，但结尾需要让氛围收住；允许轻微恐怖元素与心理冲击。",
        },
        "healing": {
            "id": "healing",
            "name": "治愈",
            "style_prompt": "以和解与成长为核心，情绪从低谷回暖；结尾温柔、克制、充满希望与修复感。",
        },
        "bittersweet": {
            "id": "bittersweet",
            "name": "苦甜",
            "style_prompt": "结尾甜中带苦：重要关系得到确认或重建，但仍留下可被记住的小伤口与余韵；整体更偏温柔遗憾。",
        },
        "growth": {
            "id": "growth",
            "name": "成长",
            "style_prompt": "强调角色的变化与自我觉醒；结尾体现选择与代价，给出更成熟的方向感；氛围偏坚定、清亮。",
        },
    }
    if style_id not in styles:
        return styles["happy"]
    return styles[style_id]


def _get_llm_adapter() -> LLMAdapter:
    """
    从 data/config.json + 环境变量 组合读取配置，实例化 LLM 适配器。
    JSON 优先，环境变量可覆盖。
    """
    cfg = app_config.load_config()
    if not cfg.api_key:
        raise RuntimeError("LLM API Key 未配置，请在 data/config.json 或环境变量中设置。")

    adapter = LLMAdapter(provider=cfg.provider, api_key=cfg.api_key, api_base=cfg.api_base)
    model = cfg.model or "gpt-4.1"
    adapter._default_model = model  # type: ignore[attr-defined]
    return adapter


@router.post("/write", response_model=dict)
def start_write(req: WriteRequest) -> dict:
    """
    非流式接口：仅用于前端拿到 task 信息。
    目前简单返回参数本身，真正内容由 /stream/write 输出。
    """
    project = project_store.get_project(req.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    next_index = len(project.chapters) + 1
    return {
        "project_id": project.id,
        "next_chapter_index": next_index,
        "mode": req.mode,
        "style_id": req.style_id,
    }


@router.get("/stream/write")
async def stream_write(
    project_id: str,
    style_id: str = "happy",
    mode: ModeType = "chapter",
    max_tokens: Optional[int] = None,
    user_note: Optional[str] = None,
    use_long_memory: bool = True,
    request_id: Optional[str] = None,
    chapter_index: Optional[int] = None,
    total_chapters: Optional[int] = None,
    tone: Optional[str] = None,
    is_final_chapter: bool = False,
):
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    cancel_event: Optional[asyncio.Event] = None
    if request_id:
        cancel_event = _cancel_events.get(request_id)
        if cancel_event is None:
            cancel_event = asyncio.Event()
            _cancel_events[request_id] = cancel_event

    # 初始化 LLM 适配器
    adapter = _get_llm_adapter()
    model = getattr(adapter, "_default_model", "gpt-4.1")  # type: ignore[attr-defined]

    memory_summary = project.memory_summary if use_long_memory else ""

    if use_long_memory:
        # 先刷新/生成长期记忆，避免截断后“忘记重要人物/事件”
        try:
            project = await maybe_refresh_memory_summary(
                project=project,
                adapter=adapter,
                model=model,
                recent_chapters_keep=3,
                max_context_chars=8000,
            )
        except Exception:
            # 摘要失败不阻断续写：直接走旧的上下文策略
            pass

        # 重新拉取一次，确保 memory_summary 落盘后能被 build_context 使用
        project = project_store.get_project(project_id) or project
        memory_summary = project.memory_summary if use_long_memory else ""

    style = _get_style(style_id)
    context = build_context(
        {
            "id": project.id,
            "title": project.title,
            "original_text": project.original_text,
            "chapters": [
                {
                    "id": c.id,
                    "index": c.index,
                    "type": c.type,
                    "style_id": c.style_id,
                    "model": c.model,
                    "content": c.content,
                    "created_at": c.created_at,
                }
                for c in project.chapters
            ],
            "memory_summary": memory_summary,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        },
        max_context_chars=8000,
    )
    next_index = len(project.chapters) + 1
    if chapter_index is not None and chapter_index > 0:
        next_index = chapter_index
    prompts = build_story_prompts(
        project={
            "id": project.id,
            "title": project.title,
            "original_text": project.original_text,
            "chapters": [
                {
                    "id": c.id,
                    "index": c.index,
                    "type": c.type,
                    "style_id": c.style_id,
                    "model": c.model,
                    "content": c.content,
                    "created_at": project.created_at,
                }
                for c in project.chapters
            ],
            "memory_summary": memory_summary,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        },
        context=context,
        style=style,
        mode=mode,
        next_chapter_index=next_index,
        user_note=user_note,
        tone=tone,
        total_chapters=total_chapters,
        is_final_chapter=is_final_chapter,
    )

    async def event_generator():
        full_text_chunks: list[str] = []
        cancelled = False
        try:
            async for chunk in adapter.generate_stream(
                model=model,
                system_prompt=prompts["system_prompt"],
                user_prompt=prompts["user_prompt"],
                max_tokens=max_tokens,
            ):
                if cancel_event and cancel_event.is_set():
                    cancelled = True
                    break
                full_text_chunks.append(chunk)
                yield f"event: chunk\ndata: {chunk}\n\n"
        except Exception as exc:  # noqa: BLE001
            # 包装为单行 JSON，避免 SSE 因异常消息里的换行导致解析不完整
            payload: dict[str, object] = {
                "message": str(exc),
                "type": exc.__class__.__name__,
                "repr": repr(exc),
            }
            if request_id:
                _cancel_events.pop(request_id, None)
            # 尽量抓取 SDK 异常体信息（不同 provider 字段不一致，尽量不抛二次异常）
            for key in ("status_code", "code", "body", "response"):
                try:
                    val = getattr(exc, key, None)
                    if val is not None:
                        if key == "body" and isinstance(val, (bytes, bytearray)):
                            payload[key] = val.decode("utf-8", errors="replace")
                        else:
                            payload[key] = val
                except Exception:
                    pass

            yield (
                "event: app_error\n"
                f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            )
            return

        if cancelled:
            if request_id:
                _cancel_events.pop(request_id, None)
            yield (
                "event: cancelled\n"
                f"data: {json.dumps({'message': '已停止续写'}, ensure_ascii=False)}\n\n"
            )
            return

        full_text = "".join(full_text_chunks)
        chapter_type = "ending" if (is_final_chapter or mode == "ending") else "normal"
        updated_project = project_store.add_chapter(
            project_id=project.id,
            content=full_text,
            style_id=style_id,
            model=model,
            chapter_type=chapter_type,
        )
        chapter_id = (
            updated_project.chapters[-1].id if updated_project and updated_project.chapters else ""
        )
        yield (
            "event: end\n"
            f"data: {json.dumps({'project_id': project.id, 'chapter_id': chapter_id, 'mode': mode}, ensure_ascii=False)}\n\n"
        )

        if request_id:
            _cancel_events.pop(request_id, None)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/stream/cancel")
async def cancel_stream(request_id: str):
    """
    通知后端停止指定 request_id 的 SSE 续写。
    """
    ev = _cancel_events.get(request_id)
    if not ev:
        raise HTTPException(status_code=404, detail="request_id not found")
    ev.set()
    return {"ok": True}

