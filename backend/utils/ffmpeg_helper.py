import asyncio
import json
import os
import subprocess
import tempfile


def check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


async def get_video_duration(video_path: str) -> float:
    loop = asyncio.get_event_loop()

    def _probe():
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                video_path,
            ],
            capture_output=True,
            text=True,
        )
        return result.stdout

    output = await loop.run_in_executor(None, _probe)
    data = json.loads(output)
    return float(data["streams"][0]["duration"])


async def loop_video(input_path: str, output_path: str, duration: int) -> None:
    loop = asyncio.get_event_loop()

    def _run():
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-stream_loop", "-1",
                "-i", input_path,
                "-t", str(duration),
                "-c", "copy",
                output_path,
            ],
            check=True,
        )

    await loop.run_in_executor(None, _run)


async def concat_videos_with_xfade(input_paths: list, output_path: str) -> None:
    loop = asyncio.get_event_loop()

    tmp_filelist = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    )
    try:
        for path in input_paths:
            tmp_filelist.write(f"file '{path}'\n")
        tmp_filelist.flush()
        tmp_filelist.close()
        filelist_path = tmp_filelist.name

        def _run():
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", filelist_path,
                    "-c:v", "libx264",
                    "-crf", "18",
                    "-preset", "fast",
                    output_path,
                ],
                check=True,
            )

        await loop.run_in_executor(None, _run)
    finally:
        try:
            os.remove(tmp_filelist.name)
        except Exception:
            pass


async def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> None:
    loop = asyncio.get_event_loop()

    def _run():
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path,
            ],
            check=True,
        )

    await loop.run_in_executor(None, _run)
