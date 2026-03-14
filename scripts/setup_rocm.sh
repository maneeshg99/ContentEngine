#!/usr/bin/env bash
# setup_rocm.sh — Automated ROCm setup for AMD RX 6700 XT / 6750 XT on WSL2
# Usage: bash scripts/setup_rocm.sh [--dry-run]

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "[DRY RUN] No changes will be made."
fi

run_cmd() {
    if $DRY_RUN; then
        echo "  [would run] $*"
    else
        "$@"
    fi
}

echo "=== ContentEngine ROCm Setup for RX 6700 XT / 6750 XT ==="
echo ""

# Check WSL2
if ! grep -qi "microsoft" /proc/version 2>/dev/null; then
    echo "WARNING: This does not appear to be WSL2."
    echo "This script is designed for WSL2 on Windows with an AMD GPU."
    read -rp "Continue anyway? (y/N) " confirm
    [[ "$confirm" =~ ^[Yy]$ ]] || exit 1
fi

# Check Ubuntu
if command -v lsb_release &>/dev/null; then
    DISTRO=$(lsb_release -si)
    VERSION=$(lsb_release -sr)
    echo "Detected: $DISTRO $VERSION"
    if [[ "$DISTRO" != "Ubuntu" ]]; then
        echo "WARNING: This script is tested on Ubuntu 22.04. Your distro ($DISTRO) may work but is untested."
    fi
else
    echo "WARNING: Cannot detect distro (lsb_release not found)."
fi

echo ""
echo "Step 1: Adding ROCm apt repository..."
if [ -f /etc/apt/sources.list.d/rocm.list ]; then
    echo "  ROCm repository already configured, skipping."
else
    run_cmd sudo mkdir -p /etc/apt/keyrings
    if ! $DRY_RUN; then
        wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/rocm.gpg
        echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/6.2 jammy main" | sudo tee /etc/apt/sources.list.d/rocm.list
    else
        echo "  [would run] wget + gpg + tee to add ROCm 6.2 repo"
    fi
fi

echo ""
echo "Step 2: Installing minimal ROCm packages..."
run_cmd sudo apt update -qq
run_cmd sudo apt install -y rocm-hip-runtime rocm-smi-lib

echo ""
echo "Step 3: Adding user to render and video groups..."
run_cmd sudo usermod -aG render,video "$USER"

echo ""
echo "Step 4: Setting environment variables..."
BASHRC="$HOME/.bashrc"
ENV_VARS=(
    "export HSA_OVERRIDE_GFX_VERSION=10.3.0"
    "export HSA_ENABLE_SDMA=0"
)

for var in "${ENV_VARS[@]}"; do
    if grep -qF "$var" "$BASHRC" 2>/dev/null; then
        echo "  Already in .bashrc: $var"
    else
        if ! $DRY_RUN; then
            echo "$var" >> "$BASHRC"
            echo "  Added to .bashrc: $var"
        else
            echo "  [would add] $var"
        fi
    fi
done

# Source the vars for the current session
export HSA_OVERRIDE_GFX_VERSION=10.3.0
export HSA_ENABLE_SDMA=0

echo ""
echo "Step 5: Installing PyTorch with ROCm 6.2..."
run_cmd pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2

echo ""
echo "Step 6: Verifying GPU detection..."
if ! $DRY_RUN; then
    python -c "
import torch
if torch.cuda.is_available():
    print('SUCCESS: GPU detected!')
    print(f'  Device: {torch.cuda.get_device_name(0)}')
    print(f'  PyTorch version: {torch.__version__}')
    print()
    print('Set whisper.device to \"cuda\" in config.yaml to use GPU acceleration.')
else:
    print('FAILED: GPU not detected.')
    print('Check that:')
    print('  1. HSA_OVERRIDE_GFX_VERSION is set to 10.3.0')
    print('  2. You are running inside WSL2')
    print('  3. AMD Adrenalin driver is installed on Windows')
    print('  See docs/gpu-setup.md for troubleshooting.')
"
else
    echo "  [would run] python GPU verification check"
fi

echo ""
echo "=== Setup complete ==="
