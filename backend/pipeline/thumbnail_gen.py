import asyncio
import os
import io
import httpx
import openai
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

from config import settings, decrypt_value, COST_DALLE3_HD
from database import SessionLocal
from models.video import Video, Job
from models.settings import get_or_create_settings
from utils.file_manager import get_thumbnail_path


_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_FONT_SIZE = 48
_MAX_LINES = 2
_THUMB_W, _THUMB_H = 1280, 720
_BOTTOM_BAND_FRACTION = 0.20
_PILL_ALPHA = 160
_PILL_PADDING_X = 24
_PILL_PADDING_Y = 14
_LINE_SPACING = 8


def _load_font(size: int = _FONT_SIZE):
    try:
        return ImageFont.truetype(_FONT_PATH, size)
    except (IOError, OSError):
        return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int):
    words = text.split()
    lines = []
    current = []

    for word in words:
        test_line = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
        if len(lines) >= _MAX_LINES:
            break

    if current and len(lines) < _MAX_LINES:
        lines.append(" ".join(current))

    if not lines:
        return [text]

    if len(lines) > _MAX_LINES:
        lines = lines[:_MAX_LINES]
        last = lines[-1]
        while last:
            test = last + "..."
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width:
                lines[-1] = test
                break
            last = last[:-1]

    return lines


def _add_text_overlay(img: Image.Image, title: str) -> Image.Image:
    img = img.convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font = _load_font(_FONT_SIZE)
    max_text_width = int(_THUMB_W * 0.85)
    lines = _wrap_text(draw, title, font, max_text_width)

    line_heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_heights.append(bbox[3] - bbox[1])

    total_text_height = sum(line_heights) + _LINE_SPACING * (len(lines) - 1)
    band_top = int(_THUMB_H * (1 - _BOTTOM_BAND_FRACTION))
    band_center_y = band_top + (_THUMB_H - band_top) // 2

    pill_h = total_text_height + _PILL_PADDING_Y * 2
    pill_top = band_center_y - pill_h // 2
    pill_bottom = pill_top + pill_h

    max_line_width = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        if w > max_line_width:
            max_line_width = w

    pill_left = (_THUMB_W - max_line_width) // 2 - _PILL_PADDING_X
    pill_right = (_THUMB_W + max_line_width) // 2 + _PILL_PADDING_X

    radius = min(pill_h // 2, 20)
    draw.rounded_rectangle(
        [pill_left, pill_top, pill_right, pill_bottom],
        radius=radius,
        fill=(0, 0, 0, _PILL_ALPHA),
    )

    y_cursor = pill_top + _PILL_PADDING_Y
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (_THUMB_W - line_w) // 2
        draw.text((x, y_cursor), line, font=font, fill=(255, 255, 255, 255))
        y_cursor += line_heights[i] + _LINE_SPACING

    combined = Image.alpha_composite(img, overlay)
    return combined.convert("RGB")


async def generate_thumbnail(db, video_id: int) -> str:
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise ValueError(f"Video {video_id} not found")

    job = Job(
        video_id=video_id,
        step="generate_thumbnail",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    video.status = "generating_thumbnail"
    db.commit()

    try:
        user_settings = get_or_create_settings(db)
        raw_key = getattr(user_settings, "openai_api_key", None)
        openai_api_key = (
            decrypt_value(raw_key) if raw_key else None
        ) or settings.openai_api_key

        concept = video.concept or {}
        thumbnail_concept = concept.get(
            "thumbnail_concept", "beautiful nature scene"
        )
        title = video.title or "Untitled"

        client = openai.AsyncOpenAI(api_key=openai_api_key)

        dalle_prompt = (
            f"Cinematic, photorealistic thumbnail for YouTube: {thumbnail_concept}. "
            "Ultra high detail, soft natural lighting, 4K quality. "
            "No text, no watermarks, no logos. "
            "Composition: rule of thirds, high contrast, visually striking. "
            "Style: National Geographic quality nature photography."
        )

        response = await client.images.generate(
            model="gpt-image-1",
            prompt=dalle_prompt,
            size="1536x1024",
            quality="high",
            n=1,
        )

        import base64
        b64 = getattr(response.data[0], 'b64_json', None)
        if b64:
            image_bytes = base64.b64decode(b64)
        else:
            image_url = response.data[0].url
            async with httpx.AsyncClient(timeout=60.0) as dl_client:
                img_resp = await dl_client.get(image_url)
                img_resp.raise_for_status()
                image_bytes = img_resp.content

        img = Image.open(io.BytesIO(image_bytes))
        img = img.resize((_THUMB_W, _THUMB_H), Image.LANCZOS)
        img = _add_text_overlay(img, title)

        thumb_path = get_thumbnail_path(f"thumb_{video_id}.jpg")
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        img.save(thumb_path, "JPEG", quality=95)

        video.thumbnail_path = thumb_path
        video.cost_usd = (video.cost_usd or 0.0) + COST_DALLE3_HD

        job.status = "done"
        job.finished_at = datetime.utcnow()
        db.commit()

        return thumb_path

    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.finished_at = datetime.utcnow()
        video.status = "failed"
        db.commit()
        raise
