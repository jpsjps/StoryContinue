from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .routes import write, projects


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def create_app() -> FastAPI:
    app = FastAPI(title="StoryContinue", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
    app.include_router(write.router, prefix="/api", tags=["write"])

    # 静态资源与首页
    if FRONTEND_DIR.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(FRONTEND_DIR), html=False),
            name="static",
        )

        @app.get("/", response_class=HTMLResponse)
        async def index() -> HTMLResponse:  # type: ignore[func-returns-value]
            index_path = FRONTEND_DIR / "index.html"
            if not index_path.exists():
                return HTMLResponse("index.html 不存在", status_code=500)
            content = index_path.read_text(encoding="utf-8")
            return HTMLResponse(content)

    return app


app = create_app()
