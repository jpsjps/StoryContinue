import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from uuid import uuid4


DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "projects"
DATA_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class Chapter:
    id: str
    index: int
    type: str  # "normal" | "ending"
    style_id: str
    model: str
    content: str
    created_at: str


@dataclass
class Project:
    id: str
    title: str
    original_text: str
    chapters: List[Chapter]
    # 长期记忆摘要：当上下文很长时，替代“丢掉旧内容”导致的遗忘
    created_at: str
    updated_at: str
    memory_summary: str = ""
    memory_updated_at: str = ""


def _project_path(project_id: str) -> Path:
    return DATA_DIR / f"{project_id}.json"


def list_projects() -> List[Project]:
    projects: List[Project] = []
    for file in DATA_DIR.glob("*.json"):
        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        chapters = [Chapter(**c) for c in data.get("chapters", [])]
        projects.append(
            Project(
                id=data["id"],
                title=data["title"],
                original_text=data.get("original_text", ""),
                chapters=chapters,
                memory_summary=data.get("memory_summary", ""),
                memory_updated_at=data.get("memory_updated_at", ""),
                created_at=data["created_at"],
                updated_at=data["updated_at"],
            )
        )
    return sorted(projects, key=lambda p: p.updated_at, reverse=True)


def get_project(project_id: str) -> Optional[Project]:
    path = _project_path(project_id)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    chapters = [Chapter(**c) for c in data.get("chapters", [])]
    return Project(
        id=data["id"],
        title=data["title"],
        original_text=data.get("original_text", ""),
        chapters=chapters,
        memory_summary=data.get("memory_summary", ""),
        memory_updated_at=data.get("memory_updated_at", ""),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def save_project(project: Project) -> None:
    path = _project_path(project.id)
    data = asdict(project)
    data["chapters"] = [asdict(c) for c in project.chapters]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_project(title: str, original_text: str) -> Project:
    now = datetime.utcnow().isoformat()
    project = Project(
        id=str(uuid4()),
        title=title,
        original_text=original_text,
        chapters=[],
        memory_summary="",
        memory_updated_at="",
        created_at=now,
        updated_at=now,
    )
    save_project(project)
    return project


def update_project(
    project_id: str,
    title: Optional[str] = None,
    original_text: Optional[str] = None,
) -> Optional[Project]:
    project = get_project(project_id)
    if not project:
        return None
    if title is not None:
        project.title = title
    if original_text is not None:
        project.original_text = original_text
    project.updated_at = datetime.utcnow().isoformat()
    save_project(project)
    return project


def delete_project(project_id: str) -> bool:
    path = _project_path(project_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def add_chapter(
    project_id: str,
    *,
    content: str,
    style_id: str,
    model: str,
    chapter_type: str = "normal",
) -> Optional[Project]:
    project = get_project(project_id)
    if not project:
        return None
    next_index = len(project.chapters) + 1
    now = datetime.utcnow().isoformat()
    chapter = Chapter(
        id=str(uuid4()),
        index=next_index,
        type=chapter_type,
        style_id=style_id,
        model=model,
        content=content,
        created_at=now,
    )
    project.chapters.append(chapter)
    project.updated_at = now
    save_project(project)
    return project


def truncate_chapters_from_index(
    project_id: str,
    *,
    from_index: int,
    clear_memory: bool = True,
) -> Optional[Project]:
    """
    从指定章节 index 开始（包含该章）截断后续章节：
    - 保留 index < from_index 的章节
    - 删除 index >= from_index 的所有章节
    - 可选清空长期记忆摘要，避免重写后摘要不一致
    """
    project = get_project(project_id)
    if not project:
        return None
    if from_index <= 1:
        project.chapters = []
    else:
        project.chapters = [c for c in project.chapters if c.index < from_index]

    project.updated_at = datetime.utcnow().isoformat()
    if clear_memory:
        project.memory_summary = ""
        project.memory_updated_at = ""

    save_project(project)
    return project


def set_project_memory_summary(
    project_id: str,
    *,
    memory_summary: str,
) -> Optional[Project]:
    project = get_project(project_id)
    if not project:
        return None
    project.memory_summary = memory_summary
    project.memory_updated_at = datetime.utcnow().isoformat()
    project.updated_at = project.memory_updated_at
    save_project(project)
    return project

