from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings as app_settings, encrypt_value, decrypt_value, NICHES, COST_CLAUDE_INPUT_PER_MTOK
from database import get_db
from models.video import Video, Job, ChannelStats
from models.settings import UserSettings, get_or_create_settings

router = APIRouter(prefix="/stats", tags=["stats"])


def _next_occurrence(time_str: str, base: Optional[datetime] = None) -> datetime:
    """Return the next datetime for a given HH:MM time string (today or tomorrow)."""
    if base is None:
        base = datetime.utcnow()
    try:
        hour, minute = [int(x) for x in time_str.split(":")]
    except Exception:
        hour, minute = 8, 0
    candidate = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= base:
        candidate += timedelta(days=1)
    return candidate


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today = now.date()

    user_settings = get_or_create_settings(db)

    # today_views
    today_views = (
        db.query(func.coalesce(func.sum(Video.views), 0))
        .filter(
            Video.status == "uploaded",
            func.date(Video.uploaded_at) == today,
        )
        .scalar()
    ) or 0

    # total_videos
    total_videos = (
        db.query(func.count(Video.id))
        .filter(Video.status == "uploaded")
        .scalar()
    ) or 0

    # total_spent
    total_spent = user_settings.total_spent_usd or 0.0

    # subscriber_count from latest ChannelStats
    latest_stats: Optional[ChannelStats] = (
        db.query(ChannelStats).order_by(ChannelStats.synced_at.desc()).first()
    )
    subscriber_count = latest_stats.subscribers if latest_stats else 0

    # watch_hours_this_month
    if latest_stats and latest_stats.watch_hours:
        watch_hours_this_month = latest_stats.watch_hours
    else:
        # approximate from total views * avg duration
        avg_duration_result = (
            db.query(func.avg(Video.duration_seconds))
            .filter(Video.status == "uploaded")
            .scalar()
        ) or 0
        total_views_all = (
            db.query(func.coalesce(func.sum(Video.views), 0))
            .filter(Video.status == "uploaded")
            .scalar()
        ) or 0
        watch_hours_this_month = round((total_views_all * avg_duration_result) / 3600, 2)

    # recent_uploads
    recent_rows = (
        db.query(Video)
        .filter(Video.status == "uploaded")
        .order_by(Video.uploaded_at.desc())
        .limit(5)
        .all()
    )
    recent_uploads = [
        {
            "id": v.id,
            "title": v.title,
            "status": v.status,
            "youtube_url": v.youtube_url,
            "thumbnail_path": v.thumbnail_path,
            "views": v.views,
            "uploaded_at": v.uploaded_at.isoformat() if v.uploaded_at else None,
        }
        for v in recent_rows
    ]

    # pipeline_running
    pipeline_running = (
        db.query(Job).filter(Job.status == "running").count() > 0
    )

    # next scheduled times
    next_short_at = _next_occurrence(user_settings.upload_time_shorts or "08:00", now)
    next_long_at = _next_occurrence(user_settings.upload_time_long or "10:00", now)

    return {
        "today_views": today_views,
        "total_videos": total_videos,
        "total_spent": total_spent,
        "subscriber_count": subscriber_count,
        "watch_hours_this_month": watch_hours_this_month,
        "recent_uploads": recent_uploads,
        "pipeline_running": pipeline_running,
        "next_short_at": next_short_at.isoformat(),
        "next_long_at": next_long_at.isoformat(),
        "automation_enabled": user_settings.automation_enabled,
        "channel_name": user_settings.youtube_channel_name,
        "channel_thumbnail": user_settings.youtube_channel_thumbnail,
    }


@router.get("/views-chart")
def get_views_chart(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    result = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        views = (
            db.query(func.coalesce(func.sum(Video.views), 0))
            .filter(
                Video.status == "uploaded",
                func.date(Video.uploaded_at) == day,
            )
            .scalar()
        ) or 0
        result.append({"date": day.isoformat(), "views": int(views)})
    return result


@router.get("/cost-breakdown")
def get_cost_breakdown(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)

    user_settings = get_or_create_settings(db)

    avg_short_cost = (
        db.query(func.avg(Video.cost_usd))
        .filter(Video.type == "short")
        .scalar()
    ) or 0.0

    avg_long_cost = (
        db.query(func.avg(Video.cost_usd))
        .filter(Video.type == "long")
        .scalar()
    ) or 0.0

    total_cost = (
        db.query(func.coalesce(func.sum(Video.cost_usd), 0.0))
        .scalar()
    ) or 0.0

    this_week = (
        db.query(func.coalesce(func.sum(Video.cost_usd), 0.0))
        .filter(Video.created_at >= week_ago)
        .scalar()
    ) or 0.0

    today_spend = (
        db.query(func.coalesce(func.sum(Video.cost_usd), 0.0))
        .filter(func.date(Video.created_at) == today)
        .scalar()
    ) or 0.0

    return {
        "avg_short_cost": round(float(avg_short_cost), 4),
        "avg_long_cost": round(float(avg_long_cost), 4),
        "total_cost": round(float(total_cost), 4),
        "this_week": round(float(this_week), 4),
        "daily_budget": user_settings.daily_budget_usd,
        "today_spend": round(float(today_spend), 4),
    }


@router.get("/youtube")
def get_youtube_stats(db: Session = Depends(get_db)):
    latest: Optional[ChannelStats] = (
        db.query(ChannelStats).order_by(ChannelStats.synced_at.desc()).first()
    )
    if latest is None:
        return {
            "id": None,
            "synced_at": None,
            "subscribers": 0,
            "total_views": 0,
            "video_count": 0,
            "watch_hours": 0.0,
        }
    return {
        "id": latest.id,
        "synced_at": latest.synced_at.isoformat() if latest.synced_at else None,
        "subscribers": latest.subscribers,
        "total_views": latest.total_views,
        "video_count": latest.video_count,
        "watch_hours": latest.watch_hours,
    }
