import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
from models.video import Video, Job
from models.settings import get_or_create_settings
from config import settings as app_settings
from pipeline.idea_generator import generate_idea
from pipeline.video_producer import produce_video
from pipeline.audio_producer import produce_audio
from pipeline.long_assembler import assemble_long_video
from pipeline.thumbnail_gen import generate_thumbnail
from pipeline.seo_writer import write_seo
from pipeline.uploader import upload_to_youtube

logger = logging.getLogger(__name__)


async def run_short_pipeline(db: Session = None, video_id: int = None):
    """Entry point for short video pipeline. Creates Video record if video_id is None."""
    own_db = db is None
    if own_db:
        db = SessionLocal()
    try:
        user_settings = get_or_create_settings(db)

        # Create video record if not provided
        if video_id is None:
            video = Video(
                type="short",
                status="pending",
                duration_seconds=user_settings.shorts_duration_seconds or 50,
            )
            db.add(video)
            db.commit()
            db.refresh(video)
            video_id = video.id

        logger.info(f"Starting short pipeline for video {video_id}")

        # Step 1: Generate idea
        concept = await generate_idea(db, video_id, "short")

        # Step 2: Produce video (Kling)
        video_path = await produce_video(db, video_id)

        # Step 3: No audio for shorts (native audio from Kling)

        # Step 4: Generate thumbnail
        thumbnail_path = await generate_thumbnail(db, video_id)

        # Step 5: Write SEO metadata
        seo = await write_seo(db, video_id)

        # Step 6: Upload to YouTube
        youtube_id = await upload_to_youtube(db, video_id)

        logger.info(f"Short pipeline complete: {youtube_id}")
        return youtube_id

    except Exception as e:
        logger.error(f"Short pipeline failed for video {video_id}: {e}")
        video = db.query(Video).get(video_id)
        if video and video.status != "failed":
            video.status = "failed"
            video.error_message = str(e)
            db.commit()
        raise
    finally:
        if own_db:
            db.close()


async def run_long_pipeline(db: Session = None, video_id: int = None):
    """Entry point for long video pipeline."""
    own_db = db is None
    if own_db:
        db = SessionLocal()
    try:
        user_settings = get_or_create_settings(db)
        target_duration = (user_settings.long_video_duration_minutes or 60) * 60

        if video_id is None:
            video = Video(
                type="long",
                status="pending",
                duration_seconds=target_duration,
            )
            db.add(video)
            db.commit()
            db.refresh(video)
            video_id = video.id

        logger.info(f"Starting long pipeline for video {video_id}")

        # Step 1: Generate idea
        concept = await generate_idea(db, video_id, "long")

        # Step 2: Produce base video clips (6 clips via Kling)
        base_video_path = await produce_video(db, video_id)

        # Step 3: Produce audio (Suno via Apiframe)
        audio_path = await produce_audio(db, video_id, target_duration)

        # Step 4: Assemble long video (loop + merge audio)
        final_video_path = await assemble_long_video(
            db, video_id, base_video_path, audio_path, target_duration
        )

        # Step 5: Generate thumbnail
        thumbnail_path = await generate_thumbnail(db, video_id)

        # Step 6: Write SEO metadata
        seo = await write_seo(db, video_id)

        # Step 7: Upload to YouTube
        youtube_id = await upload_to_youtube(db, video_id)

        logger.info(f"Long pipeline complete: {youtube_id}")
        return youtube_id

    except Exception as e:
        logger.error(f"Long pipeline failed for video {video_id}: {e}")
        video = db.query(Video).get(video_id)
        if video and video.status != "failed":
            video.status = "failed"
            video.error_message = str(e)
            db.commit()
        raise
    finally:
        if own_db:
            db.close()
