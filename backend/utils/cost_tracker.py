import datetime

from sqlalchemy.orm import Session

from models.video import Video
from models.settings import UserSettings


def add_video_cost(db, video_id: int, cost: float) -> None:
    video = db.query(Video).get(video_id)
    if video:
        video.cost_usd = (video.cost_usd or 0) + cost
        db.commit()


def add_daily_spend(db, amount: float) -> None:
    s = db.query(UserSettings).filter_by(id=1).first()
    if s:
        s.total_spent_usd = (s.total_spent_usd or 0) + amount
        db.commit()


def get_today_spend(db) -> float:
    today = datetime.datetime.utcnow().date()
    from models.video import Video
    total = db.query(Video).filter(Video.uploaded_at >= today).with_entities(Video.cost_usd).all()
    return sum(r[0] or 0 for r in total)


def check_budget(db) -> bool:
    s = db.query(UserSettings).filter_by(id=1).first()
    if not s:
        return True
    return get_today_spend(db) < s.daily_budget_usd
