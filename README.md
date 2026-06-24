# CUBE-to-XMP v2.0 Release Notes

> 专业 LUT 转换工具 · Professional LUT Converter

---

## 中文介绍

### 项目简介

CUBE-to-XMP 是一款现代化的 LUT（Look-Up Table）格式转换工具，支持 `.cube`（3D LUT）与 `.xmp`（Adobe Camera Raw 配置文件）之间的**双向转换**。采用液态玻璃风格的暗色界面，提供拖拽加载、色彩预览、尺寸选择器等功能，面向调色师、摄影师和影像后期工作者。

### 核心功能

| 功能 | 说明 |
|------|------|
| 双向转换 | CUBE → XMP / XMP → CUBE，自动识别文件格式 |
| 尺寸选择 | 支持 16 / 17 / 25 / 32 / 33 / 64 / 65 七种输出尺寸 |
| 拖拽加载 | 将文件直接拖入窗口中央区域，悬停边框高亮反馈 |
| 色彩预览 | 实时展示 6 个标准色在 LUT 应用前后的对比 |
| 内置预设 | 6 种富士胶片风格（Provia / Velvia / Classic Chrome 等） |
| 中英双语 | 界面一键切换中文 / English |
| 主题切换 | 深色 / 浅色模式切换，自动适配系统 |

### v2.0 更新内容

**新功能**
- 导出尺寸选择器，支持 7 种业界标准 CUBE 尺寸
- 拖拽文件到中间区域加载，悬停时绿色边框高亮
- 中英双语界面切换按钮
- 深色/浅色主题切换

**Bug 修复**
- 修复 customtkinter 与 tkinterdnd2 多重继承导致拖拽完全失效
- 修复主题切换时转换历史区域颜色不更新
- 修复主题切换导致程序崩溃

### 使用方法

```
# 安装依赖
pip install -r requirements.txt

# 运行程序
python cube_to_xmp.py

# Windows 用户双击 启动程序.bat 即可
```

或下载免安装版本，解压后直接运行 `CUBE-to-XMP.exe`。

### 系统要求

- Python 3.10+（源码运行）
- Windows 64-bit
- 4GB RAM

### 技术栈

- **GUI**: CustomTkinter + tkinterdnd2
- **压缩**: zlib (Deflate) + Adobe Base85 编码
- **插值**: 3D LUT 三线性插值
- **打包**: PyInstaller

---

## English Introduction

### Overview

CUBE-to-XMP is a modern LUT (Look-Up Table) format conversion tool supporting **bidirectional conversion** between `.cube` (3D LUT) and `.xmp` (Adobe Camera Raw profile) formats. Featuring a premium liquid-glass dark interface with drag-and-drop, color preview, and a size selector — designed for colorists, photographers, and post-production professionals.

### Key Features

| Feature | Description |
|---------|-------------|
| Bidirectional conversion | CUBE → XMP / XMP → CUBE with automatic format detection |
| Size selector | Choose from 16 / 17 / 25 / 32 / 33 / 64 / 65 output sizes |
| Drag & drop | Drop files directly onto the center zone with hover highlight |
| Color preview | Real-time before/after comparison of 6 reference colors |
| Built-in presets | 6 Fujifilm film simulations (Provia, Velvia, Classic Chrome, etc.) |
| Bilingual UI | One-click switch between Chinese and English |
| Theme toggle | Dark / Light mode with system auto-detection |

### What's New in v2.0

**New Features**
- CUBE size selector with 7 industry-standard presets
- Drag & drop files onto the center zone with green border hover feedback
- Bilingual UI toggle button
- Dark / Light theme switcher

**Bug Fixes**
- Fixed drag-and-drop completely broken due to customtkinter + tkinterdnd2 MRO conflict
- Fixed history panel colors not updating on theme switch
- Fixed crash when switching themes

### Quick Start

```
# Install dependencies
pip install -r requirements.txt

# Run
python cube_to_xmp.py

# Windows users: double-click 启动程序.bat
```

Or download the portable version and run `CUBE-to-XMP.exe` directly.

### Requirements

- Python 3.10+ (source)
- Windows 64-bit
- 4GB RAM

### Tech Stack

- **GUI**: CustomTkinter + tkinterdnd2
- **Compression**: zlib (Deflate) + Adobe Base85 encoding
- **Interpolation**: 3D LUT trilinear interpolation
- **Packaging**: PyInstaller

---

## 项目信息 · Project Info

| 项 | 值 |
|----|-----|
| 版本 Version | v2.0 |
| 作者 Author | 魏浩文 (Claw) |
| 许可 License | MIT |
| 仓库 Repository | [github.com/13489079165/CUBE-to-XMP](https://github.com/13489079165/CUBE-to-XMP) |
| 语言 Language | Python 3.10+ |

## 项目结构 · Project Structure

```
CUBE-to-XMP/
├── cube_to_xmp.py          # 主程序 Main application
├── generate_fuji_luts.py   # LUT 生成脚本 LUT generation
├── requirements.txt        # Python 依赖 Dependencies
├── build.py               # 跨平台构建脚本 Build script
├── build_windows.bat      # Windows 一键构建 One-click build
├── 启动程序.bat            # 快速启动 Quick launch
├── icon.ico / icon.png    # 应用图标 App icons
├── built_in_luts/         # 内置胶片预设 Built-in presets
├── fonts/                 # 字体文件 Bundled fonts
├── .github/workflows/     # GitHub Actions 自动构建 CI/CD
└── README.md
```
