@echo off
echo ========================================
echo CUBE-to-XMP v2.0 - Windows Builder
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo [1/4] Installing dependencies...
pip install pyinstaller customtkinter darkdetect tkinterdnd2
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist CUBE-to-XMP.spec del CUBE-to-XMP.spec

echo.
echo [3/4] Building executable...
python -m PyInstaller --noconfirm --onedir --windowed --name "CUBE-to-XMP" --add-data "built_in_luts;built_in_luts/" --hidden-import tkinterdnd2 --hidden-import customtkinter cube_to_xmp.py
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Creating distribution package...
cd dist
if exist CUBE-to-XMP-v2.0.zip del CUBE-to-XMP-v2.0.zip
powershell -Command "Compress-Archive -Path 'CUBE-to-XMP' -DestinationPath 'CUBE-to-XMP-v2.0.zip'"
cd ..

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\CUBE-to-XMP\CUBE-to-XMP.exe
echo.
echo To create a distributable package:
echo   - Share the entire dist\CUBE-to-XMP\ folder
echo   - Or share dist\CUBE-to-XMP-v2.0.zip
echo.
echo Users can run CUBE-to-XMP.exe directly
echo without installing Python or any dependencies!
echo.
pause
