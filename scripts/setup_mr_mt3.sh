#!/bin/bash
# Setup script for MR-MT3 model and dependencies

set -e  # Exit on error

echo "🎵 Setting up MR-MT3 for music-to-midi-api"
echo ""

# Create models directory
MR_MT3_DIR="./models/mr-mt3"
mkdir -p "$MR_MT3_DIR"

echo "📂 Created models directory: $MR_MT3_DIR"
echo ""

# Clone MR-MT3 repository
echo "📥 Cloning MR-MT3 repository..."
if [ ! -d "$MR_MT3_DIR/MR-MT3" ]; then
    git clone https://github.com/gudgud96/MR-MT3.git "$MR_MT3_DIR/MR-MT3"
    echo "✅ Repository cloned"
else
    echo "⚠️  Repository already exists, skipping clone"
fi
echo ""

# Download model checkpoint
echo "📥 Downloading MR-MT3 model checkpoint (~400MB)..."
cd "$MR_MT3_DIR"

if [ ! -f "mt3.pth" ]; then
    wget https://huggingface.co/gudgud1014/MR-MT3/resolve/main/slakh_f1_0.65.pth \
        -O mt3.pth
    echo "✅ Model checkpoint downloaded"
else
    echo "⚠️  Model checkpoint already exists"
fi

# Download config
echo "📥 Downloading model configuration..."
if [ ! -f "config.json" ]; then
    wget https://raw.githubusercontent.com/kunato/mt3-pytorch/master/config/mt3_config.json \
        -O config.json
    echo "✅ Configuration downloaded"
else
    echo "⚠️  Configuration already exists"
fi

cd ../..

echo ""
echo "🎉 MR-MT3 setup complete!"
echo ""
echo "📊 Downloaded files:"
ls -lh "$MR_MT3_DIR"/*.{pth,json} 2>/dev/null || echo "  (checking files...)"
echo ""
echo "Next steps:"
echo "  1. Install Python dependencies: pip install -r requirements.txt"
echo "  2. Start the API: python -m app.main"
echo ""
