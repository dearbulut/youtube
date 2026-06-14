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
            "You are an elite YouTube content strategist creating viral ambient nature content. "
            "Generate hyper-specific, cinematically vivid video concepts that feel like award-winning documentary moments.\n\n"
            "MANDATORY RULES — violating any of these is unacceptable:\n"
            "• NEVER write generic scenes: no 'peaceful forest', 'calm lake', 'beautiful sunset', 'serene river', 'relaxing nature'\n"
            "• ALWAYS use ultra-specific micro-niches with precise sensory detail:\n"
            "  ✓ 'single raindrop hitting still puddle in extreme macro at 5am, cold blue light'\n"
            "  ✓ 'lava fingers meeting dark ocean creating white steam at midnight, Hawaii'\n"
            "  ✓ 'frost crystals forming on spider web at -3°C at dawn, backlit by winter sun'\n"
            "  ✓ 'bioluminescent plankton washing over black sand beach at 2am, New Zealand'\n"
            "  ✓ 'morning dew drops rolling off succulent leaves in slow motion, golden 6am light'\n"
            "• Always specify: exact time of day, season, weather, temperature, light color/direction\n"
            "• The scene_description MUST open with the single most visually striking frame — the moment that stops scrolling\n"
            "• Formats that dominate: extreme macro textures, ultra-slow-motion water/fire/ice, satisfying seamless loops, ASMR-inducing close-ups\n"
            "• Think: what one frame would get 10M views as a thumbnail? Start there.\n\n"
            f"YouTube categories: {categories_list}\n"
            "Select category_id: ambient/ASMR/nature → '19' or '22'; music-forward → '10'; educational → '27'.\n"
            "Output ONLY valid JSON — no markdown, no code fences, no extra text."
        )

        if video_type == "short":
            user_prompt = (
                f"Niche: {niche_description}\n"
                f"Do NOT repeat any of these existing titles: {json.dumps(existing_titles)}\n\n"
                "Generate a YouTube Shorts concept (50 seconds, vertical 9:16). "
                "Output a JSON object with EXACTLY these keys:\n"
                "- scene: hyper-specific cinematic scene description starting with the hook moment (120 words). "
                "Include exact time, lighting, temperature, textures, and motion details.\n"
                "- hook: the single most visually arresting opening frame — describe it in 1 sentence as if briefing a cinematographer\n"
                "- audio_description: specific ambient sounds (not music) — water frequency, wind texture, material sounds\n"
                "- title: scroll-stopping title (max 60 chars) with power words and ONE emoji at end\n"
                "- thumbnail_concept: exact single frame to photograph for thumbnail — ultra-specific composition (40 words)\n"
                "- category_id: YouTube category ID string"
            )
        else:
            user_prompt = (
                f"Niche: {niche_description}\n"
                f"Do NOT repeat any of these existing titles: {json.dumps(existing_titles)}\n\n"
                "Generate a 1-hour YouTube long-form ambient video concept. "
                "Output a JSON object with EXACTLY these keys:\n"
                "- scene: rich cinematic scene description with progression through time (200 words). "
                "Start with the most striking visual moment. Include lighting shifts, seasonal detail, micro and macro elements.\n"
                "- audio_style: specific music mood, BPM range, instruments, and layered ambient sounds for 60 minutes\n"
                "- title: compelling title (max 70 chars, must include '1 Hour') with power words and ONE emoji\n"
                "- thumbnail_concept: exact single frame for thumbnail — ultra-specific composition (40 words)\n"
                "- tags: list of exactly 15 YouTube tags\n"
                "- category_id: YouTube category ID string"
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
