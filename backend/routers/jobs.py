from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.video import Video, Job
from models.settings import get_or_create_settings

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
@router.get("/")
def list_jobs(db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .order_by(Job.started_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": j.id,
            "video_id": j.video_id,
            "step": j.step,
            "status": j.status,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            "log": j.log[:500] if j.log else None,
        }
        for j in jobs
    ]


@router.get("/{id}/logs")
def get_job_logs(id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.id,
        "step": job.step,
        "status": job.status,
        "log": job.log,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
