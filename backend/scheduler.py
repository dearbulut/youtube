import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from database import SessionLocal
from models.settings import get_or_create_settings
from pipeline.orchestrator import run_short_pipeline, run_long_pipeline
from config import settings as app_settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _run_short_pipeline_job():
    db = SessionLocal()
    try:
        s = get_or_create_settings(db)
        if not s.automation_enabled:
            return
        from utils.cost_tracker import check_budget
        if not check_budget(db):
            logger.info("Daily budget reached, skipping short")
            return
        await run_short_pipeline(db)
    finally:
        db.close()


async def _run_long_pipeline_job():
    db = SessionLocal()
    try:
        s = get_or_create_settings(db)
        if not s.automation_enabled:
            return
        from utils.cost_tracker import check_budget
        if not check_budget(db):
            logger.info("Daily budget reached, skipping long")
            return
        await run_long_pipeline(db)
    finally:
        db.close()


async def _sync_youtube_stats_job():
    db = SessionLocal()
    try:
        s = get_or_create_settings(db)
        if not s.youtube_channel_id:
            return
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(f"{app_settings.base_url}/youtube/sync-stats")
    finally:
        db.close()


async def _cleanup_job():
    from utils.file_manager import cleanup_old_files
    count = cleanup_old_files(older_than_hours=24)
    logger.info(f"Cleaned up {count} temp files")


def reschedule_all():
    for job_id in ["short_1", "short_2", "long_video", "stats_sync", "cleanup"]:
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass

    db = SessionLocal()
    try:
        s = get_or_create_settings(db)
        upload_h, upload_m = map(int, s.upload_time_shorts.split(":"))
        long_h, long_m = map(int, s.upload_time_long.split(":"))

        scheduler.add_job(
            _run_short_pipeline_job,
            CronTrigger(hour=upload_h, minute=upload_m),
            id="short_1",
        )
        scheduler.add_job(
            _run_short_pipeline_job,
            CronTrigger(hour=(upload_h + 8) % 24, minute=upload_m),
            id="short_2",
        )
        scheduler.add_job(
            _run_long_pipeline_job,
            IntervalTrigger(days=s.long_video_interval_days),
            id="long_video",
        )
        scheduler.add_job(
            _sync_youtube_stats_job,
            CronTrigger(hour=3, minute=0),
            id="stats_sync",
        )
        scheduler.add_job(
            _cleanup_job,
            CronTrigger(hour=4, minute=0),
            id="cleanup",
        )
    finally:
        db.close()


def start_scheduler():
    reschedule_all()
    scheduler.start()


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
