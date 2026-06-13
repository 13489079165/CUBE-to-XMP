@echo off
title CUBE-to-XMP v2.0 - Build

echo ========================================
echo Building CUBE-to-XMP v2.0
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    echo Download: https://python.org
    pause
    exit /b 1
)

echo [1/3] Installing build dependencies...
pip install pyinstaller customtkinter darkdetect tkinterdnd2 >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [2/3] Building executable...
pyinstaller --noconfirm --onedir --windowed --name "CUBE-to-XMP" --add-data "built_in_luts;built_in_luts/" --add-data "icon.ico;." --add-data "fonts;fonts/" --icon "icon.ico" --hidden-import tkinterdnd2 --hidden-import customtkinter cube_to_xmp.py
if errorlevel 1 (
    echo [ERROR] Build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Build complete!
echo.
echo Output: dist\CUBE-to-XMP\CUBE-to-XMP.exe
echo.
echo To distribute: zip the entire dist\CUBE-to-XMP\ folder

pause
