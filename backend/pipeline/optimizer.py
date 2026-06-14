"""
Autonomous strategy optimizer.
Runs after each video upload and after daily stats sync (05:00 UTC).
Adjusts schedule, niche, duration, and category based on performance data.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from config import NICHES
from database import SessionLocal
from models.settings import UserSettings, get_or_create_settings
from models.video import OptimizationReport, Video

logger = logging.getLogger(__name__)

MIN_VIDEOS = 10

# Duration bucket definitions (minutes)
DURATION_BUCKETS = {
    "short_30": 30,
    "medium_60": 60,
    "long_120": 120,
    "extended_180": 180,
}


def _bucket_for_duration(duration_seconds: int) -> str:
    minutes = (duration_seconds or 3600) / 60
    if minutes <= 45:
        return "short_30"
    if minutes <= 90:
        return "medium_60"
    if minutes <= 150:
        return "long_120"
    return "extended_180"


def _score_video(video: Video, now: datetime) -> float:
    """Compute performance score: views*0.4 + watch_time_ratio*0.35 + ctr*0.25"""
    views = video.views or 0
    if video.uploaded_at:
        hours_since = max(1.0, (now - video.uploaded_at).total_seconds() / 3600)
    else:
        hours_since = 1.0
    watch_time_ratio = views / hours_since
    ctr_estimate = 1.0
    return (views * 0.4) + (watch_time_ratio * 0.35) + (ctr_estimate * 0.25)


def _current_strategy(s: UserSettings) -> dict:
    return {
        "shorts_per_day": s.shorts_per_day,
        "long_interval_days": s.long_video_interval_days,
        "upload_hour_shorts": s.upload_time_shorts,
        "upload_hour_long": s.upload_time_long,
        "niche_theme": s.niche_theme,
        "long_duration_minutes": s.long_video_duration_minutes,
        "manual_override": s.manual_override,
    }


class OptimizationEngine:

    def analyze_and_optimize(self, db: Session) -> dict[str, Any]:
        """Main entry point — reads DB, computes scores, updates UserSettings."""
        now = datetime.utcnow()

        # Idempotency: if already ran today, return cached report
        existing = (
            db.query(OptimizationReport)
            .filter(func.date(OptimizationReport.ran_at) == now.date())
            .order_by(OptimizationReport.ran_at.desc())
            .first()
        )
        if existing:
            logger.info("Optimizer already ran today, returning cached report")
            return {
                "ran_at": existing.ran_at.isoformat() + "Z",
                "videos_analyzed": existing.videos_analyzed,
                "decisions": existing.decisions,
                "current_strategy": existing.current_strategy,
            }

        user_settings = get_or_create_settings(db)
        strategy = _current_strategy(user_settings)

        # Check minimum data requirement
        total_uploaded = (
            db.query(func.count(Video.id))
            .filter(Video.status == "uploaded")
            .scalar()
        ) or 0

        if total_uploaded < MIN_VIDEOS:
            msg = f"Insufficient data: {total_uploaded}/{MIN_VIDEOS} uploaded videos"
            logger.info(msg)
            report = OptimizationReport(
                ran_at=now,
                videos_analyzed=total_uploaded,
                decisions=[{"metric": "skipped", "reason": msg}],
                current_strategy=strategy,
            )
            db.add(report)
            db.commit()
            return {
                "ran_at": now.isoformat() + "Z",
                "videos_analyzed": total_uploaded,
                "decisions": report.decisions,
                "current_strategy": strategy,
            }

        # manual_override: save an audit report but don't touch settings
        if user_settings.manual_override:
            logger.info("manual_override=True — skipping optimizer decisions")
            report = OptimizationReport(
                ran_at=now,
                videos_analyzed=total_uploaded,
                decisions=[{"metric": "skipped", "reason": "manual_override is enabled"}],
                current_strategy=strategy,
            )
            db.add(report)
            db.commit()
            return {
                "ran_at": now.isoformat() + "Z",
                "videos_analyzed": total_uploaded,
                "decisions": report.decisions,
                "current_strategy": strategy,
            }

        # Load last 30 days of uploaded videos
        cutoff = now - timedelta(days=30)
        videos = (
            db.query(Video)
            .filter(Video.status == "uploaded", Video.uploaded_at >= cutoff)
            .all()
        )

        decisions: list[dict] = []

        short_videos = [v for v in videos if v.type == "short"]
        long_videos = [v for v in videos if v.type == "long"]

        # ── 1. Shorts per day ───────────────────────────────────────────────
        mature_shorts = [
            v for v in short_videos
            if v.uploaded_at and (now - v.uploaded_at).days >= 7
        ]
        if mature_shorts:
            avg_views = sum(v.views or 0 for v in mature_shorts) / len(mature_shorts)
            old = user_settings.shorts_per_day
            new = old
            if avg_views < 500:
                new = max(1, old - 1)
                reason = f"avg views {avg_views:.0f} < 500 threshold"
            elif avg_views > 5000:
                new = min(4, old + 1)
                reason = f"avg views {avg_views:.0f} > 5000 threshold"
            else:
                reason = f"avg views {avg_views:.0f} within normal range (500–5000)"
            decisions.append({
                "metric": "shorts_per_day",
                "old": old, "new": new, "reason": reason,
            })
            if new != old:
                user_settings.shorts_per_day = new

        # ── 2. Long video interval ──────────────────────────────────────────
        mature_longs = [
            v for v in long_videos
            if v.uploaded_at and (now - v.uploaded_at).days >= 14
        ]
        if mature_longs:
            avg_views = sum(v.views or 0 for v in mature_longs) / len(mature_longs)
            old = user_settings.long_video_interval_days
            new = old
            if avg_views < 200:
                new = min(7, old + 1)
                reason = f"avg views {avg_views:.0f} < 200 threshold"
            elif avg_views > 2000:
                new = max(1, old - 1)
                reason = f"avg views {avg_views:.0f} > 2000 threshold"
            else:
                reason = f"avg views {avg_views:.0f} within normal range (200–2000)"
            decisions.append({
                "metric": "long_video_interval_days",
                "old": old, "new": new, "reason": reason,
            })
            if new != old:
                user_settings.long_video_interval_days = new

        # ── 3. Best upload hour for shorts ──────────────────────────────────
        short_hour_views: dict[int, list[int]] = defaultdict(list)
        for v in short_videos:
            if v.uploaded_at:
                short_hour_views[v.uploaded_at.hour].append(v.views or 0)

        eligible = {h: vs for h, vs in short_hour_views.items() if len(vs) >= 5}
        if eligible:
            avg_by_hour = {h: sum(vs) / len(vs) for h, vs in eligible.items()}
            best_h = max(avg_by_hour, key=avg_by_hour.__getitem__)
            cur_h = int((user_settings.upload_time_shorts or "08:00").split(":")[0])
            cur_avg = avg_by_hour.get(cur_h)
            best_avg = avg_by_hour[best_h]
            if cur_avg is not None and best_avg > cur_avg * 1.2 and best_h != cur_h:
                old = user_settings.upload_time_shorts
                new = f"{best_h:02d}:00"
                decisions.append({
                    "metric": "upload_time_shorts",
                    "old": old, "new": new,
                    "reason": f"hour {best_h} avg {best_avg:.0f} vs hour {cur_h} avg {cur_avg:.0f} (>20% diff)",
                })
                user_settings.upload_time_shorts = new

        # ── 4. Best upload hour for long videos ─────────────────────────────
        long_hour_views: dict[int, list[int]] = defaultdict(list)
        for v in long_videos:
            if v.uploaded_at:
                long_hour_views[v.uploaded_at.hour].append(v.views or 0)

        eligible_long = {h: vs for h, vs in long_hour_views.items() if len(vs) >= 5}
        if eligible_long:
            avg_by_hour = {h: sum(vs) / len(vs) for h, vs in eligible_long.items()}
            best_h = max(avg_by_hour, key=avg_by_hour.__getitem__)
            cur_h = int((user_settings.upload_time_long or "10:00").split(":")[0])
            cur_avg = avg_by_hour.get(cur_h)
            best_avg = avg_by_hour[best_h]
            if cur_avg is not None and best_avg > cur_avg * 1.2 and best_h != cur_h:
                old = user_settings.upload_time_long
                new = f"{best_h:02d}:00"
                decisions.append({
                    "metric": "upload_time_long",
                    "old": old, "new": new,
                    "reason": f"hour {best_h} avg {best_avg:.0f} vs hour {cur_h} avg {cur_avg:.0f} (>20% diff)",
                })
                user_settings.upload_time_long = new

        # ── 5. Niche theme rotation ──────────────────────────────────────────
        niche_scores: dict[str, list[float]] = defaultdict(list)
        for v in videos:
            niche = v.niche_theme
            if niche:
                niche_scores[niche].append(_score_video(v, now))

        known_niches = list(NICHES.keys())
        # Enough data per niche only if >= 3 videos each
        valid_niches = {n: scores for n, scores in niche_scores.items() if len(scores) >= 3}

        if len(valid_niches) >= 2:
            avg_niche_score = {n: sum(s) / len(s) for n, s in valid_niches.items()}
            sorted_niches = sorted(avg_niche_score, key=avg_niche_score.__getitem__)
            all_scores = list(avg_niche_score.values())
            bottom_cutoff = sorted(all_scores)[max(0, int(len(all_scores) * 0.2) - 1)]

            current_niche = user_settings.niche_theme
            current_avg = avg_niche_score.get(current_niche)

            # Cycle untried niches first
            untried = [n for n in known_niches if n not in niche_scores and n != "custom"]
            if untried:
                new_niche = untried[0]
                decisions.append({
                    "metric": "niche_theme",
                    "old": current_niche, "new": new_niche,
                    "reason": f"cycling to untried niche {new_niche}",
                })
                user_settings.niche_theme = new_niche
            elif current_avg is not None and current_avg <= bottom_cutoff:
                best_niche = sorted_niches[-1]
                if best_niche != current_niche:
                    decisions.append({
                        "metric": "niche_theme",
                        "old": current_niche, "new": best_niche,
                        "reason": (
                            f"{best_niche} score {avg_niche_score[best_niche]:.2f} "
                            f"vs {current_niche} {current_avg:.2f} (bottom 20%)"
                        ),
                    })
                    user_settings.niche_theme = best_niche

        # ── 6. Long video duration ───────────────────────────────────────────
        bucket_scores: dict[str, list[float]] = defaultdict(list)
        for v in long_videos:
            bucket = _bucket_for_duration(v.duration_seconds or 3600)
            bucket_scores[bucket].append(_score_video(v, now))

        eligible_buckets = {b: s for b, s in bucket_scores.items() if len(s) >= 4}
        if eligible_buckets:
            avg_bucket = {b: sum(s) / len(s) for b, s in eligible_buckets.items()}
            best_bucket = max(avg_bucket, key=avg_bucket.__getitem__)
            best_duration = DURATION_BUCKETS[best_bucket]
            old = user_settings.long_video_duration_minutes
            if best_duration != old:
                decisions.append({
                    "metric": "long_video_duration_minutes",
                    "old": old, "new": best_duration,
                    "reason": (
                        f"bucket {best_bucket} ({best_duration}min) "
                        f"avg score {avg_bucket[best_bucket]:.2f}"
                    ),
                })
                user_settings.long_video_duration_minutes = best_duration

        # ── 7. Best days of week (informational — recorded, not scheduled) ──
        dow_views: dict[int, list[int]] = defaultdict(list)
        for v in short_videos:
            if v.uploaded_at:
                dow_views[v.uploaded_at.weekday()].append(v.views or 0)

        if len(dow_views) >= 3:
            avg_dow = {d: sum(vs) / len(vs) for d, vs in dow_views.items()}
            sorted_dow = sorted(avg_dow, key=avg_dow.__getitem__, reverse=True)
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            top2 = [day_names[d] for d in sorted_dow[:2]]
            bottom2 = [day_names[d] for d in sorted_dow[-2:]]
            decisions.append({
                "metric": "best_days_of_week",
                "old": None, "new": top2,
                "reason": (
                    f"top performing days: {', '.join(top2)}; "
                    f"weakest: {', '.join(bottom2)}"
                ),
            })

        # Persist changes and report
        db.commit()
        db.refresh(user_settings)
        strategy = _current_strategy(user_settings)

        report = OptimizationReport(
            ran_at=now,
            videos_analyzed=len(videos),
            decisions=decisions,
            current_strategy=strategy,
        )
        db.add(report)
        db.commit()

        logger.info(
            "Optimizer ran: %d videos analyzed, %d decisions made",
            len(videos), len(decisions),
        )
        return {
            "ran_at": now.isoformat() + "Z",
            "videos_analyzed": len(videos),
            "decisions": decisions,
            "current_strategy": strategy,
        }

    def generate_optimization_report(self, db: Session) -> dict[str, Any]:
        """Return the most recent optimization report from DB."""
        report = (
            db.query(OptimizationReport)
            .order_by(OptimizationReport.ran_at.desc())
            .first()
        )
        if report is None:
            return {
                "ran_at": None,
                "videos_analyzed": 0,
                "decisions": [],
                "current_strategy": _current_strategy(get_or_create_settings(db)),
            }
        return {
            "ran_at": report.ran_at.isoformat() + "Z",
            "videos_analyzed": report.videos_analyzed,
            "decisions": report.decisions,
            "current_strategy": report.current_strategy,
        }
