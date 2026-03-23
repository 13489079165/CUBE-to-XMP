# LUT to XMP Converter 🎨

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)

A lightweight and modern GUI application designed to bridge the gap between video color grading and photography post-processing. This tool allows you to bidirectionally convert standard 3D LUTs (`.cube`) and Adobe Camera Raw profiles (`.xmp`). 

Perfect for photographers and colorists who want to use their favorite cinematic LUTs directly inside Lightroom Classic or Adobe Camera Raw (ACR).

---

## ✨ Features

- **🔄 Bidirectional Conversion**: 
  - `.cube` ➡️ `.xmp`: Convert 3D LUTs to Adobe Camera Raw profiles. (Automatically resamples LUTs > 32 to ensure Adobe compatibility).
  - `.xmp` ➡️ `.cube`: Extract and decode Base85 + Zlib compressed 3D LUT data from Adobe XMP profiles back into standard `.cube` files.
- **🎞️ Built-in Fuji Film Simulations**: Comes pre-loaded with generated Fujifilm-style presets that you can instantly export to `.xmp`:
  - `Fuji Provia Standard`
  - `Fuji Velvia Vivid`
  - `Fuji Classic Chrome`
  - `Fuji Astia Soft`
  - `Fuji Classic Negative NC`
  - `Fuji Monochrome`
- **🖥️ Modern UI**: Built with `customtkinter`, featuring a clean, minimalist design with Dark/Light theme support.
- **🌐 Bilingual**: Supports both English and Simplified Chinese interfaces.

## 🚀 Download & Installation

### Option 1: Download the Executable (Windows)
You don't need to install Python! Just download the standalone `.exe` file from the **[Releases](#)** page and double-click to run.

### Option 2: Run from Source
If you prefer to run it via Python or are on a Mac/Linux machine:

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/lut-to-xmp-converter.git
   cd lut-to-xmp-converter
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python cube_to_xmp.py
   ```

## 🛠️ How to Use

1. **Convert Custom Files**:
   - Go to the **"双向转换 / Custom .cube"** tab.
   - Click the convert button and select either a `.cube` or `.xmp` file.
   - The program will automatically detect the format and ask you where to save the converted file.
2. **Export Built-in Presets**:
   - Go to the **"内置胶片预设 / Film Presets"** tab.
   - Select your desired film simulation from the dropdown menu.
   - Click export and save the `.xmp` file.
3. **Import into Lightroom**:
   - Open Lightroom Classic.
   - Go to the Develop module (Develop).
   - In the Basic panel, click the Profile Browser icon (four little squares).
   - Click the `+` icon at the top of the Profile Browser and select "Import Profiles".
   - Select the generated `.xmp` file.

## 📦 Building the Executable Yourself

If you want to package the app yourself using PyInstaller:

```bash
pip install pyinstaller
pyinstaller --noconfirm --onedir --windowed --add-data "built_in_luts;built_in_luts/" cube_to_xmp.py
```
*Note: For macOS, use `:` instead of `;` in the `--add-data` argument: `--add-data "built_in_luts:built_in_luts/"`*

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](#).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
