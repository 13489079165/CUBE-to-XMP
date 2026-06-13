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


def clean_build():
    """Remove previous build artifacts."""
    print("Cleaning previous builds...")
    for dir_name in ['build', 'dist']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  Removed {dir_name}/")
    for spec_file in Path('.').glob('*.spec'):
        spec_file.unlink()
        print(f"  Removed {spec_file}")


def build_executable():
    """Build the executable using PyInstaller."""
    print("Building executable...")

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm',
        '--onedir',
        '--windowed',
        '--name', 'CUBE-to-XMP',
        '--add-data', f'built_in_luts{os.pathsep}built_in_luts/',
        '--add-data', f'icon.ico{os.pathsep}.',
        '--add-data', f'fonts{os.pathsep}fonts/',
        '--icon', 'icon.ico',
        '--hidden-import', 'tkinterdnd2',
        '--hidden-import', 'customtkinter',
        'cube_to_xmp.py'
    ]

    try:
        subprocess.check_call(cmd)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        return False


def verify_build():
    """Verify that the build was successful."""
    exe_path = Path('dist/CUBE-to-XMP/CUBE-to-XMP.exe')
    if exe_path.exists():
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"\nBuild successful!")
        print(f"Output: {exe_path} ({size_mb:.1f} MB)")
        return True
    else:
        print("Build failed - executable not found")
        return False


def main():
    print("=" * 60)
    print("Building CUBE-to-XMP v2.0")
    print("=" * 60)

    clean_build()

    if not build_executable():
        sys.exit(1)

    if not verify_build():
        sys.exit(1)

    print("\nDistributable: dist/CUBE-to-XMP/")


if __name__ == '__main__':
    main()
