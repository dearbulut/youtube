import os
import httpx
import anthropic
import openai
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional

from config import settings as app_settings, encrypt_value, decrypt_value, NICHES, COST_CLAUDE_INPUT_PER_MTOK
from database import get_db
from models.settings import UserSettings, get_or_create_settings

router = APIRouter(prefix="/settings", tags=["settings"])

# Fields the optimizer manages automatically (read-only unless manual_override=True)
AUTO_MANAGED_FIELDS = {
    "shorts_per_day",
    "long_video_interval_days",
    "upload_time_shorts",
    "upload_time_long",
    "niche_theme",
    "long_video_duration_minutes",
}

SCHEDULE_FIELDS = {
    "shorts_per_day",
    "upload_time_shorts",
    "upload_time_long",
    "long_video_interval_days",
    "automation_enabled",
}

API_KEY_FIELDS = {"anthropic_api_key", "openai_api_key", "fal_key", "apiframe_key"}

MASK = "••••••••"


def _mask_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return MASK


def _settings_to_dict(s: UserSettings) -> Dict[str, Any]:
    return {
        "id": s.id,
        "shorts_per_day": s.shorts_per_day,
        "automation_enabled": s.automation_enabled,
        "niche_theme": s.niche_theme,
        "language": s.language,
        "anthropic_api_key": _mask_key(s.anthropic_api_key),
        "openai_api_key": _mask_key(s.openai_api_key),
        "fal_key": _mask_key(s.fal_key),
        "apiframe_key": _mask_key(s.apiframe_key),
        "daily_budget_usd": s.daily_budget_usd,
        "total_spent_usd": s.total_spent_usd,
        "youtube_channel_name": s.youtube_channel_name,
        "youtube_channel_id": s.youtube_channel_id,
        "upload_time_shorts": s.upload_time_shorts,
        "upload_time_long": s.upload_time_long,
        "long_video_duration_minutes": s.long_video_duration_minutes,
        "shorts_duration_seconds": s.shorts_duration_seconds,
        "long_video_interval_days": s.long_video_interval_days,
        "custom_niche_description": s.custom_niche_description,
        "manual_override": s.manual_override,
    }


def _try_reschedule():
    try:
        from scheduler import reschedule_all
        reschedule_all()
    except Exception:
        pass


@router.get("/")
def get_settings(db: Session = Depends(get_db)):
    s = get_or_create_settings(db)
    return _settings_to_dict(s)


@router.put("/")
def update_settings(body: Dict[str, Any], db: Session = Depends(get_db)):
    s = get_or_create_settings(db)
    schedule_changed = False

    # Process manual_override first so it gates the rest of the fields in this request
    if "manual_override" in body and hasattr(s, "manual_override"):
        s.manual_override = bool(body["manual_override"])

    for field, value in body.items():
        if not hasattr(s, field):
            continue
        if field == "manual_override":
            continue  # already applied above
        # Block auto-managed fields when optimizer is in control
        if field in AUTO_MANAGED_FIELDS and not s.manual_override:
            continue
        if field in API_KEY_FIELDS:
            if value is None or value == MASK or value == "":
                continue
            value = encrypt_value(value)
        setattr(s, field, value)
        if field in SCHEDULE_FIELDS:
            schedule_changed = True

    db.commit()
    db.refresh(s)

    if schedule_changed:
        _try_reschedule()

    return _settings_to_dict(s)


@router.post("/test/anthropic")
def test_anthropic(body: Dict[str, Any], db: Session = Depends(get_db)):
    key = body.get("api_key") or body.get("anthropic_api_key")
    if not key or key == MASK:
        s = get_or_create_settings(db)
        key = decrypt_value(s.anthropic_api_key) if s.anthropic_api_key else None
    if not key:
        return {"valid": False, "error": "No API key provided"}
    try:
        client = anthropic.Anthropic(api_key=key)
        client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": "hi"}],
        )
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.post("/test/openai")
def test_openai(body: Dict[str, Any], db: Session = Depends(get_db)):
    key = body.get("api_key") or body.get("openai_api_key")
    if not key or key == MASK:
        s = get_or_create_settings(db)
        key = decrypt_value(s.openai_api_key) if s.openai_api_key else None
    if not key:
        return {"valid": False, "error": "No API key provided"}
    try:
        client = openai.OpenAI(api_key=key)
        client.models.list()
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.post("/test/fal")
def test_fal(body: Dict[str, Any], db: Session = Depends(get_db)):
    key = body.get("api_key") or body.get("fal_key")
    if not key or key == MASK:
        s = get_or_create_settings(db)
        key = decrypt_value(s.fal_key) if s.fal_key else None
    if not key:
        return {"valid": False, "error": "No API key provided"}
    try:
        if isinstance(key, str) and key.startswith("fal_"):
            os.environ["FAL_KEY"] = key
            return {"valid": True}
        os.environ["FAL_KEY"] = key
        resp = httpx.get("https://fal.run/health", timeout=10)
        return {"valid": resp.status_code < 400}
    except Exception as e:
        return {"valid": False, "error": str(e)}


@router.post("/test/apiframe")
def test_apiframe(body: Dict[str, Any], db: Session = Depends(get_db)):
    key = body.get("api_key") or body.get("apiframe_key")
    if not key or key == MASK:
        s = get_or_create_settings(db)
        key = decrypt_value(s.apiframe_key) if s.apiframe_key else None
    if not key:
        return {"valid": False, "error": "No API key provided"}
    try:
        resp = httpx.get(
            "https://api.apiframe.pro/account",
            headers={"Authorization": key},
            timeout=10,
        )
        return {"valid": resp.status_code == 200}
    except Exception as e:
        return {"valid": False, "error": str(e)}
