@echo off
echo ========================================
echo CUBE-to-XMP v2.0 - 快速启动
echo ========================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    echo 下载地址: https://python.org
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
pip show customtkinter >nul 2>&1
if errorlevel 1 (
    echo [2/3] 首次运行，正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 安装依赖失败
        pause
        exit /b 1
    )
) else (
    echo [2/3] 依赖已安装
)

echo [3/3] 启动程序...
echo.
echo ========================================
echo 提示:
echo - 可以拖放 .cube 或 .xmp 文件到窗口
echo - 支持中英文切换
echo - 关闭窗口退出程序
echo ========================================
echo.

python cube_to_xmp.py

pause
