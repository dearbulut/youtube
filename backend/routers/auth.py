from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import settings, encrypt_value, decrypt_value
from database import get_db
from models.settings import UserSettings, get_or_create_settings

router = APIRouter(prefix="/auth", tags=["auth"])

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "openid",
    "email",
    "profile",
]


def _get_client_config() -> dict:
    return {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uris": [settings.google_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


@router.get("/login")
def login():
    flow = Flow.from_client_config(
        _get_client_config(),
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )
    auth_url, _state = flow.authorization_url(access_type="offline", prompt="consent")
    return RedirectResponse(auth_url)


@router.get("/callback")
def callback(code: str, state: str = "", db: Session = Depends(get_db)):
    flow = Flow.from_client_config(
        _get_client_config(),
        scopes=SCOPES,
        redirect_uri=settings.google_redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials

    youtube = build("youtube", "v3", credentials=creds)
    response = (
        youtube.channels()
        .list(part="snippet,statistics", mine=True)
        .execute()
    )

    channel_id = None
    channel_name = None
    channel_thumbnail = None
    items = response.get("items", [])
    if items:
        item = items[0]
        channel_id = item.get("id")
        snippet = item.get("snippet", {})
        channel_name = snippet.get("title")
        thumbnails = snippet.get("thumbnails", {})
        default_thumb = thumbnails.get("default", {})
        channel_thumbnail = default_thumb.get("url")

    user_settings = get_or_create_settings(db)
    user_settings.youtube_access_token = encrypt_value(creds.token) if creds.token else None
    user_settings.youtube_refresh_token = encrypt_value(creds.refresh_token) if creds.refresh_token else None
    user_settings.youtube_token_expiry = (
        creds.expiry.isoformat() if creds.expiry else None
    )
    user_settings.youtube_channel_id = channel_id
    user_settings.youtube_channel_name = channel_name
    user_settings.youtube_channel_thumbnail = channel_thumbnail
    db.commit()

    return RedirectResponse("http://localhost:3000/")


@router.post("/logout")
def logout(db: Session = Depends(get_db)):
    user_settings = get_or_create_settings(db)
    user_settings.youtube_access_token = None
    user_settings.youtube_refresh_token = None
    user_settings.youtube_token_expiry = None
    user_settings.youtube_channel_id = None
    user_settings.youtube_channel_name = None
    user_settings.youtube_channel_thumbnail = None
    db.commit()
    return {"status": "logged_out"}


@router.get("/status")
def status(db: Session = Depends(get_db)):
    user_settings = get_or_create_settings(db)
    connected = bool(user_settings.youtube_channel_id)
    return {
        "connected": connected,
        "channel_name": user_settings.youtube_channel_name,
        "channel_id": user_settings.youtube_channel_id,
        "thumbnail": user_settings.youtube_channel_thumbnail,
    }


@router.post("/refresh")
def refresh_token(db: Session = Depends(get_db)):
    user_settings = get_or_create_settings(db)

    if not user_settings.youtube_refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token stored")

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

    creds.refresh(Request())

    user_settings.youtube_access_token = encrypt_value(creds.token) if creds.token else None
    user_settings.youtube_token_expiry = (
        creds.expiry.isoformat() if creds.expiry else None
    )
    db.commit()

    return {"status": "refreshed"}
