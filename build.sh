#!/bin/bash
# Build script for CUBE-to-XMP v2.0

echo "🚀 Building CUBE-to-XMP v2.0..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed"
    exit 1
fi

# Check if PyInstaller is installed
if ! python3 -m pip show pyinstaller &> /dev/null; then
    echo "📦 Installing PyInstaller..."
    pip3 install pyinstaller --break-system-packages
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist *.spec

# Build the executable
echo "🔨 Building executable..."
python3 -m PyInstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --name "CUBE-to-XMP" \
    --add-data "built_in_luts:built_in_luts/" \
    --hidden-import tkinterdnd2 \
    cube_to_xmp.py

# Check if build was successful
if [ -f "dist/CUBE-to-XMP/CUBE-to-XMP" ]; then
    echo ""
    echo "✅ Build successful!"
    echo "📁 Output directory: dist/CUBE-to-XMP/"
    echo "🚀 Run the application: dist/CUBE-to-XMP/CUBE-to-XMP"
    echo ""
    echo "To create a distributable zip:"
    echo "  cd dist && zip -r CUBE-to-XMP-v2.0.zip CUBE-to-XMP/"
else
    echo "❌ Build failed"
    exit 1
fi
