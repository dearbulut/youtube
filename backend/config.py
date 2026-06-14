import os
import hashlib
import base64
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

NICHES = {
    "nature_ambient": "Macro close-up shots of nature: water droplets, leaves, moss, rain on surfaces, flowing streams, morning dew, forest textures. Peaceful, meditative, no people.",
    "cozy_indoor": "Cozy atmospheric indoor scenes: rain on windows, fireplace, candles, tea steam, reading nooks, rainy cafe windows, winter blankets. Warm, intimate, no faces.",
    "ocean_beach": "Ocean and coastal scenes: waves breaking on shore, tide pools, pebbles, sand patterns, coastal fog, lighthouse, sea glass. Calming, rhythmic.",
    "forest_mountain": "Forest and mountain environments: sunlight through trees, mountain streams, pine needles, snowfall, autumn leaves falling, morning mist. Serene, epic.",
    "japanese_zen": "Japanese aesthetic: zen gardens, bamboo, cherry blossoms, koi ponds, moss gardens, temple bells, paper lanterns, stone paths. Minimalist, meditative.",
    "winter_snow": "Winter and snow scenes: snowfall close-ups, frost patterns on glass, icicles, frozen lakes, snow on pine branches, winter light. Crisp, peaceful.",
    "custom": "",
}

COST_DALLE3_HD = 0.080
COST_CLAUDE_INPUT_PER_MTOK = 3.0
COST_CLAUDE_OUTPUT_PER_MTOK = 15.0
COST_SUNO_PER_SONG = 0.07


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    fal_key: str = ""
    apiframe_key: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    secret_key: str = "change-this-to-a-random-32-char-string"
    database_url: str = "sqlite:///./storage/db/tubeauto.db"
    temp_dir: str = "./storage/temp"
    thumbnail_dir: str = "./storage/thumbnails"
    base_url: str = "http://localhost:8000"
    shorts_per_day: int = 2
    long_videos_interval_days: int = 2
    long_video_duration_minutes: int = 60
    shorts_duration_seconds: int = 50
    upload_time_shorts: str = "08:00"
    upload_time_long: str = "10:00"
    niche_theme: str = "nature_ambient"
    language: str = "en"


settings = Settings()

Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
Path(settings.thumbnail_dir).mkdir(parents=True, exist_ok=True)
Path("./storage/db").mkdir(parents=True, exist_ok=True)


def _get_fernet() -> Fernet:
    key_bytes = hashlib.sha256(settings.secret_key.encode()).digest()
    encoded_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(encoded_key)


def encrypt_value(value: str) -> str:
    if not value:
        return value
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    if not value:
        return value
    try:
        f = _get_fernet()
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value
