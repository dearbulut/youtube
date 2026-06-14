import asyncio
import os
import httpx
from datetime import datetime

from config import settings, decrypt_value, COST_SUNO_PER_SONG
from database import SessionLocal
from models.video import Video, Job
from models.settings import get_or_create_settings
from utils.file_manager import get_temp_path


async def produce_audio(db, video_id: int, duration_seconds: int) -> str:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video {video_id} not found")

    job = Job(
        video_id=video_id,
        step="generate_audio",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    video.status = "generating_audio"
    db.commit()

    try:
        user_settings = get_or_create_settings(db)
        raw_key = getattr(user_settings, "apiframe_key", None)
        apiframe_key = (
            decrypt_value(raw_key) if raw_key else None
        ) or settings.apiframe_key

        concept = video.concept or {}
        audio_style = concept.get("audio_style", "ambient nature sounds, peaceful")

        prompt_text = (
            f"{audio_style} - 3 minutes, loopable, ambient, no vocals"
        )

        async with httpx.AsyncClient(timeout=60.0) as client:
            create_resp = await client.post(
                "https://api.apiframe.pro/suno-v4",
                headers={"Authorization": apiframe_key},
                json={
                    "prompt": prompt_text,
                    "make_instrumental": True,
                    "model": "chirp-v4",
                },
            )
            create_resp.raise_for_status()
            create_data = create_resp.json()
            task_id = create_data.get("task_id") or create_data.get("id")
            if not task_id:
                raise RuntimeError(
                    f"No task_id in suno response: {create_data}"
                )

        audio_url = None
        elapsed = 0
        max_wait = 180

        async with httpx.AsyncClient(timeout=30.0) as poll_client:
            while elapsed < max_wait:
                await asyncio.sleep(5)
                elapsed += 5

                poll_resp = await poll_client.get(
                    f"https://api.apiframe.pro/fetch/{task_id}",
                    headers={"Authorization": apiframe_key},
                )
                poll_resp.raise_for_status()
                poll_data = poll_resp.json()

                status = poll_data.get("status", "")
                if status in ("done", "completed"):
                    audio_url = poll_data.get("audio_url") or (
                        poll_data.get("output", [{}])[0].get("audio_url")
                    )
                    break
                elif status in ("failed", "error"):
                    raise RuntimeError(
                        f"Suno task failed: {poll_data}"
                    )

        if not audio_url:
            raise RuntimeError(
                f"Timed out waiting for Suno audio (task_id={task_id})"
            )

        audio_path = get_temp_path(f"audio_{video_id}.mp3")
        async with httpx.AsyncClient(timeout=120.0) as dl_client:
            async with dl_client.stream("GET", audio_url) as stream:
                stream.raise_for_status()
                with open(audio_path, "wb") as f:
                    async for chunk in stream.aiter_bytes(chunk_size=8192):
                        f.write(chunk)

        video.cost_usd = (video.cost_usd or 0.0) + COST_SUNO_PER_SONG

        job.status = "done"
        job.finished_at = datetime.utcnow()
        db.commit()

        return audio_path

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.finished_at = datetime.utcnow()
        video.status = "failed"
        db.commit()
        raise
