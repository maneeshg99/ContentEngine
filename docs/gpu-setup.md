# GPU Setup Guide — AMD RX 6700 XT / 6750 XT

The ContentEngine uses OpenAI Whisper for transcription, which benefits significantly from GPU acceleration. This guide covers setup for AMD RX 6700 XT and 6750 XT GPUs (RDNA2 / gfx1031).

> **Important:** The RX 6700 XT (gfx1031) is not officially supported by AMD ROCm. It works reliably by spoofing as the supported RX 6800 XT (gfx1030) via an environment variable. This workaround is well-tested by the community.

---

## Option A: WSL2 + ROCm (Recommended for Windows users)

### Prerequisites
- Windows 10 (21H2+) or Windows 11
- AMD Adrenalin driver installed on Windows (latest version)
- WSL2 enabled with Ubuntu 22.04

### Step 1: Install WSL2 with Ubuntu

```powershell
# In PowerShell (admin)
wsl --install -d Ubuntu-22.04
```

Reboot if prompted, then launch Ubuntu from the Start menu and set up your username/password.

### Step 2: Install minimal ROCm packages

Do **not** use `amdgpu-install` — it can crash your display. Install only the minimal runtime packages:

```bash
# Add the ROCm apt repository
sudo mkdir -p /etc/apt/keyrings
wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/rocm.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/6.2 jammy main" | sudo tee /etc/apt/sources.list.d/rocm.list
sudo apt update

# Install minimal ROCm runtime
sudo apt install -y rocm-hip-runtime rocm-smi-lib

# Add your user to the required groups
sudo usermod -aG render,video $USER
```

### Step 3: Set environment variables

Add these to your `~/.bashrc`:

```bash
echo 'export HSA_OVERRIDE_GFX_VERSION=10.3.0' >> ~/.bashrc
echo 'export HSA_ENABLE_SDMA=0' >> ~/.bashrc
source ~/.bashrc
```

- `HSA_OVERRIDE_GFX_VERSION=10.3.0` — spoofs gfx1031 as gfx1030 (required)
- `HSA_ENABLE_SDMA=0` — fixes stability issues on WSL2

### Step 4: Install PyTorch with ROCm support

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2
```

### Step 5: Verify GPU detection

```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

Expected output:
```
CUDA available: True
Device: AMD Radeon RX 6700 XT
```

### Step 6: Configure ContentEngine

In `config.yaml`, set:

```yaml
whisper:
  device: "cuda"   # ROCm uses the CUDA interface in PyTorch
```

Then install and run:

```bash
cd ContentEngine
pip install -e .
content-engine init
```

---

## Option B: Docker with ROCm (Most Reliable)

Docker isolates the ROCm stack, avoiding system-level install issues.

### Prerequisites
- WSL2 with Ubuntu (or native Linux)
- Docker installed inside WSL2

### Run with Docker

```bash
docker run -it --rm \
  --device=/dev/kfd \
  --device=/dev/dri \
  -e HSA_OVERRIDE_GFX_VERSION=10.3.0 \
  -e HSA_ENABLE_SDMA=0 \
  -v $(pwd):/workspace \
  -w /workspace \
  rocm/pytorch:latest \
  bash
```

Inside the container:

```bash
pip install -e .
content-engine init
content-engine transcribe <source-id>
```

---

## Option C: CPU Only (No GPU Setup Needed)

If GPU setup is too problematic, Whisper runs fine on CPU — just slower.

In `config.yaml`:

```yaml
whisper:
  model: "base"    # Use "tiny" for fastest CPU performance
  device: "cpu"
```

No additional setup required. A "base" model transcription of a 1-hour podcast takes roughly 15-30 minutes on CPU vs 2-5 minutes on GPU.

---

## Troubleshooting

### `torch.cuda.is_available()` returns `False`

1. Verify env vars are set: `echo $HSA_OVERRIDE_GFX_VERSION` should print `10.3.0`
2. Check you're running inside WSL2, not native Windows
3. Verify ROCm can see your GPU: `rocm-smi` should list your card
4. Make sure you installed the ROCm build of PyTorch (not the default CPU build)

### `RuntimeError: HIP error` or `hipErrorNoBinaryForGpu`

The `HSA_OVERRIDE_GFX_VERSION` is not set or not taking effect. Re-source your bashrc:

```bash
source ~/.bashrc
```

### Whisper is slow even with GPU

- Use a smaller model (`tiny` or `base`) for faster transcription
- Check GPU utilization with `rocm-smi` while transcribing
- Ensure `device: "cuda"` is set in `config.yaml` (not `"cpu"`)

### `config.yaml` says `device: "rocm"` — is that right?

No. ROCm uses PyTorch's CUDA interface. Always set `device: "cuda"` for AMD GPUs. The value `"rocm"` is not valid and will raise an error.
