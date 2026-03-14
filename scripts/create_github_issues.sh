#!/bin/bash
# Run this locally where you have `gh` authenticated:
#   chmod +x scripts/create_github_issues.sh
#   ./scripts/create_github_issues.sh
#
# Prerequisites:
#   gh auth login
#   gh project create --title "Content Engine" --owner @me

set -e

REPO="maneeshg99/ContentEngine"

echo "Creating GitHub issues for Content Engine..."

# ── Phase 1: Foundation (DONE) ──────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "[Phase 1] Project scaffolding — config, DB models, CLI" \
  --label "phase-1,done" \
  --body "$(cat <<'EOF'
## Tasks
- [x] Pydantic config with YAML loading
- [x] SQLAlchemy models: Source, Clip, PlatformAccount
- [x] CLI entry point with Click (init, download, transcribe, clip, list)
- [x] Tests for config and database layers

**Status:** Complete
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 1] Content downloader — yt-dlp integration" \
  --label "phase-1,done" \
  --body "$(cat <<'EOF'
## Tasks
- [x] yt-dlp wrapper with metadata extraction
- [x] Auto-register downloaded sources in database
- [x] Configurable format and rate limiting

**Status:** Complete
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 1] Whisper transcription pipeline" \
  --label "phase-1,done" \
  --body "$(cat <<'EOF'
## Tasks
- [x] Whisper integration with word-level timestamps
- [x] JSON transcript output with segments and words
- [x] Configurable model size and device (CPU/GPU)

**Status:** Complete
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 1] FFmpeg clip extraction" \
  --label "phase-1,done" \
  --body "$(cat <<'EOF'
## Tasks
- [x] FFmpeg-based clip cutter with re-encoding for platform compatibility
- [x] Duration validation (min/max from config)
- [x] Audio energy peak detection for finding engaging moments

**Status:** Complete
EOF
)"

# ── Phase 2: Smart Clipping ─────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "[Phase 2] LLM-based virality scorer" \
  --label "phase-2,in-progress" \
  --body "$(cat <<'EOF'
## Description
Use Claude API to analyze transcript segments and score them by viral potential.

## Tasks
- [ ] Segment transcript into candidate windows
- [ ] Build scoring prompt (controversy, emotion, humor, shock value)
- [ ] Parse structured LLM output into scored segments
- [ ] Rank and filter segments by score threshold

## Dependencies
- Anthropic API key
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 2] Automated clip selection pipeline" \
  --label "phase-2,in-progress" \
  --body "$(cat <<'EOF'
## Description
End-to-end pipeline: transcribe → score → select → cut best clips automatically.

## Tasks
- [ ] Combine transcript scoring + audio energy into unified ranking
- [ ] Auto-select top N clips per source
- [ ] CLI command: `content-engine auto-clip <source_id>`
- [ ] Pipeline orchestration with status tracking

## Dependencies
- Virality scorer
- Transcription pipeline
EOF
)"

# ── Phase 3: Post-Production ────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "[Phase 3] 9:16 vertical reframing with face detection" \
  --label "phase-3,backlog" \
  --body "$(cat <<'EOF'
## Description
Smart crop from 16:9 → 9:16 keeping the speaker centered using face detection.

## Tasks
- [ ] MediaPipe/OpenCV face detection
- [ ] Dynamic crop window tracking speaker position
- [ ] Fallback to center-crop when no face detected
- [ ] FFmpeg filter chain for reframing
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 3] Animated caption generation" \
  --label "phase-3,backlog" \
  --body "$(cat <<'EOF'
## Description
Word-by-word animated captions — the #1 engagement driver on short-form content.

## Tasks
- [ ] Use Whisper word timestamps for precise alignment
- [ ] Render captions with highlight/pop animation per word
- [ ] Configurable font, color, position, style
- [ ] Burn into video via FFmpeg drawtext or Pillow overlay
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 3] Text hook overlays and branding" \
  --label "phase-3,backlog" \
  --body "$(cat <<'EOF'
## Tasks
- [ ] First-2-second text hooks ("Wait for it...", "This changed everything")
- [ ] Logo/watermark overlay
- [ ] Intro/outro bumpers
- [ ] Background music mixing
EOF
)"

# ── Phase 4: Upload & Distribution ──────────────────────────────────

gh issue create --repo "$REPO" \
  --title "[Phase 4] YouTube Shorts upload integration" \
  --label "phase-4,backlog" \
  --body "$(cat <<'EOF'
## Tasks
- [ ] YouTube Data API v3 OAuth flow
- [ ] Upload with title, description, tags, #Shorts
- [ ] Multi-account support via PlatformAccount
- [ ] Quota tracking and rate limiting

## Prereqs (your tasks)
- [ ] Google Cloud project with YouTube Data API enabled
- [ ] OAuth 2.0 credentials created
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 4] TikTok upload integration" \
  --label "phase-4,backlog" \
  --body "$(cat <<'EOF'
## Tasks
- [ ] TikTok Content Posting API OAuth flow
- [ ] Video upload with caption and hashtags
- [ ] Multi-account support
- [ ] Handle API approval delays

## Prereqs (your tasks)
- [ ] TikTok developer app with Content Posting API approved
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 4] Instagram Reels upload integration" \
  --label "phase-4,backlog" \
  --body "$(cat <<'EOF'
## Tasks
- [ ] Meta Graph API integration for Reels
- [ ] Upload with caption and hashtags
- [ ] Multi-account support
- [ ] Instagram Business account requirement

## Prereqs (your tasks)
- [ ] Meta developer app with Instagram Graph API permissions
- [ ] Instagram Business or Creator account linked
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Phase 4] Upload scheduler and queue" \
  --label "phase-4,backlog" \
  --body "$(cat <<'EOF'
## Tasks
- [ ] Schedule posts across platforms with configurable timing
- [ ] Round-robin across multiple accounts
- [ ] LLM-generated titles, descriptions, hashtags per platform
- [ ] Retry logic and failure handling
EOF
)"

# ── Phase 5: Analytics ──────────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "[Phase 5] Performance analytics and feedback loop" \
  --label "phase-5,backlog" \
  --body "$(cat <<'EOF'
## Tasks
- [ ] Pull view/like/share/comment counts from each platform API
- [ ] Streamlit dashboard for performance visualization
- [ ] Correlate clip attributes with performance metrics
- [ ] Feed performance data back to virality scorer for improvement
EOF
)"

# ── Your Tasks (API Access) ─────────────────────────────────────────

gh issue create --repo "$REPO" \
  --title "[Setup] Register TikTok developer app" \
  --label "setup,owner-task" \
  --assignee "@me" \
  --body "$(cat <<'EOF'
## Steps
1. Register at https://developers.tiktok.com
2. Create an app
3. Request "Content Posting API" access
4. Save Client Key and Client Secret

**Note:** App review can take days/weeks. Start early.
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Setup] Register Meta developer app (Instagram)" \
  --label "setup,owner-task" \
  --assignee "@me" \
  --body "$(cat <<'EOF'
## Steps
1. Register at https://developers.facebook.com
2. Create a Meta App with Instagram Graph API
3. Connect an Instagram Business or Creator account
4. Save App ID, App Secret, Access Token

**Note:** Requires Instagram Business account (not personal).
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Setup] Create Google Cloud project (YouTube)" \
  --label "setup,owner-task" \
  --assignee "@me" \
  --body "$(cat <<'EOF'
## Steps
1. Create project at https://console.cloud.google.com
2. Enable YouTube Data API v3
3. Create OAuth 2.0 credentials
4. Save Client ID and Client Secret

**Note:** Default upload quota is ~6 videos/day. Request increase early.
EOF
)"

gh issue create --repo "$REPO" \
  --title "[Setup] Obtain API keys (Anthropic + OpenAI)" \
  --label "setup,owner-task" \
  --assignee "@me" \
  --body "$(cat <<'EOF'
## Keys Needed
- [ ] Anthropic API key (for Claude-based virality scoring and metadata generation)
- [ ] OpenAI API key (for Whisper API — optional if running Whisper locally with ROCm GPU)

## GPU Note
AMD RX 6700 XT detected — Whisper can run locally via PyTorch ROCm.
Install: `pip install torch --index-url https://download.pytorch.org/whl/rocm6.0`
This eliminates the need for OpenAI API costs for transcription.
EOF
)"

echo ""
echo "✅ All issues created! Now create a Project Board:"
echo "   gh project create --title 'Content Engine' --owner @me"
echo "   Then add issues to the board via the GitHub UI or:"
echo "   gh project item-add <PROJECT_NUMBER> --owner @me --url <ISSUE_URL>"
