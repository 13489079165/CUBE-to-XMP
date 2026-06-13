# CUBE-to-XMP v2.0

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个现代化的 LUT 转换工具，支持 `.cube` (3D LUT) 和 `.xmp` (Adobe Camera Raw) 双向转换。带有拖拽支持、颜色预览、中英双语界面。

## 功能特性

- **拖拽支持** - 直接拖放 .cube / .xmp 文件到窗口
- **颜色预览** - 实时显示 LUT 对 6 个标准色的影响
- **双向转换** - CUBE ↔ XMP 互转
- **内置预设** - 6 种富士胶片风格（Provia / Velvia / Classic Chrome / Astia / Monochrome / Classic Negative）
- **中英双语** - 界面支持中文和 English 切换
- **深色/浅色主题** - 跟随系统或手动切换
- **智能插值** - 大尺寸 LUT（>32³）自动缩放到 32³

## 快速开始

### 运行程序

```bash
# 安装依赖
pip install -r requirements.txt

# 启动
python cube_to_xmp.py
```

或 Windows 用户直接双击 `启动程序.bat`。

### 打包为独立 exe

```bash
# Windows: 双击 build_windows.bat
# 跨平台:
pip install pyinstaller
python build.py
```

输出在 `dist/CUBE-to-XMP/` 目录，用户无需安装 Python。

## 使用方法

| 方式 | 操作 |
|------|------|
| 拖放 | 将 .cube 或 .xmp 文件直接拖入窗口 |
| 按钮 | 点击"选择文件并转换"，选择文件 |
| 预设 | 切换到"内置胶片预设"标签，选择预设后导出 |

## 支持的格式

- `.cube` → `.xmp`（3D LUT 转为 Adobe Camera Raw 配置）
- `.xmp` → `.cube`（Adobe 配置提取为 3D LUT）

## 项目结构

```
CUBE-to-XMP/
├── cube_to_xmp.py          # 主程序
├── generate_fuji_luts.py   # LUT 生成脚本
├── requirements.txt        # Python 依赖
├── build.py               # 跨平台构建脚本
├── build_windows.bat      # Windows 一键构建
├── CUBE-to-XMP.spec       # PyInstaller 配置
├── 启动程序.bat            # 快速启动
├── icon.ico / icon.png    # 应用图标
├── built_in_luts/         # 内置胶片预设
├── .github/workflows/     # GitHub Actions 自动构建
└── README.md
```

## 系统要求

- Python 3.10+（源码运行）
- Windows / macOS / Linux
- 4GB RAM

## 技术栈

- **GUI**: CustomTkinter + tkinterdnd2
- **压缩**: zlib (Deflate) + Adobe Base85 编码
- **LUT**: 3D LUT 三线性插值

## 构建发布

GitHub Actions 自动构建三平台版本，推送 `v*` tag 即触发。

```bash
git tag v2.0
git push origin v2.0
```

## 许可证

MIT License

## 作者

魏浩文 (Claw)
