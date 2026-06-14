import json
from datetime import datetime

import anthropic

from config import settings, decrypt_value, COST_CLAUDE_INPUT_PER_MTOK, COST_CLAUDE_OUTPUT_PER_MTOK
from models.video import Video, Job
from models.settings import get_or_create_settings


async def write_seo(db, video_id: int) -> dict:
    video = db.query(Video).filter(Video.id == video_id).first()

    job = Job(video_id=video_id, step="write_seo", status="running")
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        video.status = "writing_seo"
        db.commit()

        user_settings = get_or_create_settings(db)

        api_key = (
            decrypt_value(user_settings.anthropic_api_key)
            if user_settings.anthropic_api_key
            else settings.anthropic_api_key
        )

        language = user_settings.language or settings.language or "en"
        concept = video.concept or {}
        video_type = video.type or "short"

        client = anthropic.Anthropic(api_key=api_key)

        system_prompt = (
            "You are a YouTube SEO expert. Write metadata that maximizes discoverability. "
            "Focus on search intent, emotional triggers (relaxing, sleep, study, focus, meditation). "
            "Output ONLY valid JSON, no markdown."
        )

        if video_type == "short":
            title_limit = "60 characters"
            description_spec = "200-400 words with a strong hook, use cases, keywords, and a CTA"
        else:
            title_limit = "70 characters"
            description_spec = "800-1200 words with a strong hook, use cases (sleep/study/focus/meditation), rich keywords, and a CTA"

        user_prompt = (
            f"Write YouTube metadata for this {video_type} video.\n"
            f"Title: {concept.get('title', '')}\n"
            f"Scene: {concept.get('scene', '')}\n"
            f"Language: {language}\n\n"
            f"Output a JSON object with exactly these keys:\n"
            f"- title: SEO-optimized title (max {title_limit})\n"
            f"- description: {description_spec}\n"
            f"- tags: list of up to 30 relevant YouTube tags\n"
            f"- hashtags: list of exactly 3 hashtags (e.g. [\"#relaxing\", \"#ambient\", \"#sleep\"])"
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"): raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"): raw = raw[:-3].strip()
        seo = json.loads(raw)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens / 1e6 * COST_CLAUDE_INPUT_PER_MTOK) + (
            output_tokens / 1e6 * COST_CLAUDE_OUTPUT_PER_MTOK
        )

        video.title = seo.get("title", video.title)
        video.description = seo.get("description", video.description)
        video.tags = seo.get("tags", video.tags)
        video.cost_usd = (video.cost_usd or 0.0) + cost

        job.status = "done"
        job.finished_at = datetime.utcnow()
        db.commit()

        return seo

    except Exception as e:
        job.status = "failed"
        job.log = str(e)
        job.finished_at = datetime.utcnow()
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        raise
