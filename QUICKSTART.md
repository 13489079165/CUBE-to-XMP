# CUBE-to-XMP - 快速开始

## 🎯 如何获取 Windows 可执行文件

### 方法 1: GitHub Actions 自动构建（推荐）

1. **推送到 GitHub**
   ```bash
   git push origin main
   git tag v2.0
   git push origin v2.0
   ```

2. **下载可执行文件**
   - 访问 GitHub 仓库页面
   - 点击 "Actions" 标签
   - 选择最新的构建
   - 下载 "Artifacts" 中的 `CUBE-to-XMP-v2.0-windows-x64.zip`
   - 解压后直接运行 `CUBE-to-XMP.exe`

✅ **无需安装任何依赖，解压即用！**

---

### 方法 2: 本地手动构建（Windows）

**前提条件**: 需要安装 Python 3.10+

**步骤:**

1. **下载项目**
   ```bash
   git clone https://github.com/13489079165/CUBE-to-XMP.git
   cd CUBE-to-XMP
   ```

2. **双击运行 `build_windows.bat`**
   - 脚本会自动安装所有依赖
   - 自动构建 Windows 可执行文件
   - 完成后会在 `dist/CUBE-to-XMP/` 生成 exe 文件

3. **获取可执行文件**
   ```
   dist/
   └── CUBE-to-XMP/
       ├── CUBE-to-XMP.exe      ← 直接运行这个
       └── _internal/           ← 包含所有依赖
   ```

4. **分发给用户**
   - 将整个 `CUBE-to-XMP` 文件夹压缩为 zip
   - 用户解压后双击 exe 即可使用

✅ **用户无需安装 Python 或任何依赖！**

---

## 📦 直接使用（开发者）

如果你有 Python 环境，可以直接运行：

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python cube_to_xmp.py
```

---

## 🚀 功能特性

- ✨ **拖拽支持** - 直接拖放文件到窗口
- 👁️ **颜色预览** - 实时显示 LUT 效果
- 📐 **双向转换** - CUBE ↔ XMP
- 🎨 **内置预设** - 6 种富士胶片风格
- 🌐 **多语言** - 中文/英文支持

---

## 📁 项目结构

```
CUBE-to-XMP/
├── cube_to_xmp.py          # 主程序源代码
├── generate_fuji_luts.py   # LUT 生成脚本
├── requirements.txt        # Python 依赖
├── build_windows.bat       # Windows 一键构建脚本
├── build.py                # 跨平台构建脚本
├── built_in_luts/          # 内置预设
└── .github/workflows/      # GitHub Actions 自动构建
```

---

## ❓ 常见问题

### Q: 为什么不能直接提供 exe 文件？
A: 因为需要在 Windows 环境中构建才能生成 Windows 可执行文件。通过 GitHub Actions 可以自动完成这个过程。

### Q: 构建后的 exe 文件有多大？
A: 约 15-20MB，包含所有依赖。

### Q: 用户需要安装 Python 吗？
A: 不需要！构建后的 exe 是独立的，可以直接运行。

### Q: 如何更新版本？
A: 修改代码后，推送新的 tag（如 `v2.1`），GitHub Actions 会自动构建新版本。

---

## 📝 开发者指南

### 本地开发
```bash
# 克隆项目
git clone https://github.com/13489079165/CUBE-to-XMP.git
cd CUBE-to-XMP

# 安装依赖
pip install -r requirements.txt

# 运行程序
python cube_to_xmp.py
```

### 构建可执行文件
```bash
# Windows
build_windows.bat

# macOS/Linux
python build.py
# 或
chmod +x build.sh && ./build.sh
```

### 发布新版本
```bash
# 1. 修改代码
# 2. 提交更改
git add .
git commit -m "Your changes"

# 3. 创建版本标签
git tag v2.1

# 4. 推送
git push origin main
git push origin v2.1

# 5. GitHub Actions 自动构建并发布
```

---

## 🔗 链接

- **源代码**: https://github.com/13489079165/CUBE-to-XMP
- **发布页面**: https://github.com/13489079165/CUBE-to-XMP/releases

---

**享受使用 CUBE-to-XMP！** 🎉
