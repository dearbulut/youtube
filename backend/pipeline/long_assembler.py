import asyncio
import logging
import math
import os
import subprocess
from datetime import datetime
from functools import partial

from models.video import Video, Job
from utils.file_manager import get_temp_path

logger = logging.getLogger(__name__)


def _run_subprocess(args: list[str]) -> subprocess.CompletedProcess:
    """Run a subprocess and raise on non-zero exit code."""
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        cmd_str = " ".join(args[:4]) + " ..."
        raise RuntimeError(
            f"FFmpeg command failed (rc={result.returncode}): {cmd_str}\n"
            f"stderr: {result.stderr[-2000:]}"
        )
    return result


async def _run_subprocess_async(args: list[str]) -> subprocess.CompletedProcess:
    """Run a subprocess in a thread executor so it does not block the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, partial(_run_subprocess, args))


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


async def assemble_long_video(
    db,
    video_id: int,
    base_video_path: str,
    audio_path: str,
    target_duration_seconds: int,
) -> str:
    """
    Assemble a long-form video by looping base_video_path and audio_path to
    target_duration_seconds, then merging them into a single output file.

    Returns the path to the final merged video file.
    """
    video: Video = db.query(Video).filter(Video.id == video_id).first()
    if video is None:
        raise ValueError(f"Video {video_id} not found")

    job = _create_job(db, video_id, "assemble")

    looped_video_path = get_temp_path(f"assemble_video_looped_{video_id}.mp4")
    looped_audio_path = get_temp_path(f"assemble_audio_looped_{video_id}.aac")
    final_path = get_temp_path(f"assemble_final_{video_id}.mp4")

    try:
        video.status = "assembling"
        db.commit()

        # ------------------------------------------------------------------
        # 1. Determine base video duration and calculate loop count
        # ------------------------------------------------------------------
        probe = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    base_video_path,
                ],
                capture_output=True,
                text=True,
            ),
        )
        try:
            base_duration = float(probe.stdout.strip())
        except (ValueError, AttributeError):
            # Fallback: assume the clip duration stored on the video object
            base_duration = float(video.duration_seconds or 60)

        loops = math.ceil(target_duration_seconds / base_duration) if base_duration > 0 else 1
        logger.info(
            "Assembling video %s: base_duration=%.1fs loops=%d target=%ds",
            video_id,
            base_duration,
            loops,
            target_duration_seconds,
        )

        # ------------------------------------------------------------------
        # 2. Loop the base video to target duration
        # ------------------------------------------------------------------
        await _run_subprocess_async([
            "ffmpeg", "-y",
            "-stream_loop", str(loops),
            "-i", base_video_path,
            "-t", str(target_duration_seconds),
            "-c", "copy",
            looped_video_path,
        ])
        logger.info("Looped video written to %s", looped_video_path)

        # ------------------------------------------------------------------
        # 3. Loop audio to match video duration
        # ------------------------------------------------------------------
        await _run_subprocess_async([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", audio_path,
            "-t", str(target_duration_seconds),
            "-c", "copy",
            looped_audio_path,
        ])
        logger.info("Looped audio written to %s", looped_audio_path)

        # ------------------------------------------------------------------
        # 4. Merge looped video + looped audio
        # ------------------------------------------------------------------
        await _run_subprocess_async([
            "ffmpeg", "-y",
            "-i", looped_video_path,
            "-i", looped_audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            final_path,
        ])
        logger.info("Final merged video written to %s", final_path)

        # ------------------------------------------------------------------
        # 5. Persist result and clean up intermediate files
        # ------------------------------------------------------------------
        video.video_path = final_path
        video.status = "video_ready"
        db.commit()

        _finish_job(db, job, status="done", log=f"final={final_path}")

        for temp_path in (looped_video_path, looped_audio_path):
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError as e:
                    logger.warning("Could not remove temp file %s: %s", temp_path, e)

        return final_path

    except Exception as exc:
        logger.exception("Failed to assemble long video %s", video_id)
        _finish_job(db, job, status="failed", log=str(exc))
        video.status = "failed"
        video.error_message = str(exc)
        db.commit()

        # Best-effort cleanup of any partially-written temp files
        for temp_path in (looped_video_path, looped_audio_path, final_path):
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

        raise
