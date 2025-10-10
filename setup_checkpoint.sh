#!/bin/bash
# Setup script for YourMT3 checkpoint download

set -e

echo "============================================================"
echo "YourMT3 Checkpoint Setup"
echo "============================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if amt directory exists
if [ -d "amt" ] && [ -f "amt/logs/2024/mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops/checkpoints/last.ckpt" ]; then
    echo -e "${GREEN}✅ YourMT3 checkpoint already exists${NC}"
    exit 0
fi

echo "This script will setup the YourMT3 checkpoint (~536MB)"
echo ""
echo -e "${YELLOW}Options:${NC}"
echo "1. Download from Hugging Face (cloud instance)"
echo "2. Copy from local path (if running locally)"
echo "3. Already transferred via SCP/rsync (verify only)"
echo "4. Skip (manual setup later)"
echo ""
echo -e "${YELLOW}💡 Recommended for cloud instances:${NC}"
echo "   Transfer from your machine using:"
echo "   scp -r amt/ user@instance:/path/to/music-to-midi-api/"
echo ""

read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo ""
        echo -e "${YELLOW}📦 Downloading YourMT3 checkpoint from Hugging Face...${NC}"
        echo ""

        # Check if git-lfs is installed
        if ! command -v git-lfs &> /dev/null; then
            echo -e "${RED}❌ git-lfs not found. Installing...${NC}"

            # Install git-lfs based on OS
            if [[ "$OSTYPE" == "darwin"* ]]; then
                brew install git-lfs
            elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
                curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | sudo bash
                sudo apt-get install git-lfs
            fi

            git lfs install
        fi

        # Create amt directory
        mkdir -p amt
        cd amt

        # Clone YourMT3 checkpoint repository
        echo "Cloning checkpoint repository..."
        git clone https://huggingface.co/mimbres/YourMT3 temp_clone

        # Copy necessary files
        echo "Copying checkpoint files..."
        cp -r temp_clone/amt/logs .
        cp temp_clone/model_helper.py .
        cp temp_clone/html_helper.py .

        # Create src directory structure
        mkdir -p src
        cd temp_clone/amt/src
        cp -r model config utils ../../src/
        cd ../../..

        # Clean up
        rm -rf temp_clone

        cd ..

        echo -e "${GREEN}✅ Checkpoint downloaded successfully${NC}"
        ;;

    2)
        echo ""
        read -p "Enter path to YourMT3 checkpoint directory: " local_path

        if [ ! -d "$local_path" ]; then
            echo -e "${RED}❌ Directory not found: $local_path${NC}"
            exit 1
        fi

        echo "Copying checkpoint..."
        mkdir -p amt

        # Copy checkpoint and helper files
        cp -r "$local_path/amt/logs" amt/
        cp "$local_path/model_helper.py" amt/
        cp "$local_path/html_helper.py" amt/

        # Copy source files
        mkdir -p amt/src
        cp -r "$local_path/amt/src/"* amt/src/

        echo -e "${GREEN}✅ Checkpoint copied successfully${NC}"
        ;;

    3)
        echo ""
        echo -e "${YELLOW}🔍 Verifying transferred checkpoint...${NC}"

        if [ ! -d "amt" ]; then
            echo -e "${RED}❌ amt/ directory not found${NC}"
            echo ""
            echo "Transfer the checkpoint first using:"
            echo "  scp -r amt/ user@instance:$(pwd)/"
            echo ""
            exit 1
        fi

        echo -e "${GREEN}✅ amt/ directory found${NC}"
        echo "Checkpoint will be verified below..."
        ;;

    4)
        echo ""
        echo -e "${YELLOW}⚠️  Skipping checkpoint setup${NC}"
        echo ""
        echo "To set up manually:"
        echo "1. Transfer from your local machine:"
        echo "   scp -r amt/ user@instance:$(pwd)/"
        echo ""
        echo "2. Or download from: https://huggingface.co/mimbres/YourMT3"
        echo "   Extract to: ./amt/"
        echo ""
        echo "3. Required structure:"
        echo "   amt/"
        echo "   ├── model_helper.py"
        echo "   ├── html_helper.py"
        echo "   ├── src/"
        echo "   └── logs/2024/.../checkpoints/last.ckpt"
        echo ""
        exit 0
        ;;

    *)
        echo -e "${RED}❌ Invalid option${NC}"
        exit 1
        ;;
esac

# Verify checkpoint
if [ -f "amt/logs/2024/mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops/checkpoints/last.ckpt" ]; then
    size=$(du -sh amt/logs/2024/mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops/checkpoints/last.ckpt | cut -f1)
    echo ""
    echo -e "${GREEN}✅ Setup complete!${NC}"
    echo "   Checkpoint size: $size"
    echo ""
    echo "Next steps:"
    echo "1. Install dependencies: pip install -r requirements.txt"
    echo "2. Start server: python -m app.main"
    echo "   Or with Docker: docker-compose up"
else
    echo -e "${RED}❌ Checkpoint verification failed${NC}"
    exit 1
fi
