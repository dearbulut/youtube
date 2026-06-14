import asyncio
import datetime
import time
import os

import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from config import settings, decrypt_value
from database import SessionLocal
from models.video import Video, Job
from models.settings import UserSettings, get_or_create_settings


async def upload_to_youtube(db, video_id: int) -> str:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise Exception(f"Video {video_id} not found")

    # Step 1: Create Job and set status
    job = Job(step="upload", video_id=video_id)
    db.add(job)
    video.status = "uploading"
    db.commit()

    # Step 2: Get user settings and decrypt tokens
    user_settings = get_or_create_settings(db)

    # Step 3: Build credentials
    token = decrypt_value(user_settings.youtube_access_token)
    refresh_token = decrypt_value(user_settings.youtube_refresh_token)
    creds = Credentials(
        token=token,
        refresh_token=refresh_token,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        token_uri="https://oauth2.googleapis.com/token",
    )

    # Step 4: Refresh if expired
    if creds.expired or not creds.valid:
        creds.refresh(Request())

    # Step 5: Build YouTube service
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    # Step 6: Check quota
    if user_settings.youtube_quota_used >= 9500:
        raise Exception("YouTube quota exhausted")

    # Step 7: Video metadata body
    hashtags = video.hashtags or []
    description = video.description or ""
    body = {
        "snippet": {
            "title": video.title,
            "description": description + "\n\n" + " ".join(hashtags),
            "tags": video.tags or [],
            "categoryId": "22",
            "defaultLanguage": video.language or "en",
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    # Step 8: MediaFileUpload
    media = MediaFileUpload(
        video.video_path,
        chunksize=1024 * 1024,
        resumable=True,
    )

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    # Step 9: Upload with exponential backoff
    loop = asyncio.get_event_loop()
    response = None
    wait_times = [2, 4, 8, 16, 32]
    retry_status_codes = {500, 502, 503, 504}

    for attempt in range(5):
        try:
            def _next_chunk():
                return insert_request.next_chunk()

            status, response = await loop.run_in_executor(None, _next_chunk)
            if response is not None:
                break
            # Continue uploading chunks
            while response is None:
                status, response = await loop.run_in_executor(None, _next_chunk)
        except Exception as e:
            error_str = str(e)
            should_retry = any(str(code) in error_str for code in retry_status_codes)
            if should_retry and attempt < 4:
                await asyncio.sleep(wait_times[attempt])
                continue
            raise

    if response is None:
        raise Exception("Upload failed: no response received")

    youtube_id = response["id"]

    # Step 10: Set thumbnail
    thumbnail_path = video.thumbnail_path
    if thumbnail_path and os.path.exists(thumbnail_path):
        def _set_thumbnail():
            youtube.thumbnails().set(
                videoId=youtube_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()

        await loop.run_in_executor(None, _set_thumbnail)

    # Step 11: Update quota usage
    user_settings.youtube_quota_used = (user_settings.youtube_quota_used or 0) + 1600

    # Step 12: Update video record
    video.youtube_id = youtube_id
    video.youtube_url = f"https://www.youtube.com/watch?v={youtube_id}"
    video.status = "uploaded"
    video.uploaded_at = datetime.datetime.utcnow()

    # Step 13: Update total spend
    user_settings.total_spent_usd = (user_settings.total_spent_usd or 0) + (video.cost_usd or 0)

    db.commit()

    # Step 14: Delete video temp file
    if video.video_path and os.path.exists(video.video_path):
        try:
            os.remove(video.video_path)
        except Exception:
            pass

    # Step 15: Return youtube_id
    return youtube_id
