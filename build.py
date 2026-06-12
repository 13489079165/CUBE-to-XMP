#!/usr/bin/env python3
"""
Build script for CUBE-to-XMP v2.0
Creates a distributable executable using PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 11):
        print(f"❌ Python 3.11+ required, found {sys.version}")
        return False
    return True

def install_pyinstaller():
    """Install PyInstaller if not present."""
    try:
        import PyInstaller
        print("✓ PyInstaller is already installed")
        return True
    except ImportError:
        print("📦 Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller', '--break-system-packages'])
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install PyInstaller")
            return False

def clean_build():
    """Remove previous build artifacts."""
    print("🧹 Cleaning previous builds...")
    dirs_to_remove = ['build', 'dist']
    files_to_remove = ['*.spec']

    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  ✓ Removed {dir_name}/")

    for pattern in files_to_remove:
        for file in Path('.').glob(pattern):
            file.unlink()
            print(f"  ✓ Removed {file}")

def build_executable():
    """Build the executable using PyInstaller."""
    print("🔨 Building executable...")

    # PyInstaller command
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
        '--name', 'CUBE-to-XMP',
        '--add-data', f'built_in_luts{os.pathsep}built_in_luts/',
        '--hidden-import', 'tkinterdnd2',
        'cube_to_xmp.py'
    ]

    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False

def verify_build():
    """Verify that the build was successful."""
    exe_path = Path('dist/CUBE-to-XMP')

    if exe_path.exists():
        print("\n✅ Build successful!")
        print(f"📁 Output directory: {exe_path}")
        print(f"🚀 Run the application: {exe_path / 'CUBE-to-XMP'}")
        print("\nTo create a distributable zip:")
        print("  cd dist && zip -r CUBE-to-XMP-v2.0.zip CUBE-to-XMP/")
        return True
    else:
        print("❌ Build failed - executable not found")
        return False

def main():
    """Main build function."""
    print("=" * 60)
    print("Building CUBE-to-XMP v2.0")
    print("=" * 60)
    print()

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Install PyInstaller
    if not install_pyinstaller():
        sys.exit(1)

    # Clean previous builds
    clean_build()

    # Build executable
    if not build_executable():
        sys.exit(1)

    # Verify build
    if not verify_build():
        sys.exit(1)

    print()
    print("=" * 60)
    print("Build completed successfully!")
    print("=" * 60)

if __name__ == '__main__':
    main()
