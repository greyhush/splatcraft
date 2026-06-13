#!/usr/bin/env bash
# SplatCraft dependency installer
# Run: bash scripts/install_deps.sh

set -e

echo "=== SplatCraft Dependency Installer ==="

# Check CUDA
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ nvidia-smi not found. Install NVIDIA drivers first."
    exit 1
fi
echo "✅ NVIDIA GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"

# Install Python package
echo ""
echo "=== Installing SplatCraft ==="
pip install -e ".[gui]"

# Install PyTorch (if not already installed)
echo ""
echo "=== Checking PyTorch ==="
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA {torch.cuda.is_available()}')" 2>/dev/null || {
    echo "Installing PyTorch with CUDA..."
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
}

# Install gsplat (optional, for faster training)
echo ""
echo "=== Installing gsplat ==="
pip install gsplat 2>/dev/null || echo "⚠ gsplat install failed (optional, nerfstudio will use its own rasterizer)"

# Install nerfstudio
echo ""
echo "=== Installing nerfstudio ==="
pip install nerfstudio 2>/dev/null || {
    echo "⚠ pip install failed, trying from source..."
    pip install git+https://github.com/nerfstudio-project/nerfstudio.git
}

# Install SuGaR (mesh extraction)
echo ""
echo "=== Installing SuGaR ==="
if [ ! -d "deps/SuGaR" ]; then
    mkdir -p deps
    git clone https://github.com/Anttwo/SuGaR deps/SuGaR
fi
pip install -e deps/SuGaR 2>/dev/null || echo "⚠ SuGaR install failed (manual mesh extraction needed)"

# Install CoACD (physics colliders)
echo ""
echo "=== Installing CoACD ==="
pip install coacd 2>/dev/null || {
    echo "⚠ pip install failed, trying from source..."
    if [ ! -d "deps/CoACD" ]; then
        git clone https://github.com/SarahWeiii/CoACD deps/CoACD
    fi
    cd deps/CoACD && pip install . && cd ../..
}

# Verify
echo ""
echo "=== Verification ==="
python -c "
from splatcraft.utils.gpu import detect_gpu
gpu = detect_gpu()
print(f'GPU: {gpu.name} ({gpu.vram_total_mb}MB)' if gpu else 'GPU: Not found')
"

splatcraft check

echo ""
echo "=== Done! ==="
echo "Run: splatcraft build <photo_dir>"
echo "  or: splatcraft gui"
