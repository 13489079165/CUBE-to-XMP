# LUT to XMP Converter 🎨

[English](#english) | [中文说明](#chinese)

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)

---

<a name="english"></a>
## 🇬🇧 English Documentation

### 🌟 Overview
A lightweight, modern GUI application designed to bridge the gap between video color grading and photography post-processing. This tool provides **bidirectional conversion** between standard 3D LUTs (`.cube`) and Adobe Camera Raw profiles (`.xmp`). 

It is specifically tailored for photographers, colorists, and retouchers who wish to use cinematic `.cube` LUTs natively within **Adobe Lightroom Classic** and **Adobe Camera Raw (ACR)**.

### ⚙️ Technical Implementation

#### 1. `.cube` to `.xmp` Conversion Pipeline
Adobe XMP profiles do not store raw floating-point LUT data. Instead, they use a specific encoded block. The conversion process is as follows:
1. **Parsing**: Extracts the `LUT_3D_SIZE` and raw floating-point RGB samples (typically 0.0 to 1.0) from the `.cube` file.
2. **Resampling (Tetrahedral Interpolation)**: Adobe XMP natively supports a maximum LUT size of `32x32x32`. If a `.cube` file exceeds this dimension (e.g., `64x64x64`), the application uses a custom 3D tetrahedral interpolation algorithm to accurately downsample the LUT to `32` while preserving color fidelity.
3. **Data Formatting**: The floating-point values are mapped to `0-65535` (`uint16`) integers, offset by a pre-calculated NOP (No-Operation) linear matrix. The byte order is restructured (Blue changes fastest, then Green, then Red).
4. **Compression & Encoding**: The raw byte array is compressed using `zlib` (Deflate) and then encoded into an ASCII string using Adobe's proprietary **Base85** variant character set.
5. **XML Injection**: The resulting string, along with dynamically generated MD5 hashes and UUIDs, is injected into a standard Adobe `<x:xmpmeta>` XML template.

#### 2. `.xmp` to `.cube` Extraction Pipeline
1. **XML Parsing**: Uses Regex to extract the `<crs:Table_...>` block and the profile Title from the `.xmp` file.
2. **Base85 Decoding**: Reverses the custom Base85 encoding back into compressed bytes.
3. **Decompression**: Uses `zlib.decompress` to restore the binary payload.
4. **Byte Extraction**: Reads the 16-byte header to determine the LUT dimensions, then unpacks the `uint16` data blocks, reverses the NOP matrix subtraction, and normalizes the values back to `0.0 - 1.0` floats.
5. **Reordering & Exporting**: Restores the CUBE standard ordering (Red changes fastest) and writes the data to a standard `.cube` format.

#### 3. Built-in Film Simulations (Algorithmic Generation)
The tool includes a script (`generate_fuji_luts.py`) that programmatically generates 3D LUTs by manipulating the HSV color space. It mathematically simulates the characteristics of classic film stocks (e.g., *Provia, Velvia, Classic Chrome, Classic Negative NC*) using custom S-curves for contrast and specific Hue/Saturation shifts.

### 🚀 Installation & Usage

#### Option 1: Standalone Executable (Windows Recommended)
No Python environment is required! Just go to the **[发布](#)** page, download the latest `.zip` file, extract it, and double-click `cube_to_xmp.exe` to run.

#### Option 2: Run from Source (Win/Mac)
If you have a Python environment, you can run it directly:
```bash
git clone https://github.com/yourusername/lut-to-xmp-converter.git
cd lut-to-xmp-converter
pip install -r requirements.txt
python cube_to_xmp.py
```

#### 📸 How to Import XMP into Lightroom Classic
1. Use this tool to convert your `.cube` file to `.xmp`.
2. Open Lightroom Classic and go to the **Develop** module.
3. In the Basic panel on the right, click the **Profile Browser** icon (four small rectangles).
4. Click the `+` icon at the top left of the browser and select **Import Profiles**.
5. Select your generated `.xmp` file. You can now apply this cinematic LUT with one click!

### 🛠️ Developer Packaging Guide
If you want to modify the code and repackage it as an `.exe` file yourself, run:
```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --add-data "built_in_luts;built_in_luts/" cube_to_xmp.py
```
*(Note: If packaging on macOS, change the semicolon in the `--add-data` argument to a colon: `--add-data "built_in_luts:built_in_luts/"`)*

---

<a name="chinese"></a>
## 🇨🇳 中文技术文档

### 🌟 项目简介
这是一个轻量级且现代化的 GUI 桌面应用程序，旨在打通视频调色与摄影后期之间的壁垒。本工具支持标准 3D LUT (`.cube`) 与 Adobe Camera Raw 配置文件 (`.xmp`) 之间的**双向无损转换**。

对于希望在 **Adobe Lightroom Classic** 和 **Adobe Camera Raw (ACR)** 中直接使用电影级 `.cube` 调色预设的摄影师、调色师和修图师来说，这是一个完美的解决方案。

### ⚙️ 核心技术实现

#### 1. `.cube` 转 `.xmp` 编码流程
Adobe XMP 配置文件并不会直接存储浮点数 LUT 数据，而是使用了一种特殊的压缩编码块。转换流程如下：
1. **数据解析**：从 `.cube` 文件中提取 `LUT_3D_SIZE` 维度信息以及原始的 RGB 浮点采样数据（通常为 0.0 到 1.0）。
2. **重采样（四面体插值）**：Adobe XMP 原生最高仅支持 `32x32x32` 大小的 LUT。如果导入的 `.cube` 文件超过此限制（如 64 精度），程序会使用自定义的 **3D 四面体插值算法（Tetrahedral Interpolation）** 将其精确缩放至 32 精度，以确保色彩保真度并完美兼容 Adobe。
3. **数据格式化**：将浮点数映射为 `0-65535` (`uint16`) 的整数，并减去预先计算的 NOP（无操作）线性基础矩阵。重新排列字节顺序（Adobe 要求的顺序为：蓝通道变化最快，其次是绿、红）。
4. **压缩与编码**：将原始字节数组使用 `zlib` (Deflate) 算法进行压缩，随后使用 Adobe 专用的 **Base85 变体字符集** 将其编码为 ASCII 字符串。
5. **XML 注入**：将生成的字符串、动态计算的 MD5 哈希值以及 UUID 注入到标准的 Adobe `<x:xmpmeta>` XML 模板中。

#### 2. `.xmp` 转 `.cube` 解码流程
1. **XML 解析**：通过正则表达式精准定位并提取 `.xmp` 文件中的 `<crs:Table_...>` 数据块以及配置文件标题。
2. **Base85 解码**：逆向解析 Adobe 专用的 Base85 编码，还原为压缩的字节流。
3. **数据解压**：调用 `zlib.decompress` 还原二进制载荷。
4. **数据提取**：读取 16 字节的文件头获取 LUT 维度，随后解包 `uint16` 数据块，逆向补偿 NOP 矩阵的偏移量，并将数值重新归一化为 `0.0 - 1.0` 的浮点数。
5. **重排序与导出**：将数据恢复为 CUBE 标准的排序方式（红通道变化最快），并输出为标准的 `.cube` 文本文件。

#### 3. 内置胶片滤镜（算法生成）
项目中包含一个独立的生成脚本 (`generate_fuji_luts.py`)，它不依赖外部素材，而是纯粹通过数学算法在 **HSV 色彩空间** 中对像素进行重映射。通过自定义对比度 S 曲线以及特定的色相/饱和度偏移，精准模拟了多款经典胶片（如 *Provia, Velvia, Classic Chrome, Classic Negative NC*）的色彩特征，并生成对应的 LUT 文件。

### 🚀 安装与使用

#### 方式一：下载独立程序（Windows 推荐）
对于非开发者用户，无需安装 Python 环境。请直接前往 GitHub 的 **[发布](#)** 页面，下载最新的 `.zip` 压缩包。解压后双击运行 `cube_to_xmp.exe` 即可。

#### 方式二：通过源码运行（支持 Win/Mac）
如果你有 Python 环境，可以通过以下命令直接运行：
```bash
git clone https://github.com/yourusername/lut-to-xmp-converter.git
cd lut-to-xmp-converter
pip install -r requirements.txt
python cube_to_xmp.py
```

#### 📸 如何将生成的 XMP 导入 Lightroom Classic
1. 使用本软件将你的 `.cube` 文件转换为 `.xmp`。
2. 打开 Lightroom Classic 并进入 **“修改照片” (Develop)** 模块。
3. 在右侧的“基本”面板中，点击**配置文件浏览器**图标（四个小方块组成的图标）。
4. 点击浏览器左上角的 `+` 号，选择 **“导入配置文件” (Import Profiles)**。
5. 选择你刚刚生成的 `.xmp` 文件。现在你就可以在配置列表中一键应用这个电影级 LUT 了！

### 🛠️ 开发者打包指南
如果你想自己修改代码并重新打包为 `.exe` 文件，请执行：
```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --add-data "built_in_luts;built_in_luts/" cube_to_xmp.py
```
*(注意：如果你在 macOS 下打包，请将 `--add-data` 参数中的分号改为冒号：`--add-data "built_in_luts:built_in_luts/"`)*
