import asyncio
import os
import logging
from datetime import datetime

import httpx
import fal_client

from config import settings, decrypt_value
from models.video import Video, Job
from models.settings import get_or_create_settings
from utils.ffmpeg_helper import loop_video, concat_videos_with_xfade
from utils.file_manager import get_temp_path

logger = logging.getLogger(__name__)

DEFAULT_CLIP_COST = 0.045  # USD per 10-second clip

LONG_VIDEO_LIGHT_SUFFIXES = [
    " morning light",
    " afternoon golden light",
    " golden hour",
    " dusk light",
    " evening blue hour",
    " night moonlight",
]


async def _download_video(url: str, dest_path: str) -> None:
    """Stream-download a video URL to dest_path using httpx."""
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    f.write(chunk)


def _extract_clip_cost(result: dict) -> float:
    """Try to read cost from fal result, fall back to default."""
    try:
        cost = result.get("cost")
        if cost is not None:
            return float(cost)
    except (TypeError, ValueError):
        pass
    return DEFAULT_CLIP_COST


def _create_job(db, video_id: int, step: str) -> Job:
    job = Job(video_id=video_id, step=step, status="running", started_at=datetime.utcnow())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _finish_job(db, job: Job, status: str = "done", log: str = "") -> None:
    job.status = status
    job.log = log
    job.finished_at = datetime.utcnow()
    db.commit()


async def produce_video(db, video_id: int) -> str:
    """
    Generate a video using fal-ai/kling-video.

    Returns the path to the produced video file.
    """
    video: Video = db.query(Video).filter(Video.id == video_id).first()
    if video is None:
        raise ValueError(f"Video {video_id} not found")

    user_settings = get_or_create_settings(db)

    # Resolve FAL API key: prefer user-level encrypted key, fall back to env/config
    raw_fal_key = user_settings.fal_key or settings.fal_key
    fal_key = decrypt_value(raw_fal_key) if raw_fal_key else ""
    if not fal_key:
        raise ValueError("FAL_KEY is not configured. Set it in user settings or .env.")
    os.environ["FAL_KEY"] = fal_key

    concept: dict = video.concept or {}
    video_type: str = (video.type or "short").lower()

    video.status = "generating_video"
    db.commit()

    if video_type == "short":
        await _produce_short(db, video, concept)
    else:
        await _produce_long(db, video, concept)

    db.commit()
    return video.video_path


# ---------------------------------------------------------------------------
# SHORT video path
# ---------------------------------------------------------------------------

async def _produce_short(db, video: Video, concept: dict) -> None:
    job = _create_job(db, video.id, "generate_clip")
    try:
        scene: str = concept.get("scene", "")
        hook: str = concept.get("hook", "")
        prompt = f"{scene} {hook}".strip()

        logger.info("Generating SHORT clip for video %s: %r", video.id, prompt[:80])

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: fal_client.subscribe(
                "fal-ai/kling-video/v2.1/standard/text-to-video",
                arguments={
                    "prompt": prompt,
                    "duration": "10",
                    "aspect_ratio": "9:16",
                    "cfg_scale": 0.5,
                },
                with_logs=True,
            ),
        )

        clip_url: str = result["video"]["url"]
        clip_cost: float = _extract_clip_cost(result)

        raw_path = get_temp_path(f"short_raw_{video.id}.mp4")
        await _download_video(clip_url, raw_path)

        looped_path = get_temp_path(f"short_looped_{video.id}.mp4")
        await loop_video(raw_path, looped_path, duration=50)

        # Clean up raw clip
        if os.path.exists(raw_path):
            try:
                os.remove(raw_path)
            except OSError:
                pass

        video.video_path = looped_path
        video.duration_seconds = 50
        video.cost_usd = (video.cost_usd or 0.0) + clip_cost
        video.status = "video_ready"

        _finish_job(db, job, status="done", log=f"clip_cost={clip_cost}")
        logger.info("SHORT video ready: %s", looped_path)

    except Exception as exc:
        logger.exception("Failed to produce SHORT video %s", video.id)
        _finish_job(db, job, status="failed", log=str(exc))
        video.status = "failed"
        video.error_message = str(exc)
        db.commit()
        raise


# ---------------------------------------------------------------------------
# LONG video path (6 clips + crossfade concat)
# ---------------------------------------------------------------------------

async def _produce_long(db, video: Video, concept: dict) -> None:
    job = _create_job(db, video.id, "generate_clips")
    clip_paths: list[str] = []
    total_cost = 0.0
    try:
        base_scene: str = concept.get("scene", "")
        hook: str = concept.get("hook", "")
        base_prompt = f"{base_scene} {hook}".strip()

        logger.info("Generating LONG video (%d clips) for video %s", len(LONG_VIDEO_LIGHT_SUFFIXES), video.id)

        for idx, suffix in enumerate(LONG_VIDEO_LIGHT_SUFFIXES):
            prompt = base_prompt + suffix
            logger.info("  Clip %d/%d: %r", idx + 1, len(LONG_VIDEO_LIGHT_SUFFIXES), prompt[:80])

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda _p=prompt: fal_client.subscribe(
                    "fal-ai/kling-video/v2.1/standard/text-to-video",
                    arguments={
                        "prompt": _p,
                        "duration": "10",
                        "aspect_ratio": "16:9",
                        "cfg_scale": 0.5,
                    },
                    with_logs=True,
                ),
            )

            clip_url: str = result["video"]["url"]
            clip_cost: float = _extract_clip_cost(result)
            total_cost += clip_cost

            clip_path = get_temp_path(f"long_clip_{video.id}_{idx}.mp4")
            await _download_video(clip_url, clip_path)
            clip_paths.append(clip_path)

        # Assemble all clips into a single video with crossfades
        assembled_path = get_temp_path(f"long_assembled_{video.id}.mp4")
        await concat_videos_with_xfade(clip_paths, assembled_path)

        # Clean up individual clip files
        for p in clip_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

        video.video_path = assembled_path
        video.duration_seconds = 60
        video.cost_usd = (video.cost_usd or 0.0) + total_cost
        video.status = "video_ready"

        _finish_job(db, job, status="done", log=f"clips=6 total_cost={total_cost:.4f}")
        logger.info("LONG video ready: %s (cost $%.4f)", assembled_path, total_cost)

    except Exception as exc:
        logger.exception("Failed to produce LONG video %s", video.id)
        # Clean up any downloaded clips on failure
        for p in clip_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass
        _finish_job(db, job, status="failed", log=str(exc))
        video.status = "failed"
        video.error_message = str(exc)
        db.commit()
        raise
