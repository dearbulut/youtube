import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.video import Video, Job
from models.settings import get_or_create_settings
from pipeline.orchestrator import run_short_pipeline, run_long_pipeline

router = APIRouter(prefix="/videos", tags=["videos"])


def video_to_dict(video: Video) -> dict:
    return {
        "id": video.id,
        "type": video.type,
        "status": video.status,
        "title": video.title,
        "youtube_id": video.youtube_id,
        "youtube_url": video.youtube_url,
        "thumbnail_path": video.thumbnail_path,
        "duration_seconds": video.duration_seconds,
        "cost_usd": video.cost_usd,
        "created_at": video.created_at.isoformat() if video.created_at else None,
        "uploaded_at": video.uploaded_at.isoformat() if video.uploaded_at else None,
        "views": video.views,
    }


def job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "step": job.step,
        "status": job.status,
        "log": job.log,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


@router.get("")
@router.get("/")
def list_videos(
    page: int = 1,
    per_page: int = 20,
    type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Video)

    if type is not None:
        query = query.filter(Video.type == type)
    if status is not None:
        query = query.filter(Video.status == status)
    if date_from is not None:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.filter(Video.created_at >= dt_from)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format")
    if date_to is not None:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.filter(Video.created_at <= dt_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format")

    total = query.count()
    pages = max(1, (total + per_page - 1) // per_page)
    videos = (
        query.order_by(Video.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return {
        "videos": [video_to_dict(v) for v in videos],
        "total": total,
        "page": page,
        "pages": pages,
    }


@router.get("/{id}")
def get_video(id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    data = video_to_dict(video)
    jobs = db.query(Job).filter(Job.video_id == id).order_by(Job.started_at.asc()).all()
    data["jobs"] = [
        {
            "id": j.id,
            "step": j.step,
            "status": j.status,
            "log": j.log,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
        }
        for j in jobs
    ]
    return data


@router.post("/{id}/retry")
async def retry_video(id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != "failed":
        raise HTTPException(
            status_code=400, detail="Video is not in failed state"
        )

    video.status = "pending"
    video.error_message = None
    db.commit()

    video_id = video.id
    video_type = video.type

    if video_type == "short":
        asyncio.create_task(run_short_pipeline(video_id))
    else:
        asyncio.create_task(run_long_pipeline(video_id))

    return {"status": "retrying", "video_id": id}


@router.delete("/{id}")
def delete_video(id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    db.delete(video)
    db.commit()
    return {"status": "deleted"}


@router.post("/trigger/short")
async def trigger_short(db: Session = Depends(get_db)):
    app_settings = get_or_create_settings(db)

    if hasattr(app_settings, "daily_budget_usd") and hasattr(app_settings, "spent_today_usd"):
        if app_settings.spent_today_usd >= app_settings.daily_budget_usd:
            raise HTTPException(status_code=400, detail="Daily budget exceeded")

    asyncio.create_task(run_short_pipeline())
    return {"status": "triggered", "message": "Short video pipeline started"}


@router.post("/trigger/long")
async def trigger_long(db: Session = Depends(get_db)):
    app_settings = get_or_create_settings(db)

    if hasattr(app_settings, "daily_budget_usd") and hasattr(app_settings, "spent_today_usd"):
        if app_settings.spent_today_usd >= app_settings.daily_budget_usd:
            raise HTTPException(status_code=400, detail="Daily budget exceeded")

    asyncio.create_task(run_long_pipeline())
    return {"status": "triggered", "message": "Long video pipeline started"}
