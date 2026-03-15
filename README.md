# ContentEngine

Automated pipeline that takes a video URL and produces ready-to-post short-form clips with animated captions, 9:16 reframing, and hook overlays — optimized for TikTok, Instagram Reels, and YouTube Shorts.

## Requirements

- **Python 3.11+**
- **FFmpeg** — for all video/audio processing

```bash
# Ubuntu/Debian/WSL
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## Installation

```bash
git clone <repo-url> && cd ContentEngine
pip install -e .
content-engine init
```

This creates the database and storage directories (`data/raw`, `data/clips`, `data/rendered`, `data/transcripts`).

## Quick Start — One Command

The `process` command runs the full pipeline: **download → transcribe → find best clips → render**.

```bash
content-engine process "https://www.youtube.com/watch?v=VIDEO_ID"
```

That's it. Clips land in `data/rendered/`.

### Options

```bash
# Extract top 3 clips with a custom hook overlay
content-engine process "https://youtube.com/watch?v=..." --top-n 3 --hook "Wait for it..."

# Use auto-generated hooks from clip scoring
content-engine process "https://youtube.com/watch?v=..." --hook auto

# Skip reframing (keep original aspect ratio)
content-engine process "https://youtube.com/watch?v=..." --no-reframe

# Skip captions
content-engine process "https://youtube.com/watch?v=..." --no-captions

# Extract clips only (no rendering)
content-engine process "https://youtube.com/watch?v=..." --no-render

# Add a watermark
content-engine process "https://youtube.com/watch?v=..." --watermark path/to/logo.png

# Use LLM scoring (better quality, requires API key)
content-engine process "https://youtube.com/watch?v=..." --api-key sk-ant-...
```

## Scoring Modes

### Free — Local Heuristic Scoring (default)

Works out of the box with no API key. Scores clips based on:
- Keyword pattern matching (controversy, emotion, story hooks, quotability)
- Sentence structure analysis (punchy vs. rambly)
- Audio energy peaks (volume spikes, laughter, applause)

Good enough for testing and general use.

### LLM Scoring (optional, better quality)

Uses Claude to analyze each transcript segment for virality potential. Set the API key to enable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
content-engine process "https://youtube.com/watch?v=..."
```

Or pass it per-command: `--api-key sk-ant-...`

The engine auto-detects which mode to use. If no key is found, it silently falls back to heuristic scoring.

## Step-by-Step Commands

If you prefer running each stage manually:

```bash
# 1. Download a source video
content-engine download "https://youtube.com/watch?v=..."

# 2. Transcribe it (uses Whisper locally)
content-engine transcribe 1

# 3. Auto-find best clips
content-engine auto-clip 1 --top-n 5

# 4. Render a specific clip with post-production
content-engine render 1 --hook "This changed everything"

# Or extract a clip manually by timestamp
content-engine clip 1 --start 120.0 --end 180.0 --title "Best moment"
```

## Listing Sources and Clips

```bash
content-engine list --type sources
content-engine list --type clips
```

## What the Render Pipeline Does

When you run `process` or `render`, each clip goes through:

1. **9:16 Reframing** — Crops landscape video to portrait with face detection (MediaPipe). Keeps speakers centered. Falls back to center crop if no faces detected.
2. **Animated Captions** — TikTok-style word-by-word highlighted captions generated from Whisper timestamps. Burns them directly into the video.
3. **Hook Overlay** — Text overlay in the first 2.5 seconds with fade-in/out (e.g., "Wait for it...").
4. **Watermark** — Optional logo/branding overlay (PNG with transparency).

Each step can be toggled on/off individually.

## Configuration

All settings are in `config.yaml`:

```yaml
storage:
  raw_dir: "data/raw"
  clips_dir: "data/clips"
  rendered_dir: "data/rendered"
  transcripts_dir: "data/transcripts"

whisper:
  model: "base"       # tiny, base, small, medium, large
  device: "cpu"        # cpu or cuda (cuda also works for AMD ROCm)

clipper:
  min_duration: 30     # seconds
  max_duration: 90     # seconds

editor:
  reframe: true
  captions: true
  caption_font: "Arial"
  caption_font_size: 20
  caption_uppercase: true
  caption_words_per_group: 4
  watermark_path: ""
  watermark_position: "top-right"
  watermark_opacity: 0.7
```

## GPU Acceleration

### AMD ROCm (RX 6700 XT / 6750 XT)

See [docs/gpu-setup.md](docs/gpu-setup.md) or run:

```bash
bash scripts/setup_rocm.sh
```

Then set `device: "cuda"` in `config.yaml` (ROCm uses PyTorch's CUDA interface).

### NVIDIA

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

Then set `device: "cuda"` in `config.yaml`.

## Project Structure

```
content_engine/
├── sourcer/          # Content ingestion (yt-dlp downloader)
├── clipper/          # Clip detection & extraction
│   ├── transcriber.py    # Whisper transcription
│   ├── scorer.py         # LLM virality scoring (Claude)
│   ├── heuristic_scorer.py  # Local scoring (no API needed)
│   ├── audio_analysis.py    # Energy peak detection
│   ├── cutter.py         # FFmpeg clip extraction
│   └── pipeline.py       # Auto-clip orchestration
├── editor/           # Post-production
│   ├── reframe.py        # 9:16 face-tracked reframing
│   ├── captions.py       # Animated word-by-word captions
│   ├── overlay.py        # Hook text & watermark overlays
│   └── render.py         # Render pipeline orchestration
├── cli.py            # CLI commands
├── config.py         # Configuration models
└── database.py       # SQLAlchemy models
```

## Supported Input Sources

The downloader uses `yt-dlp`, which supports 1000+ sites including:
- YouTube
- Vimeo
- Twitter/X
- Reddit
- Twitch VODs
- Direct video URLs

Full list: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```
