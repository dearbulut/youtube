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
            "You are an elite YouTube SEO strategist specializing in viral ambient/nature content. "
            "Your titles stop scrolling, your descriptions rank on search, your tags cover every angle.\n\n"
            "TITLE RULES — all must apply:\n"
            "• Use power words: Rare, Hypnotic, Satisfying, Incredible, Unreal, Secret, Hidden, Ancient\n"
            "• Use curiosity/surprise: 'You've Never Seen...', 'Wait For It...', 'Nature Did This...'\n"
            "• Include ONE emoji at the end (not middle)\n"
            "• Must feel like something the viewer HAS to watch\n"
            "• Examples: \"Frost Crystals Forming in Real Time Will Hypnotize You ❄️\"\n"
            "           \"You've Never Heard Rain Like This Before 🌧️\"\n"
            "           \"This Lava Meets Ocean at Midnight — Unreal 🌋\"\n\n"
            "DESCRIPTION RULES:\n"
            "• First 2 lines (before 'Show more') must be a HOOK — make the viewer feel the scene\n"
            "• Then: use cases (sleep, study, focus, meditation, anxiety relief, work)\n"
            "• Then: rich keyword paragraph, timestamps for long videos\n"
            "• End with CTA: 'Subscribe for daily nature escapes'\n\n"
            "Output ONLY valid JSON, no markdown, no code fences."
        )

        if video_type == "short":
            title_limit = "60 characters"
            description_spec = (
                "150-300 words. First 2 lines = cinematic hook (describe the feeling/scene). "
                "Then use cases. Then keyword paragraph. Then CTA."
            )
            tags_spec = "list of exactly 15 YouTube tags — mix broad (relaxing nature) and specific (frost crystal macro)"
        else:
            title_limit = "70 characters, must include '1 Hour'"
            description_spec = (
                "600-1000 words. First 2 lines = cinematic hook. "
                "Then use cases (sleep/study/focus/meditation). "
                "Then timestamps every 10 minutes. Then rich keyword paragraph. Then CTA."
            )
            tags_spec = "list of exactly 15 YouTube tags — mix broad (1 hour relaxing music) and ultra-specific"

        user_prompt = (
            f"Write YouTube metadata for this {video_type} video.\n"
            f"Title: {concept.get('title', '')}\n"
            f"Scene: {concept.get('scene', '')}\n"
            f"Language: {language}\n\n"
            f"Output a JSON object with exactly these keys:\n"
            f"- title: viral, scroll-stopping title (max {title_limit})\n"
            f"- description: {description_spec}\n"
            f"- tags: {tags_spec}\n"
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
