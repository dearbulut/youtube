from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import create_tables
from routers import auth, videos, jobs, settings as settings_router, stats, youtube
from routers.auth import require_app_auth
from scheduler import start_scheduler, stop_scheduler
from config import settings

app = FastAPI(title="TubeAuto API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tube.bulutworks.com", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    create_tables()
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.thumbnail_dir).mkdir(parents=True, exist_ok=True)
    Path("./storage/db").mkdir(parents=True, exist_ok=True)
    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    stop_scheduler()


_auth_dep = [Depends(require_app_auth)]

app.include_router(auth.router)  # public — contains login/status/callback
app.include_router(videos.router, dependencies=_auth_dep)
app.include_router(jobs.router, dependencies=_auth_dep)
app.include_router(settings_router.router, dependencies=_auth_dep)
app.include_router(stats.router, dependencies=_auth_dep)
app.include_router(youtube.router, dependencies=_auth_dep)

app.mount(
    "/storage/thumbnails",
    StaticFiles(directory=settings.thumbnail_dir),
    name="thumbnails",
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
