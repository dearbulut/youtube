from sqlalchemy import Column, Integer, String, Boolean, Float
from sqlalchemy.orm import Session
from database import Base


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True)
    shorts_per_day = Column(Integer, default=2)
    long_video_interval_days = Column(Integer, default=2)
    long_video_duration_minutes = Column(Integer, default=60)
    shorts_duration_seconds = Column(Integer, default=50)
    upload_time_shorts = Column(String, default="08:00")
    upload_time_long = Column(String, default="10:00")
    automation_enabled = Column(Boolean, default=True)
    niche_theme = Column(String, default="nature_ambient")
    custom_niche_description = Column(String, nullable=True)
    language = Column(String, default="en")
    # stored encrypted
    anthropic_api_key = Column(String, nullable=True)
    openai_api_key = Column(String, nullable=True)
    fal_key = Column(String, nullable=True)
    apiframe_key = Column(String, nullable=True)
    youtube_access_token = Column(String, nullable=True)
    youtube_refresh_token = Column(String, nullable=True)
    youtube_token_expiry = Column(String, nullable=True)
    youtube_channel_id = Column(String, nullable=True)
    youtube_channel_name = Column(String, nullable=True)
    youtube_channel_thumbnail = Column(String, nullable=True)
    daily_budget_usd = Column(Float, default=5.0)
    total_spent_usd = Column(Float, default=0.0)
    youtube_quota_used = Column(Integer, default=0)
    youtube_quota_date = Column(String, nullable=True)  # YYYY-MM-DD
    manual_override = Column(Boolean, default=False)


def get_or_create_settings(db: Session) -> UserSettings:
    obj = db.query(UserSettings).filter(UserSettings.id == 1).first()
    if obj is None:
        obj = UserSettings(id=1)
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj
