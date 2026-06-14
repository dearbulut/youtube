from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    type = Column(String)
    status = Column(String, default="pending")
    niche_theme = Column(String, nullable=True)
    title = Column(String, default="")
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    youtube_id = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    thumbnail_path = Column(String, nullable=True)
    video_path = Column(String, nullable=True)
    concept = Column(JSON, nullable=True)
    duration_seconds = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime, nullable=True)
    views = Column(Integer, default=0)

    jobs = relationship("Job", back_populates="video", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("videos.id"))
    step = Column(String)
    status = Column(String, default="running")
    log = Column(Text, default="")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    video = relationship("Video", back_populates="jobs")


class ChannelStats(Base):
    __tablename__ = "channel_stats"

    id = Column(Integer, primary_key=True)
    synced_at = Column(DateTime, default=datetime.utcnow)
    subscribers = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    video_count = Column(Integer, default=0)
    watch_hours = Column(Float, default=0.0)


class OptimizationReport(Base):
    __tablename__ = "optimization_reports"

    id = Column(Integer, primary_key=True)
    ran_at = Column(DateTime, default=datetime.utcnow)
    videos_analyzed = Column(Integer, default=0)
    decisions = Column(JSON, default=list)
    current_strategy = Column(JSON, default=dict)
