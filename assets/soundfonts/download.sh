#!/bin/bash
# Download soundfonts for LMMS-AI
# Run this script to download the soundfonts used by this project

set -e
cd "$(dirname "$0")"

echo "Downloading soundfonts to $(pwd)..."

# GeneralUser GS - High quality GM soundfont (30MB)
if [ ! -f "GeneralUser GS v1.471.sf2" ]; then
    echo "Downloading GeneralUser GS v1.471..."
    curl -L -o "GeneralUser_GS.zip" "https://www.dropbox.com/s/4x27l49kxcwamp5/GeneralUser_GS_1.471.sf2?dl=1"
    unzip -o GeneralUser_GS.zip
    mv "GeneralUser GS 1.471/GeneralUser GS v1.471.sf2" .
    rm -rf "GeneralUser GS 1.471" GeneralUser_GS.zip
    echo "  Done: GeneralUser GS v1.471.sf2"
else
    echo "  Skipping GeneralUser GS (already exists)"
fi

# TR-808 Drums (398KB)
if [ ! -f "HS TR-808 Drums.sf2" ]; then
    echo "Downloading TR-808 Drums..."
    curl -L -o "tr808.zip" "http://www.ibiblio.org/thammer/HammerSound/localfiles/soundfonts/hs_tr808.zip"
    unzip -o tr808.zip
    rm -f tr808.zip hs_tr808.txt
    echo "  Done: HS TR-808 Drums.sf2"
else
    echo "  Skipping TR-808 (already exists)"
fi

# Check for system soundfonts and copy if available
if [ ! -f "FluidR3_GM.sf2" ]; then
    if [ -f "/usr/share/sounds/sf2/FluidR3_GM.sf2" ]; then
        echo "Copying FluidR3_GM from system..."
        cp /usr/share/sounds/sf2/FluidR3_GM.sf2 .
        echo "  Done: FluidR3_GM.sf2"
    else
        echo "  FluidR3_GM not found on system. Install fluid-soundfont-gm package or download manually."
    fi
else
    echo "  Skipping FluidR3_GM (already exists)"
fi

if [ ! -f "TimGM6mb.sf2" ]; then
    if [ -f "/usr/share/sounds/sf2/TimGM6mb.sf2" ]; then
        echo "Copying TimGM6mb from system..."
        cp /usr/share/sounds/sf2/TimGM6mb.sf2 .
        echo "  Done: TimGM6mb.sf2"
    else
        echo "  TimGM6mb not found on system. Install timgm6mb-soundfont package or download manually."
    fi
else
    echo "  Skipping TimGM6mb (already exists)"
fi

echo ""
echo "Soundfonts downloaded:"
ls -lh *.sf2 2>/dev/null || echo "  (none found)"
