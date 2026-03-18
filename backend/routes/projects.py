from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services import project_store


router = APIRouter()


class ChapterOut(BaseModel):
    id: str
    index: int
    type: str
    style_id: str
    model: str
    content: str
    created_at: str


class ProjectOut(BaseModel):
    id: str
    title: str
    original_text: str
    chapters: List[ChapterOut]
    created_at: str
    updated_at: str


class ProjectSummaryOut(BaseModel):
    id: str
    title: str
    chapter_count: int
    created_at: str
    updated_at: str


class ProjectCreateIn(BaseModel):
    title: str
    original_text: str


class ProjectUpdateIn(BaseModel):
    title: Optional[str] = None
    original_text: Optional[str] = None


class TruncateChaptersIn(BaseModel):
    from_index: int  # 删除/截断从该章开始（包含该章）


@router.get("", response_model=List[ProjectSummaryOut])
def list_projects() -> List[ProjectSummaryOut]:
    projects = project_store.list_projects()
    return [
        ProjectSummaryOut(
            id=p.id,
            title=p.title,
            chapter_count=len(p.chapters),
            created_at=p.created_at,
            updated_at=p.updated_at,
        )
        for p in projects
    ]


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreateIn) -> ProjectOut:
    project = project_store.create_project(
        title=payload.title,
        original_text=payload.original_text,
    )
    return ProjectOut(
        id=project.id,
        title=project.title,
        original_text=project.original_text,
        chapters=[
            ChapterOut(**c.__dict__) for c in project.chapters
        ],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str) -> ProjectOut:
    project = project_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut(
        id=project.id,
        title=project.title,
        original_text=project.original_text,
        chapters=[
            ChapterOut(**c.__dict__) for c in project.chapters
        ],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdateIn) -> ProjectOut:
    project = project_store.update_project(
        project_id,
        title=payload.title,
        original_text=payload.original_text,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectOut(
        id=project.id,
        title=project.title,
        original_text=project.original_text,
        chapters=[
            ChapterOut(**c.__dict__) for c in project.chapters
        ],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.delete("/{project_id}")
def delete_project(project_id: str) -> dict:
    ok = project_store.delete_project(project_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


@router.post("/{project_id}/chapters/truncate")
def truncate_chapters(project_id: str, payload: TruncateChaptersIn) -> dict:
    """
    删除指定章节及其后续所有章节。
    用于“删除章节/重写章节”。
    """
    updated = project_store.truncate_chapters_from_index(
        project_id,
        from_index=payload.from_index,
        clear_memory=True,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True, "chapter_count": len(updated.chapters)}

