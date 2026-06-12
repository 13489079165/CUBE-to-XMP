@echo off
echo ========================================
echo CINELUT Studio v2.0 - Professional UI
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

echo [3/3] 启动 CINELUT Studio...
echo.
echo ========================================
echo 功能亮点:
echo - 专业级深色电影感界面
echo - 中央大尺寸拖拽导入区域
echo - 左侧: 文件/预设管理
echo - 中间: 色彩预览和转换
echo - 右侧: 输出设置和历史
echo - 底部: 状态栏
echo ========================================
echo.

python cube_to_xmp_ui.py

pause
