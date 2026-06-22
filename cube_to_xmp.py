"""
CUBE-to-XMP  v2.0
Professional LUT conversion tool for colorists and photographers.
CUBE (3D LUT) <-> XMP (Adobe Camera Raw) bidirectional converter.

Premium dark interface inspired by DaVinci Resolve / Adobe Lightroom.
"""

import os
import re
import struct
import zlib
import hashlib
import time
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
import ctypes

# ============================================================
# BASE PATH (for PyInstaller)
# ============================================================
if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# COLOR PALETTES — Dark & Light
# ============================================================
C_DARK = {
    "bg":           "#08080A",
    "surface_0":    "#0E0E12",
    "surface_1":    "#141419",
    "surface_2":    "#1A1A21",
    "surface_3":    "#22222B",
    "border":       "#2A2A35",
    "border_act":   "#404055",
    "accent":       "#00D4AA",
    "accent_dim":   "#00A885",
    "accent_2":     "#4DA6FF",
    "text":         "#E4E4EA",
    "text_sec":     "#90909A",
    "text_muted":   "#585862",
    "success":      "#34C759",
    "warning":      "#FF9F0A",
    "error":        "#FF453A",
    "drop_bg":      "#101016",
    "drop_border":  "#353545",
    "drop_border_h":"#00D4AA55",
}

C_LIGHT = {
    "bg":           "#F2F2F7",
    "surface_0":    "#FFFFFF",
    "surface_1":    "#F9F9FC",
    "surface_2":    "#E8E8EE",
    "surface_3":    "#DDDDE5",
    "border":       "#D1D1D8",
    "border_act":   "#A0A0AE",
    "accent":       "#00A885",
    "accent_dim":   "#008060",
    "accent_2":     "#3B82F6",
    "text":         "#1D1D1F",
    "text_sec":     "#6E6E77",
    "text_muted":   "#A0A0AB",
    "success":      "#30B250",
    "warning":      "#E8900A",
    "error":        "#E83030",
    "drop_bg":      "#EBEBF2",
    "drop_border":  "#CCCCD5",
    "drop_border_h":"#00A88555",
}

C = dict(C_DARK)  # Start with dark theme

# ============================================================
# FONTS — Load bundled font files via Windows API
# ============================================================
FONTS_DIR = os.path.join(BASE_PATH, "fonts")

# Register bundled .otf/.ttf files with Windows (current session only, no admin needed)
if sys.platform == "win32" and os.path.isdir(FONTS_DIR):
    for fname in os.listdir(FONTS_DIR):
        fpath = os.path.join(FONTS_DIR, fname)
        if fname.lower().endswith((".otf", ".ttf")):
            try:
                ctypes.windll.gdi32.AddFontResourceW(fpath)
            except Exception:
                pass

# Font families — if bundled fonts are registered, they'll be available.
# tkinter gracefully falls back to system fonts if a family is not found.
FONT_FAMILY = "Inter"
TITLE_FONT_FAMILY = "Montserrat"  # Used for "CUBE to XMP" title
MONO_FAMILY = "Consolas"

# Common CUBE LUT sizes — industry standard presets
CUBE_SIZE_PRESETS = [16, 17, 25, 32, 33, 64, 65]


def font(size=13, weight="normal", family=None):
    """Create a CTkFont — body text."""
    return ctk.CTkFont(family=family or FONT_FAMILY, size=size, weight=weight)


def title_font(size=22, weight="bold"):
    """Font for app title — uses TITLE_FONT_FAMILY."""
    return ctk.CTkFont(family=TITLE_FONT_FAMILY, size=size, weight=weight)


def mono_font(size=12):
    """Monospace font for code/paths."""
    return ctk.CTkFont(family=MONO_FAMILY, size=size)

# ============================================================
# GLOBAL THEME SETUP
# ============================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# ============================================================
# CONVERSION FUNCTIONS
# ============================================================
kEncodeTable = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?`'|()[]{}@%$#"


def parse_xmp(file_path):
    import xml.etree.ElementTree as ET
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    title = "Extracted_LUT"
    title_match = re.search(r'<crs:Name>\s*<rdf:Alt>\s*<rdf:li xml:lang="x-default">(.*?)</rdf:li>', content, re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
    table_match = re.search(r'crs:Table_[A-F0-9]+="([^"]+)"', content)
    if not table_match:
        raise ValueError("Valid RGBTable data not found in XMP.")
    encoded_str = table_match.group(1)
    kDecodeTable = {c: i for i, c in enumerate(kEncodeTable)}
    compressed_data = bytearray()
    val, phase = 0, 0
    for c in encoded_str:
        if c not in kDecodeTable:
            continue
        d = kDecodeTable[c]
        phase += 1
        if phase == 1: val = d
        elif phase == 2: val += d * 85
        elif phase == 3: val += d * (85 * 85)
        elif phase == 4: val += d * (85 * 85 * 85)
        elif phase == 5:
            val += d * (85 * 85 * 85 * 85)
            compressed_data.extend(struct.pack('<I', val))
            phase = 0
    if phase > 0:
        if phase == 2: compressed_data.extend(struct.pack('<B', val & 0xFF))
        elif phase == 3: compressed_data.extend(struct.pack('<H', val & 0xFFFF))
        elif phase == 4: compressed_data.extend(struct.pack('<I', val)[:3])
    if len(compressed_data) < 4:
        raise ValueError("Invalid compressed data size")
    uncompressed_size = struct.unpack('<I', compressed_data[:4])[0]
    z_data = compressed_data[4:]
    try:
        block_data = zlib.decompress(z_data)
    except zlib.error:
        block_data = zlib.decompress(z_data, bufsize=uncompressed_size)
    if len(block_data) < 16:
        raise ValueError("Invalid uncompressed data block")
    h_v1, h_v2, dims, size = struct.unpack('<4I', block_data[:16])
    if dims != 3:
        raise ValueError(f"Only 3D LUTs are supported (found {dims}D)")
    lut_3d = [[[(0, 0, 0) for _ in range(size)] for _ in range(size)] for _ in range(size)]
    nopValue = [(i * 0xFFFF + (size // 2)) // (size - 1) for i in range(size)]
    offset = 16
    for b in range(size):
        for g in range(size):
            for r in range(size):
                if offset + 6 > len(block_data):
                    break
                temp_r, temp_g, temp_b = struct.unpack('<HHH', block_data[offset:offset+6])
                offset += 6
                lut_3d[r][g][b] = (
                    (temp_r + nopValue[r]) / 65535.0,
                    (temp_g + nopValue[g]) / 65535.0,
                    (temp_b + nopValue[b]) / 65535.0,
                )
    samples = []
    for b in range(size):
        for g in range(size):
            for r in range(size):
                samples.append(lut_3d[r][g][b])
    return title, size, samples


def build_cube(title, size, samples):
    lines = [
        f'TITLE "{title}"',
        f'LUT_3D_SIZE {size}',
        'DOMAIN_MIN 0.0 0.0 0.0',
        'DOMAIN_MAX 1.0 1.0 1.0',
        '',
    ]
    for r, g, b in samples:
        lines.append(f"{r:.6f} {g:.6f} {b:.6f}")
    return '\n'.join(lines)


def encode_zlib_base85(data: bytes) -> str:
    padded_data = data + b'\x00\x00\x00'
    encoded_chars = []
    compressed_size = len(data)
    for i in range(0, len(data), 4):
        x = struct.unpack('<I', padded_data[i:i+4])[0]
        for j in range(5):
            encoded_chars.append(kEncodeTable[x % 85])
            x //= 85
            if j > 0:
                compressed_size -= 1
                if compressed_size == 0:
                    break
    return "".join(encoded_chars)


def parse_cube(file_path):
    size = None
    title = "My LUT"
    samples = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('TITLE'):
                match = re.match(r'TITLE\s+"([^"]+)"', line)
                if match:
                    title = match.group(1)
            elif line.startswith('LUT_3D_SIZE'):
                size = int(line.split()[1])
            elif line.startswith('DOMAIN_'):
                continue
            else:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        samples.append((float(parts[0]), float(parts[1]), float(parts[2])))
                    except ValueError:
                        pass
    return title, size, samples


def interpolate_3d(samples, size, new_size=32):
    new_samples = []
    ratio = (size - 1.0) / (new_size - 1.0)

    def get_sample(r, g, b):
        r = max(0, min(size - 1, r))
        g = max(0, min(size - 1, g))
        b = max(0, min(size - 1, b))
        return samples[r + g * size + b * size * size]

    for b_idx in range(new_size):
        for g_idx in range(new_size):
            for r_idx in range(new_size):
                r_pos = r_idx * ratio
                g_pos = g_idx * ratio
                b_pos = b_idx * ratio
                r0, g0, b0 = int(r_pos), int(g_pos), int(b_pos)
                r1, g1, b1 = min(r0 + 1, size - 1), min(g0 + 1, size - 1), min(b0 + 1, size - 1)
                fr, fg, fb = r_pos - r0, g_pos - g0, b_pos - b0

                if fg >= fb and fb >= fr:
                    c0, c1, c2, c3 = (get_sample(r0, g0, b0), get_sample(r0, g1, b0),
                                       get_sample(r0, g1, b1), get_sample(r1, g1, b1))
                    w0, w1, w2, w3 = 1 - fg, fg - fb, fb - fr, fr
                elif fb > fr and fr > fg:
                    c0, c1, c2, c3 = (get_sample(r0, g0, b0), get_sample(r0, g0, b1),
                                       get_sample(r1, g0, b1), get_sample(r1, g1, b1))
                    w0, w1, w2, w3 = 1 - fb, fb - fr, fr - fg, fg
                elif fb > fg and fg >= fr:
                    c0, c1, c2, c3 = (get_sample(r0, g0, b0), get_sample(r0, g0, b1),
                                       get_sample(r0, g1, b1), get_sample(r1, g1, b1))
                    w0, w1, w2, w3 = 1 - fb, fb - fg, fg - fr, fr
                elif fr >= fg and fg > fb:
                    c0, c1, c2, c3 = (get_sample(r0, g0, b0), get_sample(r1, g0, b0),
                                       get_sample(r1, g1, b0), get_sample(r1, g1, b1))
                    w0, w1, w2, w3 = 1 - fr, fr - fg, fg - fb, fb
                elif fg > fr and fr >= fb:
                    c0, c1, c2, c3 = (get_sample(r0, g0, b0), get_sample(r0, g1, b0),
                                       get_sample(r1, g1, b0), get_sample(r1, g1, b1))
                    w0, w1, w2, w3 = 1 - fg, fg - fr, fr - fb, fb
                else:
                    c0, c1, c2, c3 = (get_sample(r0, g0, b0), get_sample(r1, g0, b0),
                                       get_sample(r1, g0, b1), get_sample(r1, g1, b1))
                    w0, w1, w2, w3 = 1 - fr, fr - fb, fb - fg, fg

                new_samples.append((
                    c0[0] * w0 + c1[0] * w1 + c2[0] * w2 + c3[0] * w3,
                    c0[1] * w0 + c1[1] * w1 + c2[1] * w2 + c3[1] * w3,
                    c0[2] * w0 + c1[2] * w1 + c2[2] * w2 + c3[2] * w3,
                ))
    return new_samples


def build_xmp(title, size, samples):
    if size is None or not samples:
        raise ValueError("Invalid CUBE file")
    if size > 32:
        samples = interpolate_3d(samples, size, 32)
        size = 32
    nopValue = [(i * 0xFFFF + (size // 2)) // (size - 1) for i in range(size)]
    block_data = bytearray()
    block_data.extend(struct.pack('<4I', 1, 1, 3, size))
    sample_bytes = bytearray(size * size * size * 6)
    for b in range(size):
        for g in range(size):
            for r in range(size):
                cube_idx = r + g * size + b * size * size
                r_val, g_val, b_val = samples[cube_idx]
                out_idx = (r * size * size + g * size + b) * 6
                temp_r = (int(round(r_val * 65535)) - nopValue[r]) & 0xFFFF
                temp_g = (int(round(g_val * 65535)) - nopValue[g]) & 0xFFFF
                temp_b = (int(round(b_val * 65535)) - nopValue[b]) & 0xFFFF
                struct.pack_into('<HHH', sample_bytes, out_idx, temp_r, temp_g, temp_b)
    block_data.extend(sample_bytes)
    block_data.extend(struct.pack('<3I', 0, 1, 0))
    block_data.extend(struct.pack('<2d', 0.0, 2.0))
    uncompressed_size = len(block_data)
    md5_hash = hashlib.md5(block_data).hexdigest()
    uuid_str = hashlib.md5((md5_hash + str(int(time.time()))).encode('utf-8')).hexdigest().upper()
    z_data = zlib.compress(block_data, level=zlib.Z_DEFAULT_COMPRESSION)
    compressed_block = struct.pack('<I', uncompressed_size) + z_data
    encoded_str = encode_zlib_base85(compressed_block)

    return f"""<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00        ">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
   crs:PresetType="Look"
   crs:Cluster=""
   crs:UUID="{uuid_str}"
   crs:SupportsAmount="True"
   crs:SupportsColor="True"
   crs:SupportsMonochrome="True"
   crs:SupportsHighDynamicRange="True"
   crs:SupportsNormalDynamicRange="True"
   crs:SupportsSceneReferred="True"
   crs:SupportsOutputReferred="True"
   crs:RequiresRGBTables="False"
   crs:CameraModelRestriction=""
   crs:Copyright=""
   crs:ContactInfo=""
   crs:Version="14.3"
   crs:ProcessVersion="11.0"
   crs:ConvertToGrayscale="False"
   crs:RGBTable="{md5_hash}"
   crs:Table_{md5_hash}="{encoded_str}"
   crs:HasSettings="True">
   <crs:Name>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{title}</rdf:li>
    </rdf:Alt>
   </crs:Name>
   <crs:ShortName>
    <rdf:Alt>
     <rdf:li xml:lang="x-default"/>
    </rdf:Alt>
   </crs:ShortName>
   <crs:SortName>
    <rdf:Alt>
     <rdf:li xml:lang="x-default"/>
    </rdf:Alt>
   </crs:SortName>
   <crs:Group>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">Profiles</rdf:li>
    </rdf:Alt>
   </crs:Group>
   <crs:Description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default"/>
    </rdf:Alt>
   </crs:Description>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
"""

# ============================================================
# TRANSLATIONS
# ============================================================
T = {
    "zh": {
        "title": "CUBE to XMP",
        "subtitle": "专业 LUT 转换工具",
        "tab_library": "LUT 库",
        "tab_convert": "转换",
        "presets": "内置预设",
        "recent": "最近使用",
        "no_presets": "未找到预设文件",
        "no_recent": "暂无转换记录",
        "drop_title": "拖放文件到此处",
        "drop_sub": "支持 .cube 和 .xmp 格式",
        "btn_browse": "选择文件",
        "btn_export": "导出",
        "btn_export_xmp": "导出 XMP",
        "btn_export_cube": "导出 CUBE",
        "lut_info": "LUT 信息",
        "lut_name": "名称",
        "lut_size": "尺寸",
        "lut_type": "类型",
        "lut_path": "路径",
        "params": "输出参数",
        "param_group": "分组",
        "param_desc": "描述",
        "param_cube_size": "导出尺寸",
        "history": "转换历史",
        "ready": "就绪",
        "parsing": "正在解析文件...",
        "building": "正在构建配置文件...",
        "success": "已保存: {filename}",
        "cancelled": "已取消",
        "error": "发生错误",
        "processing": "处理中...",
        "cancel": "取消",
        "preview": "色彩预览",
        "before": "原始",
        "after": "应用 LUT",
        "direction_cube_to_xmp": "CUBE → XMP",
        "direction_xmp_to_cube": "XMP → CUBE",
        "action_convert": "转换",
        "action_clear": "清空历史",
        "file_cube": "CUBE 文件",
        "file_xmp": "XMP 文件",
    },
    "en": {
        "title": "CUBE to XMP",
        "subtitle": "Professional LUT Converter",
        "tab_library": "LUT Library",
        "tab_convert": "Convert",
        "presets": "Built-in Presets",
        "recent": "Recent",
        "no_presets": "No preset files found",
        "no_recent": "No conversion history",
        "drop_title": "Drop files here",
        "drop_sub": "Supports .cube and .xmp formats",
        "btn_browse": "Browse Files",
        "btn_export": "Export",
        "btn_export_xmp": "Export XMP",
        "btn_export_cube": "Export CUBE",
        "lut_info": "LUT Information",
        "lut_name": "Name",
        "lut_size": "Size",
        "lut_type": "Type",
        "lut_path": "Path",
        "params": "Output Parameters",
        "param_group": "Group",
        "param_desc": "Description",
        "param_cube_size": "Output Size",
        "history": "Conversion History",
        "ready": "Ready",
        "parsing": "Parsing file...",
        "building": "Building profile...",
        "success": "Saved: {filename}",
        "cancelled": "Cancelled",
        "error": "Error occurred",
        "processing": "Processing...",
        "cancel": "Cancel",
        "preview": "Color Preview",
        "before": "Original",
        "after": "With LUT",
        "direction_cube_to_xmp": "CUBE → XMP",
        "direction_xmp_to_cube": "XMP → CUBE",
        "action_convert": "Convert",
        "action_clear": "Clear History",
        "file_cube": "CUBE File",
        "file_xmp": "XMP File",
    },
}

# ============================================================
# CUSTOM UI COMPONENTS
# ============================================================

class Card(ctk.CTkFrame):
    """Premium card frame with subtle border and rounded corners."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=C["surface_1"],
            border_width=1,
            border_color=C["border"],
            corner_radius=10,
            **kwargs,
        )

    def _update_theme(self, C_):
        self.configure(fg_color=C_["surface_1"], border_color=C_["border"])


class SectionHeader(ctk.CTkLabel):
    """Uppercase section label with subdued color."""
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent,
            text=text.upper(),
            font=font(11, "bold"),
            text_color=C["text_sec"],
            anchor="w",
            **kwargs,
        )


class PresetItem(ctk.CTkFrame):
    """Clickable preset card in the left sidebar."""
    def __init__(self, parent, name, file_path, on_click=None, **kwargs):
        super().__init__(
            parent,
            fg_color=C["surface_2"],
            border_width=1,
            border_color=C["border"],
            corner_radius=8,
            height=44,
            **kwargs,
        )
        self.file_path = file_path
        self.on_click = on_click
        self._selected = False

        # Dot indicator
        ext = os.path.splitext(name)[1].lower()
        self._dot_is_cube = (ext == ".cube")
        dot_fill = C["accent"] if self._dot_is_cube else C["accent_2"]
        self.dot = tk.Canvas(self, width=8, height=8, bg=C["surface_2"], highlightthickness=0)
        self.dot.create_oval(0, 0, 8, 8, fill=dot_fill, outline="")
        self.dot.pack(side="left", padx=(12, 8), pady=0)
        self.dot.configure(bg=C["surface_2"])

        # Name
        display_name = os.path.splitext(name)[0].replace("_", " ")
        self.label = ctk.CTkLabel(
            self, text=display_name, font=font(12),
            text_color=C["text_sec"], anchor="w",
        )
        self.label.pack(side="left", fill="x", expand=True, padx=(0, 12))

        # Bind click
        for widget in [self, self.label, self.dot]:
            widget.bind("<Button-1>", lambda e: self._handle_click())
            widget.bind("<Enter>", lambda e: self._on_hover(True))
            widget.bind("<Leave>", lambda e: self._on_hover(False))

    def _handle_click(self):
        if self.on_click:
            self.on_click(self.file_path)
        self.set_selected(True)

    def _on_hover(self, entering):
        if not self._selected:
            color = C["surface_3"] if entering else C["surface_2"]
            self.configure(fg_color=color)
            self.dot.configure(bg=color)

    def set_selected(self, selected):
        self._selected = selected
        if selected:
            self.configure(fg_color=C["surface_3"], border_color=C["accent"])
            self.dot.configure(bg=C["surface_3"])
            self.label.configure(text_color=C["text"])
        else:
            self.configure(fg_color=C["surface_2"], border_color=C["border"])
            self.dot.configure(bg=C["surface_2"])
            self.label.configure(text_color=C["text_sec"])

    def _update_theme(self, C_):
        self.configure(fg_color=C_["surface_2"], border_color=C_["border"])
        self.dot.configure(bg=C_["surface_2"])
        self.label.configure(text_color=C_["text_sec"])
        # Redraw the dot
        self.dot.delete("all")
        fill = C_["accent"] if self._dot_is_cube else C_["accent_2"]
        self.dot.create_oval(0, 0, 8, 8, fill=fill, outline="")
        if self._selected:
            self.configure(fg_color=C_["surface_3"], border_color=C_["accent"])
            self.dot.configure(bg=C_["surface_3"])
            self.label.configure(text_color=C_["text"])


class DropZone(ctk.CTkFrame):
    """Premium drag-and-drop zone with visual feedback."""
    def __init__(self, parent, on_click=None, on_drop=None, **kwargs):
        super().__init__(
            parent,
            fg_color=C["drop_bg"],
            border_width=2,
            border_color=C["drop_border"],
            corner_radius=14,
            **kwargs,
        )
        self.on_click_cb = on_click
        self.on_drop_cb = on_drop

        # Register this frame as a DND target so files dropped directly
        # onto the drop zone are handled (not just the parent window).
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)
            self.dnd_bind('<<DragEnter>>', lambda e: self.set_hover(True))
            self.dnd_bind('<<DragLeave>>', lambda e: self.set_hover(False))
        except Exception:
            pass  # parent window DND will catch it as fallback

        # Icon area (drawn with Canvas)
        self.icon_canvas = tk.Canvas(
            self, width=64, height=64,
            bg=C["drop_bg"], highlightthickness=0,
        )
        self.icon_canvas.pack(pady=(30, 8))
        self._draw_icon()

        # Title
        self.title_lbl = ctk.CTkLabel(
            self, text="", font=font(17, "bold"),
            text_color=C["text"],
        )
        self.title_lbl.pack()

        # Subtitle
        self.sub_lbl = ctk.CTkLabel(
            self, text="", font=font(12),
            text_color=C["text_muted"],
        )
        self.sub_lbl.pack(pady=(4, 10))

        # Browse button
        self.browse_btn = ctk.CTkButton(
            self, text="", height=34, width=140,
            font=font(12, "bold"),
            fg_color=C["surface_3"],
            hover_color=C["border_act"],
            border_width=1,
            border_color=C["border"],
            corner_radius=8,
            text_color=C["text"],
            command=self._on_browse,
        )
        self.browse_btn.pack(pady=(0, 30))

        # Bind click on the zone itself
        self.bind("<Button-1>", lambda e: self._on_browse())
        self.title_lbl.bind("<Button-1>", lambda e: self._on_browse())
        self.sub_lbl.bind("<Button-1>", lambda e: self._on_browse())

    def _draw_icon(self):
        """Draw a simple upload arrow icon."""
        c = self.icon_canvas
        c.delete("all")
        # Arrow body
        c.create_line(32, 48, 32, 16, fill=C["text_muted"], width=3, capstyle="round")
        # Arrow head
        c.create_line(32, 16, 22, 28, fill=C["text_muted"], width=3, capstyle="round")
        c.create_line(32, 16, 42, 28, fill=C["text_muted"], width=3, capstyle="round")
        # Bottom tray
        c.create_line(14, 48, 50, 48, fill=C["text_muted"], width=3, capstyle="round")

    def _on_browse(self):
        if self.on_click_cb:
            self.on_click_cb()

    def _on_drop(self, event):
        """Forward drop event to the parent callback."""
        if self.on_drop_cb:
            self.on_drop_cb(event)

    def set_hover(self, active):
        if active:
            self.configure(border_color=C["accent"])
            self.icon_canvas.configure(bg=C["drop_bg"])
            self.icon_canvas.delete("all")
            c = self.icon_canvas
            c.create_line(32, 48, 32, 16, fill=C["accent"], width=3, capstyle="round")
            c.create_line(32, 16, 22, 28, fill=C["accent"], width=3, capstyle="round")
            c.create_line(32, 16, 42, 28, fill=C["accent"], width=3, capstyle="round")
            c.create_line(14, 48, 50, 48, fill=C["accent"], width=3, capstyle="round")
        else:
            self.configure(border_color=C["drop_border"])
            self._draw_icon()

    def _update_theme(self, C_):
        self.configure(fg_color=C_["drop_bg"], border_color=C_["drop_border"])
        self.title_lbl.configure(text_color=C_["text"])
        self.sub_lbl.configure(text_color=C_["text_muted"])
        self.icon_canvas.configure(bg=C_["drop_bg"])
        self.browse_btn.configure(
            fg_color=C_["surface_3"],
            hover_color=C_["border_act"],
            border_color=C_["border"],
            text_color=C_["text"],
        )
        self._draw_icon()


class ColorPreview(ctk.CTkFrame):
    """Color patch comparison: original vs LUT-applied."""
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=C["surface_1"],
            border_width=1,
            border_color=C["border"],
            corner_radius=10,
            **kwargs,
        )

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkLabel(
            self, text="", font=font(12, "bold"),
            text_color=C["text"],
        )
        self.header.grid(row=0, column=0, columnspan=2, pady=(14, 4), sticky="w", padx=16)

        self.lbl_before = ctk.CTkLabel(
            self, text="", font=font(10),
            text_color=C["text_muted"],
        )
        self.lbl_before.grid(row=1, column=0, pady=(0, 4))

        self.lbl_after = ctk.CTkLabel(
            self, text="", font=font(10),
            text_color=C["text_muted"],
        )
        self.lbl_after.grid(row=1, column=1, pady=(0, 4))

        self.canvas_before = tk.Canvas(
            self, width=180, height=110,
            bg=C["surface_2"], highlightthickness=1,
            highlightbackground=C["border"],
        )
        self.canvas_before.grid(row=2, column=0, padx=(16, 8), pady=(0, 16))

        self.canvas_after = tk.Canvas(
            self, width=180, height=110,
            bg=C["surface_2"], highlightthickness=1,
            highlightbackground=C["border"],
        )
        self.canvas_after.grid(row=2, column=1, padx=(8, 16), pady=(0, 16))

        self._draw_default()

    def _draw_default(self):
        colors = [
            ('#FF3B30', 15, 10), ('#34C759', 95, 10), ('#007AFF', 15, 60),
            ('#FFCC00', 95, 60), ('#AF52DE', 55, 10), ('#FF9500', 55, 60),
        ]
        for canvas in [self.canvas_before, self.canvas_after]:
            canvas.delete('all')
            for color, x, y in colors:
                canvas.create_rectangle(x, y, x + 60, y + 40, fill=color, outline='')

    def update_preview(self, samples, size):
        """Apply LUT to reference colors and show comparison."""
        colors = [
            ((1.0, 0.0, 0.0), 15, 10), ((0.0, 1.0, 0.0), 95, 10),
            ((0.0, 0.0, 1.0), 15, 60), ((1.0, 1.0, 0.0), 95, 60),
            ((1.0, 0.0, 1.0), 55, 10), ((0.0, 1.0, 1.0), 55, 60),
        ]
        self.canvas_after.delete('all')
        for (r, g, b), x, y in colors:
            nr, ng, nb = self._apply_lut(r, g, b, samples, size)
            hex_color = f'#{int(nr*255):02x}{int(ng*255):02x}{int(nb*255):02x}'
            self.canvas_after.create_rectangle(x, y, x + 60, y + 40, fill=hex_color, outline='')

    def _apply_lut(self, r, g, b, samples, size):
        r_idx = r * (size - 1)
        g_idx = g * (size - 1)
        b_idx = b * (size - 1)
        r0, g0, b0 = int(r_idx), int(g_idx), int(b_idx)
        r1, g1, b1 = min(r0 + 1, size - 1), min(g0 + 1, size - 1), min(b0 + 1, size - 1)
        fr, fg, fb = r_idx - r0, g_idx - g0, b_idx - b0

        def sample(ri, gi, bi):
            idx = ri + gi * size + bi * size * size
            return samples[idx] if idx < len(samples) else (0.0, 0.0, 0.0)

        c000, c100 = sample(r0, g0, b0), sample(r1, g0, b0)
        c010, c110 = sample(r0, g1, b0), sample(r1, g1, b0)
        c001, c101 = sample(r0, g0, b1), sample(r1, g0, b1)
        c011, c111 = sample(r0, g1, b1), sample(r1, g1, b1)

        result = []
        for ch in range(3):
            val = (c000[ch] * (1-fr) * (1-fg) * (1-fb) +
                   c100[ch] * fr * (1-fg) * (1-fb) +
                   c010[ch] * (1-fr) * fg * (1-fb) +
                   c110[ch] * fr * fg * (1-fb) +
                   c001[ch] * (1-fr) * (1-fg) * fb +
                   c101[ch] * fr * (1-fg) * fb +
                   c011[ch] * (1-fr) * fg * fb +
                   c111[ch] * fr * fg * fb)
            result.append(max(0.0, min(1.0, val)))
        return tuple(result)

    def _update_theme(self, C_):
        self.configure(fg_color=C_["surface_1"], border_color=C_["border"])
        self.header.configure(text_color=C_["text"])
        self.lbl_before.configure(text_color=C_["text_muted"])
        self.lbl_after.configure(text_color=C_["text_muted"])
        for c in [self.canvas_before, self.canvas_after]:
            c.configure(bg=C_["surface_2"], highlightbackground=C_["border"])


class HistoryItem(ctk.CTkFrame):
    """Single entry in the conversion history queue."""
    def __init__(self, parent, filename, direction, status, timestamp, **kwargs):
        super().__init__(
            parent,
            fg_color=C["surface_2"],
            border_width=1,
            border_color=C["border"],
            corner_radius=6,
            height=32,
            **kwargs,
        )
        self._status_ok = (status == "ok")
        self._is_cube_dir = ("CUBE" in direction)

        # Status dot
        dot_fill = C["success"] if self._status_ok else C["error"]
        self._dot = tk.Canvas(self, width=8, height=8, bg=C["surface_2"], highlightthickness=0)
        self._dot.create_oval(0, 0, 8, 8, fill=dot_fill, outline="")
        self._dot.pack(side="left", padx=(10, 8))

        # Filename
        ctk.CTkLabel(
            self, text=filename[:28], font=font(11),
            text_color=C["text_sec"], anchor="w",
        ).pack(side="left")

        # Direction badge
        badge_fill = C["accent"] if self._is_cube_dir else C["accent_2"]
        ctk.CTkLabel(
            self, text=direction, font=font(9, "bold"),
            text_color=badge_fill,
        ).pack(side="left", padx=(8, 0))

        # Timestamp (right-aligned)
        ctk.CTkLabel(
            self, text=timestamp, font=font(9),
            text_color=C["text_muted"],
        ).pack(side="right", padx=(0, 10))

    def _update_theme(self, C_):
        self.configure(fg_color=C_["surface_2"], border_color=C_["border"])
        # Redraw status dot
        self._dot.configure(bg=C_["surface_2"])
        self._dot.delete("all")
        fill = C_["success"] if self._status_ok else C_["error"]
        self._dot.create_oval(0, 0, 8, 8, fill=fill, outline="")
        # Update labels
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkLabel):
                txt = child.cget("text")
                if txt and ("CUBE" in txt or "XMP" in txt):
                    child.configure(text_color=C_["accent"] if "CUBE" in txt else C_["accent_2"])
                elif txt and ":" in txt:
                    child.configure(text_color=C_["text_muted"])
                else:
                    child.configure(text_color=C_["text_sec"])


# ============================================================
# MAIN APPLICATION
# ============================================================

class App(ctk.CTk, TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        # --- State ---
        self.lang = "zh"
        self._theme = "dark"
        self.current_file = None
        self.current_lut = None  # (title, size, samples)
        self._header_icon = None  # loaded icon image for header
        self.history = []
        self.preset_items = []

        # --- Window (native) ---
        self.title("CUBE to XMP")
        self.geometry("1200x780")
        self.minsize(960, 640)
        self.configure(fg_color=C["bg"])

        # Set icon
        icon_path = os.path.join(BASE_PATH, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # --- Drag & Drop ---
        # CTk.__init__ calls tkinter.Tk.__init__ directly (via CTK_PARENT_CLASS),
        # which SKIPS TkinterDnD.Tk.__init__ in the MRO. As a result the tkdnd
        # library is never loaded and DND silently fails. We must call
        # TkinterDnD._require(self) manually to load it.
        try:
            self.TkdndVersion = TkinterDnD._require(self)
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self._on_drop)
        except Exception as e:
            print(f"[DND] init failed: {e}")

        # --- Grid ---
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ============================================================
        # HEADER BAR
        # ============================================================
        self.topbar = ctk.CTkFrame(
            self, fg_color=C["surface_0"], corner_radius=0, height=44,
        )
        self.topbar.grid(row=0, column=0, sticky="ew")
        self.topbar.grid_propagate(False)

        # Logo + app name
        self.logo_frame = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.logo_frame.pack(side="left", padx=(16, 0), pady=3)

        # Load icon for header display
        icon_path = os.path.join(BASE_PATH, "icon.ico")
        if os.path.exists(icon_path):
            try:
                from PIL import Image
                img = Image.open(icon_path)
                # Pick the best size from the ICO
                img = img.resize((28, 28), Image.LANCZOS)
                self._header_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(28, 28))
                icon_lbl = ctk.CTkLabel(self.logo_frame, image=self._header_icon, text="")
                icon_lbl.pack(side="left", padx=(0, 10))
            except Exception:
                # Fallback to green dot
                dot = tk.Canvas(self.logo_frame, width=10, height=10, bg=C["surface_0"], highlightthickness=0)
                dot.create_oval(0, 0, 10, 10, fill=C["accent"], outline="")
                dot.pack(side="left", padx=(0, 10))
        else:
            # Fallback to green dot
            dot = tk.Canvas(self.logo_frame, width=10, height=10, bg=C["surface_0"], highlightthickness=0)
            dot.create_oval(0, 0, 10, 10, fill=C["accent"], outline="")
            dot.pack(side="left", padx=(0, 10))

        self.subtitle_lbl = ctk.CTkLabel(
            self.logo_frame, text="",
            font=font(12), text_color=C["text_muted"],
        )
        self.subtitle_lbl.pack(side="left")

        # Theme + language buttons
        top_right = ctk.CTkFrame(self.topbar, fg_color="transparent")
        top_right.pack(side="right", padx=(0, 12), pady=5)

        self.theme_btn = ctk.CTkButton(
            top_right, text="\u263E", width=28, height=28,
            font=font(14),
            fg_color=C["surface_2"], hover_color=C["surface_3"],
            border_width=1, border_color=C["border"],
            corner_radius=6, text_color=C["text_sec"],
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="left", padx=(0, 6))

        self.lang_btn = ctk.CTkButton(
            top_right, text="EN", width=40, height=28,
            font=font(11, "bold"),
            fg_color=C["surface_2"], hover_color=C["surface_3"],
            border_width=1, border_color=C["border"],
            corner_radius=6, text_color=C["text_sec"],
            command=self._toggle_language,
        )
        self.lang_btn.pack(side="left")

        # ============================================================
        # MAIN CONTENT — 3 columns
        # ============================================================
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.main.grid_columnconfigure(0, weight=0, minsize=240)   # Left
        self.main.grid_columnconfigure(1, weight=1)                 # Center
        self.main.grid_columnconfigure(2, weight=0, minsize=260)   # Right
        self.main.grid_rowconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=0, minsize=140)      # Bottom queue

        # ---- LEFT PANEL ----
        self._build_left_panel()

        # ---- CENTER PANEL ----
        self._build_center_panel()

        # ---- RIGHT PANEL ----
        self._build_right_panel()

        # ---- BOTTOM QUEUE ----
        self._build_bottom_queue()

        # ============================================================
        # STATUS BAR
        # ============================================================
        self.statusbar = ctk.CTkFrame(
            self, fg_color=C["surface_0"], corner_radius=0, height=32,
        )
        self.statusbar.grid(row=2, column=0, sticky="ew")
        self.statusbar.grid_propagate(False)

        self.status_lbl = ctk.CTkLabel(
            self.statusbar, text="",
            font=font(11), text_color=C["text_muted"],        )
        self.status_lbl.pack(side="left", padx=14, pady=5)

        # --- Final setup ---
        self._refresh_texts()
        self.set_status("ready")

    # ============================================================
    # BUILD LEFT PANEL
    # ============================================================
    def _build_left_panel(self):
        self.left_panel = ctk.CTkFrame(
            self.main, fg_color=C["surface_0"], corner_radius=10,
        )
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(6, 3), rowspan=2)

        # Presets section
        self.presets_header = SectionHeader(self.left_panel, text="")
        self.presets_header.pack(fill="x", padx=14, pady=(16, 8))
        self.presets_container = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.presets_container.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        self._load_presets()

        # Recent section
        self.recent_header = SectionHeader(self.left_panel, text="")
        self.recent_header.pack(fill="x", padx=14, pady=(12, 8))
        self.recent_container = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.recent_container.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.no_recent_lbl = ctk.CTkLabel(
            self.recent_container, text="",
            font=font(11), text_color=C["text_muted"],
        )
        self.no_recent_lbl.pack(pady=20)

    def _load_presets(self):
        built_in_luts_path = os.path.join(BASE_PATH, "built_in_luts")
        if not os.path.exists(built_in_luts_path):
            self.no_presets_lbl = ctk.CTkLabel(
                self.presets_container, text="",
                font=font(11), text_color=C["text_muted"],
            )
            self.no_presets_lbl.pack(pady=20)
            return

        files = sorted([f for f in os.listdir(built_in_luts_path) if f.endswith(('.cube', '.xmp'))])
        if not files:
            self.no_presets_lbl = ctk.CTkLabel(
                self.presets_container, text="",
                font=font(11), text_color=C["text_muted"],
            )
            self.no_presets_lbl.pack(pady=20)
            return

        self.preset_items = []
        for fname in files:
            path = os.path.join(built_in_luts_path, fname)
            item = PresetItem(
                self.presets_container, fname, path,
                on_click=self._on_preset_click,
            )
            item.pack(fill="x", pady=2)
            self.preset_items.append(item)

    def _on_preset_click(self, file_path):
        """When a preset is clicked, load it for preview."""
        for item in self.preset_items:
            item.set_selected(item.file_path == file_path)
        self._load_file(file_path)

    # ============================================================
    # BUILD CENTER PANEL
    # ============================================================
    def _build_center_panel(self):
        self.center_panel = ctk.CTkFrame(
            self.main, fg_color="transparent",
        )
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=3)
        self.center_panel.grid_columnconfigure(0, weight=1)
        self.center_panel.grid_rowconfigure(0, weight=1)

        # Drop zone (shown when no file loaded)
        self.drop_zone = DropZone(
            self.center_panel, on_click=self._browse_file, on_drop=self._on_drop,
        )
        self.drop_zone.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Preview area (shown when file is loaded)
        self.preview = ColorPreview(self.center_panel)

    # ============================================================
    # BUILD RIGHT PANEL
    # ============================================================
    def _build_right_panel(self):
        self.right_panel = ctk.CTkFrame(
            self.main, fg_color=C["surface_0"], corner_radius=10,
        )
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(3, 6), rowspan=2)
        self.right_panel.grid_columnconfigure(0, weight=1)

        # LUT Info section
        self.lut_info_header = SectionHeader(self.right_panel, text="")
        self.lut_info_header.pack(fill="x", padx=14, pady=(16, 10))

        self.info_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.info_frame.pack(fill="x", padx=14)
        self.info_frame.grid_columnconfigure(1, weight=1)

        info_fields = [
            ("lut_name", "—"),
            ("lut_size", "—"),
            ("lut_type", "—"),
            ("lut_path", "—"),
        ]
        self.info_labels = {}
        for i, (key, default) in enumerate(info_fields):
            lbl = ctk.CTkLabel(
                self.info_frame, text="",
                font=font(11), text_color=C["text_muted"],            )
            lbl.grid(row=i, column=0, sticky="w", pady=3, padx=(0, 12))
            val = ctk.CTkLabel(
                self.info_frame, text=default,
                font=font(11), text_color=C["text"],
                anchor="w",
            )
            val.grid(row=i, column=1, sticky="ew", pady=3)
            self.info_labels[key] = val

        # Parameters section
        self.params_header = SectionHeader(self.right_panel, text="")
        self.params_header.pack(fill="x", padx=14, pady=(18, 10))

        self.params_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.params_frame.pack(fill="x", padx=14)
        self.params_frame.grid_columnconfigure(1, weight=1)

        # Group entry
        self.param_group_lbl = ctk.CTkLabel(
            self.params_frame, text="",
            font=font(11), text_color=C["text_muted"],
        )
        self.param_group_lbl.grid(row=0, column=0, sticky="w", pady=3, padx=(0, 12))
        self.group_entry = ctk.CTkEntry(
            self.params_frame, height=30,
            font=font(11), fg_color=C["surface_2"],
            border_color=C["border"], corner_radius=6,
            text_color=C["text"],
        )
        self.group_entry.grid(row=0, column=1, sticky="ew", pady=3)
        self.group_entry.insert(0, "Profiles")

        # Description entry
        self.param_desc_lbl = ctk.CTkLabel(
            self.params_frame, text="",
            font=font(11), text_color=C["text_muted"],
        )
        self.param_desc_lbl.grid(row=1, column=0, sticky="w", pady=3, padx=(0, 12))
        self.desc_entry = ctk.CTkEntry(
            self.params_frame, height=30,
            font=font(11), fg_color=C["surface_2"],
            border_color=C["border"], corner_radius=6,
            text_color=C["text"],
        )
        self.desc_entry.grid(row=1, column=1, sticky="ew", pady=3)

        # Cube output size selector
        self.param_size_lbl = ctk.CTkLabel(
            self.params_frame, text="",
            font=font(11), text_color=C["text_muted"],
        )
        self.param_size_lbl.grid(row=2, column=0, sticky="w", pady=3, padx=(0, 12))
        self.cube_size_var = tk.StringVar(value="33")
        self.cube_size_menu = ctk.CTkOptionMenu(
            self.params_frame,
            values=[str(s) for s in CUBE_SIZE_PRESETS],
            variable=self.cube_size_var,
            height=30, font=font(11),
            fg_color=C["surface_2"],
            button_color=C["accent"],
            button_hover_color=C["accent_dim"],
            dropdown_fg_color=C["surface_0"],
            dropdown_text_color=C["text"],
            dropdown_hover_color=C["surface_3"],
            text_color=C["text"],
            corner_radius=6,
        )
        self.cube_size_menu.grid(row=2, column=1, sticky="ew", pady=3)
        # Export button
        self.export_btn = ctk.CTkButton(
            self.right_panel, text="", height=40,
            font=font(13, "bold"),
            fg_color=C["accent"], hover_color=C["accent_dim"],
            corner_radius=8, text_color="#FFFFFF",
            command=self._export,
        )
        self.export_btn.pack(fill="x", padx=14, pady=(20, 16))

        # Disable export initially
        self.export_btn.configure(state="disabled", fg_color=C["surface_2"], text_color=C["text_muted"])

    # ============================================================
    # BUILD BOTTOM QUEUE
    # ============================================================
    def _build_bottom_queue(self):
        self.queue_frame = ctk.CTkFrame(
            self.main, fg_color=C["surface_0"], corner_radius=10,
        )
        self.queue_frame.grid(row=1, column=1, sticky="nsew", padx=3, pady=(4, 0))

        # Header row
        header_row = ctk.CTkFrame(self.queue_frame, fg_color="transparent")
        header_row.pack(fill="x", padx=14, pady=(10, 4))

        self.history_header = SectionHeader(header_row, text="")
        self.history_header.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            header_row, text="", width=70, height=22,
            font=font(9), fg_color=C["surface_2"],
            hover_color=C["surface_3"], border_width=1,
            border_color=C["border"], corner_radius=5,
            text_color=C["text_muted"], command=self._clear_history,
        )
        self.clear_btn.pack(side="right")

        # Scrollable history
        self.history_scroll = ctk.CTkScrollableFrame(
            self.queue_frame, fg_color=C["surface_0"],
        )
        self.history_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        self.no_history_lbl = ctk.CTkLabel(
            self.history_scroll, text="",
            font=font(11), text_color=C["text_muted"],
        )
        self.no_history_lbl.pack(pady=20)

    # ============================================================
    # TEXT / I18N
    # ============================================================
    def tr(self, key):
        return T[self.lang].get(key, key)

    def _toggle_language(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.lang_btn.configure(text="EN" if self.lang == "zh" else "中文")
        self._refresh_texts()

    def _toggle_theme(self):
        """Toggle between dark and light themes."""
        global C
        if self._theme == "dark":
            self._theme = "light"
            C.update(C_LIGHT)
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="\u263C")
            self.theme_btn.configure(text_color=C["text_sec"])
        else:
            self._theme = "dark"
            C.update(C_DARK)
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="\u263E")
            self.theme_btn.configure(text_color=C["text_sec"])
        self._apply_theme()

    def _apply_theme(self):
        """Recolour all custom widgets after theme switch."""
        C_ = C

        # --- Header ---
        self.configure(fg_color=C_["bg"])
        self.topbar.configure(fg_color=C_["surface_0"])
        if hasattr(self, 'topbar'):
            self.topbar.configure(border_color=C_["border"])

        # --- Logo dot canvas ---
        for child in self.logo_frame.winfo_children():
            if isinstance(child, tk.Canvas):
                child.configure(bg=C_["surface_0"])
                child.delete("all")
                child.create_oval(0, 0, 10, 10, fill=C_["accent"], outline="")

        # --- Subtitle label ---
        self.subtitle_lbl.configure(text_color=C_["text_muted"])

        # --- Header buttons ---
        for btn in [self.theme_btn, self.lang_btn]:
            btn.configure(
                fg_color=C_["surface_2"],
                hover_color=C_["surface_3"],
                border_color=C_["border"],
                text_color=C_["text_sec"],
            )

        # --- Drop zone ---
        self.drop_zone._update_theme(C_)

        # --- Preview ---
        if hasattr(self, 'preview'):
            self.preview._update_theme(C_)

        # --- Left panel ---
        self.left_panel.configure(fg_color=C_["surface_0"])
        # Section headers
        for child in self.left_panel.winfo_children():
            if isinstance(child, SectionHeader):
                child.configure(text_color=C_["text_sec"])
            elif isinstance(child, ctk.CTkFrame):
                child.configure(fg_color="transparent")

        # Preset items (inside containers)
        for container in [getattr(self, 'presets_container', None), getattr(self, 'recent_container', None)]:
            if container is None:
                continue
            container.configure(fg_color="transparent")
            for child in container.winfo_children():
                if isinstance(child, PresetItem):
                    child._update_theme(C_)
                elif isinstance(child, ctk.CTkLabel):
                    child.configure(text_color=C_["text_muted"])

        # No-presets / no-recent labels
        for attr in ['no_presets_lbl', 'no_recent_lbl']:
            if hasattr(self, attr) and getattr(self, attr).winfo_exists():
                getattr(self, attr).configure(text_color=C_["text_muted"])

        # --- Right panel ---
        self.right_panel.configure(fg_color=C_["surface_0"])
        for child in self.right_panel.winfo_children():
            if isinstance(child, SectionHeader):
                child.configure(text_color=C_["text_sec"])
            elif isinstance(child, Card):
                child._update_theme(C_)
            elif isinstance(child, ctk.CTkFrame):
                child.configure(fg_color="transparent")
            elif isinstance(child, ctk.CTkButton):
                child.configure(
                    fg_color=C_["surface_2"],
                    hover_color=C_["surface_3"],
                    border_color=C_["border"],
                    text_color=C_["text_sec"],
                )

        # Right panel info/param labels (inside info_frame, params_frame)
        for frame_attr in ['info_frame', 'params_frame']:
            frame = getattr(self, frame_attr, None)
            if frame is None:
                continue
            for child in frame.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    child.configure(text_color=C_["text_muted"])
                elif isinstance(child, ctk.CTkEntry):
                    child.configure(
                        fg_color=C_["surface_2"],
                        border_color=C_["border"],
                        text_color=C_["text"],
                    )
                elif isinstance(child, ctk.CTkOptionMenu):
                    child.configure(
                        fg_color=C_["surface_2"],
                        button_color=C_["accent"],
                        button_hover_color=C_["accent_dim"],
                        dropdown_fg_color=C_["surface_0"],
                        dropdown_text_color=C_["text"],
                        dropdown_hover_color=C_["surface_3"],
                        text_color=C_["text"],
                    )

        # --- Bottom history ---
        self.queue_frame.configure(fg_color=C_["surface_0"])
        if hasattr(self, 'history_scroll'):
            self.history_scroll.configure(fg_color=C_["surface_0"])
            for child in self.history_scroll.winfo_children():
                if isinstance(child, HistoryItem):
                    child._update_theme(C_)
                elif isinstance(child, ctk.CTkLabel):
                    child.configure(text_color=C_["text_muted"])

        # --- Export button ---
        if self.current_file:
            self.export_btn.configure(
                fg_color=C_["accent"],
                hover_color=C_["accent_dim"],
                text_color="#FFFFFF",
            )
        else:
            self.export_btn.configure(
                fg_color=C_["surface_2"],
                hover_color=C_["surface_3"],
                border_color=C_["border"],
                text_color=C_["text_muted"],
            )

        # --- History header ---
        if hasattr(self, 'history_header'):
            self.history_header.configure(text_color=C_["text_sec"])
        if hasattr(self, 'clear_btn'):
            self.clear_btn.configure(
                fg_color=C_["surface_2"],
                hover_color=C_["surface_3"],
                border_color=C_["border"],
                text_color=C_["text_muted"],
            )
        if hasattr(self, 'no_history_lbl'):
            self.no_history_lbl.configure(text_color=C_["text_muted"])
        if hasattr(self, 'no_recent_lbl'):
            self.no_recent_lbl.configure(text_color=C_["text_muted"])

        # --- Status bar ---
        if hasattr(self, 'statusbar'):
            self.statusbar.configure(fg_color=C_["surface_0"], border_color=C_["border"])
        if hasattr(self, 'status_lbl'):
            self.status_lbl.configure(text_color=C_["text_muted"])

        # --- Center frame ---
        if hasattr(self, 'center_panel'):
            self.center_panel.configure(fg_color="transparent")
        if hasattr(self, 'main'):
            self.main.configure(fg_color="transparent")

        # Force flush — ensures all widgets render with new colors immediately
        self.update_idletasks()

    def _refresh_texts(self):
        """Refresh all UI text to current language."""
        self.subtitle_lbl.configure(text=self.tr("subtitle"))
        self._update_section_headers()

        # Drop zone
        self.drop_zone.title_lbl.configure(text=self.tr("drop_title"))
        self.drop_zone.sub_lbl.configure(text=self.tr("drop_sub"))
        self.drop_zone.browse_btn.configure(text=self.tr("btn_browse"))

        # Preview
        self.preview.header.configure(text=self.tr("preview"))
        self.preview.lbl_before.configure(text=self.tr("before"))
        self.preview.lbl_after.configure(text=self.tr("after"))

        # History
        self.history_header.configure(text=self.tr("history").upper())
        self.clear_btn.configure(text=self.tr("action_clear"))
        self.no_history_lbl.configure(text=self.tr("no_recent"))
        self.no_recent_lbl.configure(text=self.tr("no_recent"))

        # Export button
        self._update_export_button_text()

    def _update_section_headers(self):
        """Update all section header and label texts."""
        self.presets_header.configure(text=self.tr("presets").upper())
        self.recent_header.configure(text=self.tr("recent").upper())
        self.lut_info_header.configure(text=self.tr("lut_info").upper())
        self.params_header.configure(text=self.tr("params").upper())

        # Param labels
        self.param_group_lbl.configure(text=self.tr("param_group"))
        self.param_desc_lbl.configure(text=self.tr("param_desc"))
        self.param_size_lbl.configure(text=self.tr("param_cube_size"))

        # Info labels
        info_widgets = list(self.info_frame.winfo_children())
        for key, idx in [("lut_name", 0), ("lut_size", 2), ("lut_type", 4), ("lut_path", 6)]:
            if idx < len(info_widgets):
                info_widgets[idx].configure(text=self.tr(key))

        # No presets label
        if hasattr(self, 'no_presets_lbl') and self.no_presets_lbl.winfo_exists():
            self.no_presets_lbl.configure(text=self.tr("no_presets"))

    def _update_export_button_text(self):
        if self.current_file:
            ext = os.path.splitext(self.current_file)[1].lower()
            if ext == '.cube':
                self.export_btn.configure(text=self.tr("btn_export_xmp"))
            else:
                self.export_btn.configure(text=self.tr("btn_export_cube"))
        else:
            self.export_btn.configure(text=self.tr("btn_export"))

    # ============================================================
    # FILE HANDLING
    # ============================================================
    def _on_drop(self, event):
        # tkdnd delivers paths wrapped in {} (spaces) or bare; handle both.
        raw = event.data.strip()
        if raw.startswith('{') and raw.endswith('}'):
            file_path = raw[1:-1]
        elif raw.startswith('"') and raw.endswith('"'):
            file_path = raw[1:-1]
        else:
            file_path = raw
        # If multiple files dropped, take the first one
        if ' ' in file_path and not os.path.exists(file_path):
            file_path = file_path.split(' ')[0].strip('{}').strip('"')
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.cube', '.xmp']:
                self._load_file(file_path)
            else:
                messagebox.showerror(
                    "Error" if self.lang == "en" else "错误",
                    "Unsupported format. Please use .cube or .xmp files."
                    if self.lang == "en" else "不支持的文件格式，请使用 .cube 或 .xmp 文件。"
                )

    def _browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("LUT files", "*.cube;*.xmp"),
                ("CUBE files", "*.cube"),
                ("XMP files", "*.xmp"),
            ],
        )
        if file_path:
            self._load_file(file_path)

    def _load_file(self, file_path):
        """Load a .cube or .xmp file and show preview + info."""
        self.current_file = file_path
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == '.cube':
                title, size, samples = parse_cube(file_path)
                self.current_lut = (title, size, samples, "CUBE")
            else:
                title, size, samples = parse_xmp(file_path)
                self.current_lut = (title, size, samples, "XMP")

            # Show preview area, hide drop zone
            self.drop_zone.grid_remove()
            self.preview.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
            self.preview.update_preview(samples, size)

            # Update info panel
            self.info_labels["lut_name"].configure(text=title)
            self.info_labels["lut_size"].configure(text=f"{size} x {size} x {size}")
            self.info_labels["lut_type"].configure(
                text=self.tr("file_cube") if ext == '.cube' else self.tr("file_xmp")
            )
            # Truncate path for display
            display_path = file_path
            if len(display_path) > 45:
                display_path = "..." + display_path[-42:]
            self.info_labels["lut_path"].configure(text=display_path)

            # Enable export
            self.export_btn.configure(
                state="normal", fg_color=C["accent"],
                hover_color=C["accent_dim"], text_color="#FFFFFF",
            )
            self._update_export_button_text()

            # Set default output size to nearest preset
            nearest = min(CUBE_SIZE_PRESETS, key=lambda s: abs(s - size))
            self.cube_size_var.set(str(nearest))

            # Update preset selection
            for item in self.preset_items:
                item.set_selected(item.file_path == file_path)

            self.set_status("ready")

        except Exception as e:
            messagebox.showerror(
                "Error" if self.lang == "en" else "错误",
                f"Failed to load file:\n{str(e)}"
                if self.lang == "en" else f"加载文件失败:\n{str(e)}"
            )
            self.set_status("error")

    # ============================================================
    # EXPORT
    # ============================================================
    def _export(self):
        if not self.current_file or not self.current_lut:
            return

        title, size, samples, source_type = self.current_lut
        ext = os.path.splitext(self.current_file)[1].lower()
        target_size = int(self.cube_size_var.get())  # user-selected output size

        self.set_status("processing")

        try:
            if ext == '.cube':
                # CUBE → XMP — interpolate to target size if different
                out_title = f"{title}_{target_size}x{target_size}" if target_size != size else title
                if target_size != size:
                    out_samples = interpolate_3d(samples, size, target_size)
                    out_size = target_size
                else:
                    out_samples, out_size = samples, size
                xmp_content = build_xmp(out_title, out_size, out_samples)
                default_name = os.path.basename(self.current_file).replace(".cube", ".xmp")
                out_path = filedialog.asksaveasfilename(
                    title=self.tr("btn_export_xmp"),
                    defaultextension=".xmp",
                    filetypes=[("XMP files", "*.xmp")],
                    initialfile=default_name,
                )
                if out_path:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(xmp_content)
                    self._add_history(os.path.basename(out_path), "CUBE → XMP", "ok")
                    self.set_status("success", filename=os.path.basename(out_path))
            else:
                # XMP → CUBE — interpolate to user-selected size
                if target_size != size:
                    out_samples = interpolate_3d(samples, size, target_size)
                    out_size = target_size
                else:
                    out_samples, out_size = samples, size
                cube_content = build_cube(title, out_size, out_samples)
                default_name = os.path.basename(self.current_file).replace(".xmp", ".cube")
                out_path = filedialog.asksaveasfilename(
                    title=self.tr("btn_export_cube"),
                    defaultextension=".cube",
                    filetypes=[("CUBE files", "*.cube")],
                    initialfile=default_name,
                )
                if out_path:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(cube_content)
                    self._add_history(os.path.basename(out_path), "XMP → CUBE", "ok")
                    self.set_status("success", filename=os.path.basename(out_path))

            if not out_path:
                self.set_status("cancelled")

        except Exception as e:
            self._add_history(os.path.basename(self.current_file), "ERROR", "fail")
            self.set_status("error")
            messagebox.showerror(
                "Error" if self.lang == "en" else "错误",
                f"Conversion failed:\n{str(e)}"
                if self.lang == "en" else f"转换失败:\n{str(e)}"
            )

    # ============================================================
    # HISTORY
    # ============================================================
    def _add_history(self, filename, direction, status):
        now = datetime.now().strftime("%H:%M:%S")
        self.history.insert(0, (filename, direction, status, now))
        if len(self.history) > 50:
            self.history = self.history[:50]
        self._refresh_history()

    def _refresh_history(self):
        # Clear existing
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        if not self.history:
            self.no_history_lbl = ctk.CTkLabel(
                self.history_scroll, text=self.tr("no_recent"),
                font=font(11), text_color=C["text_muted"],
            )
            self.no_history_lbl.pack(pady=20)
            return

        for filename, direction, status, ts in self.history:
            item = HistoryItem(self.history_scroll, filename, direction, status, ts)
            item.pack(fill="x", pady=1)

    def _clear_history(self):
        self.history.clear()
        self._refresh_history()

    # ============================================================
    # STATUS BAR
    # ============================================================
    def set_status(self, key, **kwargs):
        msg = self.tr(key)
        if kwargs:
            msg = msg.format(**kwargs)
        self.status_lbl.configure(text=msg)

        # Color the status
        if key == "success":
            self.status_lbl.configure(text_color=C["success"])
        elif key == "error":
            self.status_lbl.configure(text_color=C["error"])
        elif key == "processing":
            self.status_lbl.configure(text_color=C["accent"])
        else:
            self.status_lbl.configure(text_color=C["text_muted"])


# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    app = App()
    app.mainloop()
