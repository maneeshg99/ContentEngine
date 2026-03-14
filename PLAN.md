# Short-Form Content Engine — Project Plan

## Overview

An automated pipeline that sources, clips, enhances, and uploads short-form video content to TikTok, Instagram Reels, and YouTube Shorts for monetization.

---

## Architecture — 5 Core Modules

### 1. Content Sourcing & Ingestion
**What it does:** Downloads or ingests raw long-form content (podcasts, bodycam footage, etc.)

**Sources:**
- YouTube (full podcast episodes) via `yt-dlp`
- Podcast RSS feeds (audio-only, then pair with stock/avatar video)
- Public domain / Creative Commons video (bodycam, dashcam, etc.)
- User-uploaded raw footage

**Key components:**
- `sourcer/downloader.py` — downloads video/audio from URLs
- `sourcer/rss_feed.py` — polls podcast RSS feeds for new episodes
- `sourcer/metadata.py` — stores source info (title, guest, timestamps, tags)

**Storage:** Raw files stored in cloud storage (S3/GCS) with metadata in a database.

---

### 2. Clip Detection & Extraction
**What it does:** Identifies the most engaging segments from long-form content and cuts them into 30–90 second clips.

**Strategies:**
- **Transcript-based:** Use Whisper (OpenAI) to transcribe, then use an LLM to score segments by "virality" (controversial takes, emotional moments, funny bits, shocking statements)
- **Audio energy analysis:** Detect spikes in volume, laughter, applause
- **Chat/comment mining:** If available, find timestamps that generated the most live-chat or comment activity
- **Manual override:** Allow user-defined timestamp ranges

**Key components:**
- `clipper/transcriber.py` — Whisper transcription
- `clipper/scorer.py` — LLM-based virality scoring of transcript segments
- `clipper/cutter.py` — FFmpeg-based clip extraction
- `clipper/audio_analysis.py` — energy/peak detection

---

### 3. Post-Production & Enhancement
**What it does:** Makes clips look native to short-form platforms.

**Enhancements:**
- **Captions/subtitles:** Animated word-by-word captions (the #1 engagement driver)
- **Aspect ratio:** Crop/reframe to 9:16 vertical
- **Face tracking:** Keep speaker centered when cropping from 16:9
- **Branding:** Add watermark/logo, intro/outro bumpers
- **Background music:** Optional low-volume background track
- **Hooks:** Add text overlay hooks in first 2 seconds ("Wait for it...", "This changed everything")

**Key components:**
- `editor/captions.py` — generate and burn in animated captions
- `editor/reframe.py` — smart crop with face detection (MediaPipe/OpenCV)
- `editor/overlay.py` — text hooks, logos, branding
- `editor/audio_mix.py` — background music mixing
- `editor/render.py` — final FFmpeg render pipeline

---

### 4. Upload & Distribution
**What it does:** Posts finished clips to all platforms with optimized metadata.

**Platforms & APIs:**
| Platform | API / Method | Auth |
|---|---|---|
| **TikTok** | TikTok Content Posting API | OAuth 2.0 — requires approved developer app |
| **Instagram Reels** | Instagram Graph API (via Meta Business) | Facebook App + Instagram Business account |
| **YouTube Shorts** | YouTube Data API v3 | Google OAuth 2.0 + API key |

**Key components:**
- `uploader/tiktok.py` — TikTok Content Posting API integration
- `uploader/instagram.py` — Meta Graph API Reels upload
- `uploader/youtube.py` — YouTube Data API upload
- `uploader/scheduler.py` — queue and schedule posts across platforms
- `uploader/metadata_gen.py` — LLM-generated titles, descriptions, hashtags per platform

---

### 5. Analytics & Optimization
**What it does:** Tracks performance and feeds data back to improve clip selection.

**Key components:**
- `analytics/tracker.py` — pull view/like/share/comment counts from each platform API
- `analytics/dashboard.py` — simple web dashboard (Streamlit or similar)
- `analytics/feedback_loop.py` — correlate clip attributes with performance to improve the scorer

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Video processing | FFmpeg, MoviePy |
| Transcription | OpenAI Whisper (local or API) |
| LLM (scoring/metadata) | Claude API (Anthropic) |
| Face detection | MediaPipe / OpenCV |
| Captions | Whisper timestamps + custom renderer |
| Storage | S3-compatible (AWS S3, MinIO for local dev) |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Task queue | Celery + Redis (for async processing) |
| Scheduling | APScheduler or Celery Beat |
| Web dashboard | Streamlit |
| Config | YAML + environment variables |

---

## What I Need From You (Access & Credentials)

### Required — Platform API Access
1. **TikTok Developer Account**
   - Register at https://developers.tiktok.com
   - Create an app and request "Content Posting API" access
   - Provide: Client Key, Client Secret
   - **Roadblock:** TikTok requires app review before content posting is enabled. This can take days/weeks.

2. **Meta (Instagram) Developer Account**
   - Register at https://developers.facebook.com
   - Create a Meta App with Instagram Graph API permissions
   - Connect an **Instagram Business or Creator account**
   - Provide: App ID, App Secret, Access Token
   - **Roadblock:** Instagram Reels upload via API requires a Business account and approved permissions.

3. **Google (YouTube) Developer Account**
   - Create a project at https://console.cloud.google.com
   - Enable YouTube Data API v3
   - Create OAuth 2.0 credentials
   - Provide: Client ID, Client Secret
   - **Roadblock:** New API projects have a default upload quota of ~6 videos/day. You can request an increase.

### Required — AI/ML Services
4. **OpenAI API Key** (for Whisper transcription) — OR we run Whisper locally (free but needs GPU)
5. **Anthropic API Key** (for Claude-based clip scoring and metadata generation)

### Optional
6. **AWS / GCS credentials** for cloud storage (can use local filesystem for dev)
7. **Domain + hosting** if you want the analytics dashboard publicly accessible

---

## Known Roadblocks & Legal Considerations

### Legal / Copyright (THE BIG ONE)
- **Podcast clips:** Reposting clips from JRE, Diary of a CEO, etc. without permission is copyright infringement. Mitigation strategies:
  - Focus on podcasts that explicitly allow clips / have open licenses
  - Keep clips short and transformative (add commentary, captions, new framing) to strengthen fair use arguments
  - Use content that's already widely clipped without DMCA enforcement
  - Build a "permission list" of creators who encourage clip channels
  - Be prepared for DMCA takedowns — build the system to handle them gracefully
- **Bodycam/public domain:** Generally safe if sourced from public records requests or news outlets that release under open licenses

### Technical Roadblocks
- **TikTok API approval** is slow and restrictive — fallback: use browser automation (Selenium/Playwright), though this violates TOS
- **Instagram API** requires Business account — cannot upload from personal accounts
- **YouTube quota limits** — may throttle uploads; request quota increase early
- **Whisper on CPU** is slow — GPU recommended for batch processing
- **Face tracking** for reframing is computationally expensive — can pre-compute or use simpler cropping heuristics

### Monetization Requirements
| Platform | Requirement |
|---|---|
| TikTok Creator Fund | 10K followers, 100K views in last 30 days |
| Instagram Reels Bonuses | Invite-only (Meta selects eligible creators) |
| YouTube Shorts RPM | 1K subscribers + 10M Shorts views in 90 days, must join YPP |

---

## Proposed Development Phases

### Phase 1 — Foundation (Week 1-2)
- [ ] Project scaffolding (config, database models, CLI)
- [ ] Content downloader (`yt-dlp` integration)
- [ ] Whisper transcription pipeline
- [ ] Basic clip extraction (manual timestamps)

### Phase 2 — Smart Clipping (Week 3-4)
- [ ] LLM-based virality scorer
- [ ] Audio energy analysis
- [ ] Automated clip selection pipeline

### Phase 3 — Post-Production (Week 5-6)
- [ ] 9:16 reframing with face detection
- [ ] Animated caption generation
- [ ] Text hook overlays
- [ ] Branding/watermark system

### Phase 4 — Upload & Distribution (Week 7-8)
- [ ] YouTube Shorts upload integration
- [ ] TikTok upload integration
- [ ] Instagram Reels upload integration
- [ ] Scheduling and queue system
- [ ] LLM-generated metadata (titles, hashtags, descriptions)

### Phase 5 — Analytics & Optimization (Week 9-10)
- [ ] Performance tracking from platform APIs
- [ ] Dashboard
- [ ] Feedback loop to scorer

---

## Immediate Next Steps

1. **You:** Set up developer accounts on TikTok, Meta, and Google (this takes time due to approval processes — start now)
2. **Me:** Scaffold the project, build the downloader + transcription + clipping pipeline (Phases 1-2) — no API keys needed for this
3. **You:** Decide on Whisper approach: local (needs GPU) vs. OpenAI API (costs ~$0.006/min)
4. **You:** Provide an Anthropic API key for Claude-based scoring/metadata generation
