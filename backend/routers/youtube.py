from datetime import date, datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import settings, encrypt_value, decrypt_value
from database import get_db
from models.video import Video, ChannelStats
from models.settings import UserSettings, get_or_create_settings

router = APIRouter(prefix="/youtube", tags=["youtube"])

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "openid",
    "email",
    "profile",
]


def build_youtube_service(db: Session):
    """Build and return an authenticated YouTube API client.

    Raises HTTPException(400) if credentials are not stored.
    Automatically refreshes the access token if expired.
    """
    user_settings = get_or_create_settings(db)

    if not user_settings.youtube_channel_id:
        raise HTTPException(status_code=400, detail="YouTube account not connected")

    if not user_settings.youtube_refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available")

    access_token = decrypt_value(user_settings.youtube_access_token or "")
    refresh_token_val = decrypt_value(user_settings.youtube_refresh_token)

    creds = Credentials(
        token=access_token or None,
        refresh_token=refresh_token_val,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        scopes=SCOPES,
    )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            user_settings.youtube_access_token = (
                encrypt_value(creds.token) if creds.token else None
            )
            user_settings.youtube_token_expiry = (
                creds.expiry.isoformat() if creds.expiry else None
            )
            db.commit()

    return build("youtube", "v3", credentials=creds)


@router.get("/quota")
def get_quota(db: Session = Depends(get_db)):
    user_settings = get_or_create_settings(db)
    today_str = date.today().isoformat()

    if user_settings.youtube_quota_date != today_str:
        user_settings.youtube_quota_used = 0
        user_settings.youtube_quota_date = today_str
        db.commit()

    quota_used = user_settings.youtube_quota_used or 0
    limit = 10000

    return {
        "used": quota_used,
        "limit": limit,
        "remaining": limit - quota_used,
        "date": today_str,
    }


@router.post("/sync-stats")
def sync_stats(db: Session = Depends(get_db)):
    youtube = build_youtube_service(db)

    channel_response = (
        youtube.channels()
        .list(part="snippet,statistics,contentDetails", mine=True)
        .execute()
    )

    items = channel_response.get("items", [])
    if not items:
        raise HTTPException(status_code=404, detail="No channel found")

    item = items[0]
    statistics = item.get("statistics", {})

    subscribers = int(statistics.get("subscriberCount", 0))
    total_views = int(statistics.get("viewCount", 0))
    video_count = int(statistics.get("videoCount", 0))

    channel_stat = ChannelStats(
        synced_at=datetime.utcnow(),
        subscribers=subscribers,
        total_views=total_views,
        video_count=video_count,
    )
    db.add(channel_stat)
    db.commit()

    # Sync recent video view counts for last 20 uploaded videos
    recent_videos: List[Video] = (
        db.query(Video)
        .filter(Video.youtube_id.isnot(None))
        .order_by(Video.uploaded_at.desc())
        .limit(20)
        .all()
    )

    if recent_videos:
        youtube_ids = [v.youtube_id for v in recent_videos if v.youtube_id]
        if youtube_ids:
            # YouTube API accepts up to 50 ids per request
            ids_param = ",".join(youtube_ids)
            video_response = (
                youtube.videos()
                .list(part="statistics", id=ids_param)
                .execute()
            )
            stats_by_id = {
                v_item["id"]: v_item.get("statistics", {})
                for v_item in video_response.get("items", [])
            }
            for video in recent_videos:
                if video.youtube_id in stats_by_id:
                    view_count = int(
                        stats_by_id[video.youtube_id].get("viewCount", 0)
                    )
                    video.views = view_count

            db.commit()

    return {
        "status": "synced",
        "subscribers": subscribers,
        "total_views": total_views,
    }
