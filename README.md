# ContentEngine

Automated pipeline for sourcing, clipping, and uploading short-form video content to TikTok, Instagram Reels, and YouTube Shorts.

## Quick Start

```bash
pip install -e .
content-engine init
```

## GPU Acceleration (AMD)

For AMD RX 6700 XT / 6750 XT users, see [docs/gpu-setup.md](docs/gpu-setup.md) for ROCm setup instructions, or run:

```bash
bash scripts/setup_rocm.sh
```