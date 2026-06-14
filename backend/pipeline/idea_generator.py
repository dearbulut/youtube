import json
from datetime import datetime

import anthropic

from config import settings, NICHES, decrypt_value, COST_CLAUDE_INPUT_PER_MTOK, COST_CLAUDE_OUTPUT_PER_MTOK
from models.video import Video, Job
from models.settings import get_or_create_settings

YOUTUBE_CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}


async def generate_idea(db, video_id: int, video_type: str) -> dict:
    video = db.query(Video).filter(Video.id == video_id).first()

    job = Job(video_id=video_id, step="generate_idea", status="running")
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        video.status = "generating_idea"
        db.commit()

        user_settings = get_or_create_settings(db)

        api_key = (
            decrypt_value(user_settings.anthropic_api_key)
            if user_settings.anthropic_api_key
            else settings.anthropic_api_key
        )

        recent_titles = (
            db.query(Video.title)
            .filter(Video.uploaded_at.isnot(None))
            .order_by(Video.uploaded_at.desc())
            .limit(30)
            .all()
        )
        existing_titles = [row.title for row in recent_titles if row.title]

        if user_settings.niche_theme == "custom":
            niche_description = user_settings.custom_niche_description or ""
        else:
            niche_description = NICHES.get(user_settings.niche_theme, "")

        client = anthropic.Anthropic(api_key=api_key)

        categories_list = ", ".join(f"{k}={v}" for k, v in YOUTUBE_CATEGORIES.items())
        system_prompt = (
            "You are a YouTube content strategist specializing in ambient and satisfying nature content. "
            "Generate unique video concepts that vary in location, season, time of day, weather, and texture. "
            "Never repeat themes from the provided existing_titles list. "
            "Also select the most appropriate YouTube category_id for this content: "
            "Nature/ambient/ASMR → 19 (Travel & Events) or 22 (People & Blogs); "
            "Music-forward → 10 (Music); Educational/explainer → 27 (Education). "
            f"Available categories: {categories_list}. "
            "Output ONLY valid JSON, no markdown."
        )

        if video_type == "short":
            user_prompt = (
                f"Niche: {niche_description}\n"
                f"Existing titles (do not repeat): {json.dumps(existing_titles)}\n\n"
                "Generate a YouTube Short video concept. Output a JSON object with exactly these keys:\n"
                "- scene: vivid visual scene description (100 words)\n"
                "- audio_description: describe the sounds and ambient audio\n"
                "- title: catchy title (max 60 characters)\n"
                "- hook: opening 3-second visual/audio description to hook viewers\n"
                "- thumbnail_concept: thumbnail visual description (30 words)\n"
                "- category_id: best YouTube category ID string for this content"
            )
        else:
            user_prompt = (
                f"Niche: {niche_description}\n"
                f"Existing titles (do not repeat): {json.dumps(existing_titles)}\n\n"
                "Generate a 1-hour YouTube long-form ambient video concept. Output a JSON object with exactly these keys:\n"
                "- scene: rich visual scene description (150 words)\n"
                "- audio_style: music mood and ambient sounds suitable for 60 minutes\n"
                "- title: descriptive title (max 70 characters, must include '1 Hour')\n"
                "- thumbnail_concept: thumbnail visual description (30 words)\n"
                "- tags: list of 15 relevant YouTube tags\n"
                "- category_id: best YouTube category ID string for this content"
            )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = response.content[0].text
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        if raw.endswith("```"):
            raw = raw[:-3].strip()
        concept = json.loads(raw)

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens / 1e6 * COST_CLAUDE_INPUT_PER_MTOK) + (
            output_tokens / 1e6 * COST_CLAUDE_OUTPUT_PER_MTOK
        )

        video.concept = concept
        video.cost_usd = (video.cost_usd or 0.0) + cost
        video.niche_theme = user_settings.niche_theme

        job.status = "done"
        job.finished_at = datetime.utcnow()
        db.commit()

        return concept

    except Exception as e:
        job.status = "failed"
        job.log = str(e)
        job.finished_at = datetime.utcnow()
        video.status = "failed"
        video.error_message = str(e)
        db.commit()
        raise
