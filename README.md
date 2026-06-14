# TubeAuto - Automated YouTube Channel Manager

A fully automated YouTube channel management system that leverages multiple AI services to generate, produce, and publish videos with minimal human intervention.

## Features

- **AI-powered video concept generation** (Claude claude-sonnet-4-6) — generates unique, SEO-friendly video ideas with anti-repetition tracking across 14k+ content combinations
- **Automated video production** (fal.ai Kling) — text-to-video generation for short clips and multi-segment long-form content
- **Background music generation** (Suno via Apiframe) — automatically adds matching background music for long videos
- **AI thumbnail generation** (DALL-E 3 + Pillow) — creates eye-catching thumbnails with text overlays
- **SEO-optimized metadata** (Claude claude-sonnet-4-6) — titles, descriptions, and tags optimized for YouTube discovery
- **Automatic YouTube upload** with OAuth 2.0 — hands-free publishing directly to your channel
- **Web dashboard** for monitoring and control — real-time pipeline status, video history, and manual triggers
- **Budget management** — daily spending caps to control API costs across all services
- **Anti-repetition system** — tracks 14k+ unique content combinations to ensure fresh ideas every time

## Quick Start

1. Copy `.env.example` to `.env` and fill in your API keys:
   ```bash
   cp .env.example .env
   ```

2. Start all services with Docker Compose:
   ```bash
   docker-compose up
   ```

3. Visit the dashboard at [http://localhost:3000](http://localhost:3000)

4. Connect your YouTube account via **Settings** and complete the OAuth flow

## API Keys Required

| Service | Where to get it |
|---------|----------------|
| Anthropic API key | [claude.ai](https://claude.ai) / [console.anthropic.com](https://console.anthropic.com) |
| OpenAI API key | [platform.openai.com](https://platform.openai.com) |
| fal.ai key | [fal.ai](https://fal.ai) |
| Apiframe key (Suno) | [apiframe.pro](https://apiframe.pro) |
| Google OAuth credentials | [console.cloud.google.com](https://console.cloud.google.com) |

## Architecture

```
Backend:  FastAPI + SQLite + APScheduler
Frontend: React 18 + Vite + TailwindCSS
Pipeline: 6-step AI content production
```

### Production Pipeline

1. **Concept Generation** — Claude generates a unique video idea
2. **Script Writing** — Claude writes a narration script with scene descriptions
3. **Video Generation** — fal.ai Kling converts scenes to video clips
4. **Music Generation** — Suno creates background audio (long videos only)
5. **Thumbnail Creation** — DALL-E 3 generates artwork, Pillow composites text
6. **Upload & Publish** — Metadata finalized and video uploaded to YouTube

## Cost Estimates

| Video Type | Services Used | Estimated Cost |
|------------|--------------|----------------|
| Short video | Kling + DALL-E 3 + Claude | ~$0.15 – $0.20 |
| Long video | 6x Kling + Suno + DALL-E 3 + Claude | ~$0.35 – $0.50 |

Default daily budget: **$5.00** (configurable in `.env`)

## Manual Triggers

Use the dashboard buttons **"Generate Short Now"** and **"Generate Long Now"** for on-demand production.

Or call the API directly:

```bash
# Trigger a short video
curl -X POST http://localhost:8000/videos/trigger/short

# Trigger a long video
curl -X POST http://localhost:8000/videos/trigger/long
```

## Configuration

Key environment variables in `.env`:

```env
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
FAL_KEY=...
APIFRAME_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

DAILY_BUDGET_USD=5.00
SHORT_VIDEO_SCHEDULE=0 10 * * *    # daily at 10:00
LONG_VIDEO_SCHEDULE=0 15 * * 1,4  # Mon & Thu at 15:00
```

## Development

Run services individually without Docker:

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Storage Layout

```
storage/
  db/         SQLite database
  temp/       Intermediate video/audio files
  thumbnails/ Generated thumbnail images
```
