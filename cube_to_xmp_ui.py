import os
import re
import struct
import zlib
import hashlib
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES
from datetime import datetime

# Configure global customtkinter settings
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

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
    kDecodeTable = {}
    for i, c in enumerate(kEncodeTable):
        kDecodeTable[c] = i
    compressed_data = bytearray()
    val = 0
    phase = 0
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
    nopValue = [(i * 0xFFFF + (size // 2)) // (size - 1) for i in range(size)]
    samples = []
    lut_3d = [[[ (0,0,0) for _ in range(size)] for _ in range(size)] for _ in range(size)]
    offset = 16
    for b in range(size):
        for g in range(size):
            for r in range(size):
                if offset + 6 > len(block_data):
                    break
                temp_r, temp_g, temp_b = struct.unpack('<HHH', block_data[offset:offset+6])
                offset += 6
                r_val = (temp_r + nopValue[r]) / 65535.0
                g_val = (temp_g + nopValue[g]) / 65535.0
                b_val = (temp_b + nopValue[b]) / 65535.0
                lut_3d[r][g][b] = (r_val, g_val, b_val)
    for b in range(size):
        for g in range(size):
            for r in range(size):
                samples.append(lut_3d[r][g][b])
    return title, size, samples

def build_cube(title, size, samples):
    lines = []
    lines.append(f'TITLE "{title}"')
    lines.append(f'LUT_3D_SIZE {size}')
    lines.append('DOMAIN_MIN 0.0 0.0 0.0')
    lines.append('DOMAIN_MAX 1.0 1.0 1.0')
    lines.append('')
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
                        r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                        samples.append((r, g, b))
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
                    c0 = get_sample(r0, g0, b0)
                    c1 = get_sample(r0, g1, b0)
                    c2 = get_sample(r0, g1, b1)
                    c3 = get_sample(r1, g1, b1)
                    w0, w1, w2, w3 = 1 - fg, fg - fb, fb - fr, fr
                elif fb > fr and fr > fg:
                    c0 = get_sample(r0, g0, b0)
                    c1 = get_sample(r0, g0, b1)
                    c2 = get_sample(r1, g0, b1)
                    c3 = get_sample(r1, g1, b1)
                    w0, w1, w2, w3 = 1 - fb, fb - fr, fr - fg, fg
                elif fb > fg and fg >= fr:
                    c0 = get_sample(r0, g0, b0)
                    c1 = get_sample(r0, g0, b1)
                    c2 = get_sample(r0, g1, b1)
                    c3 = get_sample(r1, g1, b1)
                    w0, w1, w2, w3 = 1 - fb, fb - fg, fg - fr, fr
                elif fr >= fg and fg > fb:
                    c0 = get_sample(r0, g0, b0)
                    c1 = get_sample(r1, g0, b0)
                    c2 = get_sample(r1, g1, b0)
                    c3 = get_sample(r1, g1, b1)
                    w0, w1, w2, w3 = 1 - fr, fr - fg, fg - fb, fb
                elif fg > fr and fr >= fb:
                    c0 = get_sample(r0, g0, b0)
                    c1 = get_sample(r0, g1, b0)
                    c2 = get_sample(r1, g1, b0)
                    c3 = get_sample(r1, g1, b1)
                    w0, w1, w2, w3 = 1 - fg, fg - fr, fr - fb, fb
                else:
                    c0 = get_sample(r0, g0, b0)
                    c1 = get_sample(r1, g0, b0)
                    c2 = get_sample(r1, g0, b1)
                    c3 = get_sample(r1, g1, b1)
                    w0, w1, w2, w3 = 1 - fr, fr - fb, fb - fg, fg
                out_r = c0[0]*w0 + c1[0]*w1 + c2[0]*w2 + c3[0]*w3
                out_g = c0[1]*w0 + c1[1]*w1 + c2[1]*w2 + c3[1]*w3
                out_b = c0[2]*w0 + c1[2]*w1 + c2[2]*w2 + c3[2]*w3
                new_samples.append((out_r, out_g, out_b))
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
    xmp_template = f"""<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Adobe XMP Core 7.0-c000 1.000000, 0000/00/00-00:00:00        ">
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
    return xmp_template

TRANSLATIONS = {
    "bg_primary": "#0a0a0a",
    "bg_secondary": "#141414",
    "bg_tertiary": "#1e1e1e",
    "bg_card": "#1a1a1a",
    "accent": "#3d3d3d",
    "accent_hover": "#4a4a4a",
    "accent_active": "#555555",
    "text_primary": "#ffffff",
    "text_secondary": "#a0a0a0",
    "text_muted": "#666666",
    "border": "#2a2a2a",
    "border_light": "#333333",
    "success": "#4caf50",
    "warning": "#ff9800",
    "error": "#f44336",
    "info": "#2196f3",
    "drop_zone": "#1a1a1a",
    "drop_zone_active": "#252525",
}

# ... [保持原有的解析和构建函数不变] ...

# [这里会包含 parse_xmp, build_cube, encode_zlib_base85, parse_cube,
#  interpolate_3d, build_xmp 等函数，保持不变]

TRANSLATIONS = {
    "en": {
        "title": "CINELUT Studio",
        "subtitle": "Professional Color Grading Tool",
        "tab_convert": "CONVERT",
        "tab_presets": "PRESETS",
        "tab_history": "HISTORY",
        "drop_hint": "DROP CUBE FILE HERE",
        "drop_hint_active": "RELEASE TO CONVERT",
        "or_click": "or click to browse",
        "output_settings": "Output Settings",
        "output_format": "Format",
        "quality": "Quality",
        "output_path": "Output Path",
        "color_preview": "Color Preview",
        "original": "Original",
        "processed": "Processed",
        "convert_btn": "CONVERT TO XMP",
        "export_btn": "EXPORT",
        "cancel_btn": "CANCEL",
        "status_ready": "Ready",
        "status_processing": "Processing...",
        "status_complete": "Conversion Complete",
        "status_error": "Error",
        "history_empty": "No conversion history",
        "preset_name": "Preset Name",
        "apply_preset": "APPLY",
        "settings": "Settings",
        "theme": "Theme",
        "language": "Language",
        "about": "About",
        "version": "Version 2.0",
    },
    "zh": {
        "title": "CINELUT Studio",
        "subtitle": "专业调色工具",
        "tab_convert": "转换",
        "tab_presets": "预设",
        "tab_history": "历史",
        "drop_hint": "拖放 CUBE 文件到此处",
        "drop_hint_active": "释放以开始转换",
        "or_click": "或点击浏览文件",
        "output_settings": "输出设置",
        "output_format": "格式",
        "quality": "质量",
        "output_path": "输出路径",
        "color_preview": "色彩预览",
        "original": "原始",
        "processed": "处理后",
        "convert_btn": "转换为 XMP",
        "export_btn": "导出",
        "cancel_btn": "取消",
        "status_ready": "就绪",
        "status_processing": "处理中...",
        "status_complete": "转换完成",
        "status_error": "错误",
        "history_empty": "暂无转换历史",
        "preset_name": "预设名称",
        "apply_preset": "应用",
        "settings": "设置",
        "theme": "主题",
        "language": "语言",
        "about": "关于",
        "version": "版本 2.0",
    }
}

class HistoryItem:
    """历史记录项"""
    def __init__(self, filename, timestamp, status, output_path=None):
        self.filename = filename
        self.timestamp = timestamp
        self.status = status
        self.output_path = output_path

class ModernDropZone(ctk.CTkFrame):
    """现代化拖放区域"""
    def __init__(self, master, on_drop_callback, **kwargs):
        super().__init__(master, **kwargs)

        self.on_drop_callback = on_drop_callback
        self.is_dragging = False

        # 配置样式
        self.configure(
            fg_color=COLORS["drop_zone"],
            corner_radius=16,
            border_width=2,
            border_color=COLORS["border"]
        )

        # 内部布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 图标和文字容器
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # 文件图标
        self.icon_label = ctk.CTkLabel(
            self.content_frame,
            text="📁",
            font=("SF Pro Display", 64)
        )
        self.icon_label.grid(row=0, column=0, pady=(20, 15))

        # 主提示文字
        self.hint_label = ctk.CTkLabel(
            self.content_frame,
            text="拖放 CUBE 文件到此处",
            font=("SF Pro Display", 20, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.hint_label.grid(row=1, column=0, pady=(0, 8))

        # 副提示文字
        self.sub_hint_label = ctk.CTkLabel(
            self.content_frame,
            text="或点击浏览文件",
            font=("SF Pro Display", 14),
            text_color=COLORS["text_secondary"]
        )
        self.sub_hint_label.grid(row=2, column=0, pady=(0, 20))

        # 浏览按钮
        self.browse_btn = ctk.CTkButton(
            self.content_frame,
            text="选择文件",
            width=140,
            height=36,
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=("SF Pro Display", 13),
            command=self.browse_file
        )
        self.browse_btn.grid(row=3, column=0)

        # 绑定拖放事件
        self.bind_drag_events()

    def bind_drag_events(self):
        """绑定拖放事件"""
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, event):
        self.configure(border_color=COLORS["info"])
        self.is_dragging = True
        self.hint_label.configure(text="释放以开始转换")

    def on_leave(self, event):
        self.configure(border_color=COLORS["border"])
        self.is_dragging = False
        self.hint_label.configure(text="拖放 CUBE 文件到此处")

    def browse_file(self):
        """浏览文件"""
        file_path = filedialog.askopenfilename(
            filetypes=[("CUBE files", "*.cube"), ("All files", "*.*")]
        )
        if file_path:
            self.on_drop_callback(file_path)

class ColorPreviewPanel(ctk.CTkFrame):
    """色彩预览面板"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.configure(
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )

        # 标题
        self.title_label = ctk.CTkLabel(
            self,
            text="色彩预览",
            font=("SF Pro Display", 14, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(pady=(16, 12), padx=16, anchor="w")

        # 预览容器
        self.preview_container = ctk.CTkFrame(self, fg_color="transparent")
        self.preview_container.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # 原始颜色
        self.original_frame = ctk.CTkFrame(
            self.preview_container,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=8
        )
        self.original_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            self.original_frame,
            text="原始",
            font=("SF Pro Display", 11),
            text_color=COLORS["text_secondary"]
        ).pack(pady=(8, 4))

        self.original_colors = ctk.CTkFrame(self.original_frame, fg_color="transparent")
        self.original_colors.pack(fill="x", padx=8, pady=(0, 8))

        # 处理后颜色
        self.processed_frame = ctk.CTkFrame(
            self.preview_container,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=8
        )
        self.processed_frame.pack(side="right", fill="both", expand=True, padx=(8, 0))

        ctk.CTkLabel(
            self.processed_frame,
            text="处理后",
            font=("SF Pro Display", 11),
            text_color=COLORS["text_secondary"]
        ).pack(pady=(8, 4))

        self.processed_colors = ctk.CTkFrame(self.processed_frame, fg_color="transparent")
        self.processed_colors.pack(fill="x", padx=8, pady=(0, 8))

        # 初始化颜色方块
        self.color_squares_original = []
        self.color_squares_processed = []
        self.init_color_squares()

    def init_color_squares(self):
        """初始化颜色方块"""
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]

        for i, color in enumerate(colors):
            # 原始颜色方块
            square_orig = ctk.CTkFrame(
                self.original_colors,
                width=40,
                height=40,
                fg_color=color,
                corner_radius=4
            )
            square_orig.grid(row=0, column=i, padx=4, pady=4)
            self.color_squares_original.append(square_orig)

            # 处理后颜色方块
            square_proc = ctk.CTkFrame(
                self.processed_colors,
                width=40,
                height=40,
                fg_color=color,
                corner_radius=4
            )
            square_proc.grid(row=0, column=i, padx=4, pady=4)
            self.color_squares_processed.append(square_proc)

    def update_colors(self, processed_colors):
        """更新处理后的颜色"""
        for square, color in zip(self.color_squares_processed, processed_colors):
            square.configure(fg_color=color)

class OutputSettingsPanel(ctk.CTkFrame):
    """输出设置面板"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.configure(
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )

        # 标题
        self.title_label = ctk.CTkLabel(
            self,
            text="输出设置",
            font=("SF Pro Display", 14, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(pady=(16, 12), padx=16, anchor="w")

        # 设置内容
        self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.settings_frame.pack(fill="x", padx=16, pady=(0, 16))

        # 格式选择
        self.format_label = ctk.CTkLabel(
            self.settings_frame,
            text="输出格式",
            font=("SF Pro Display", 12),
            text_color=COLORS["text_secondary"]
        )
        self.format_label.pack(anchor="w", pady=(0, 6))

        self.format_var = tk.StringVar(value="xmp")
        self.format_menu = ctk.CTkSegmentedButton(
            self.settings_frame,
            values=["XMP", "CUBE"],
            variable=self.format_var,
            font=("SF Pro Display", 12),
            fg_color=COLORS["bg_tertiary"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_tertiary"],
            unselected_hover_color=COLORS["accent"]
        )
        self.format_menu.pack(fill="x", pady=(0, 12))

        # 质量设置
        self.quality_label = ctk.CTkLabel(
            self.settings_frame,
            text="质量",
            font=("SF Pro Display", 12),
            text_color=COLORS["text_secondary"]
        )
        self.quality_label.pack(anchor="w", pady=(0, 6))

        self.quality_slider = ctk.CTkSlider(
            self.settings_frame,
            from_=0,
            to=100,
            number_of_steps=10,
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["accent"],
            button_color=COLORS["text_primary"],
            button_hover_color=COLORS["accent_hover"]
        )
        self.quality_slider.pack(fill="x", pady=(0, 12))
        self.quality_slider.set(80)

        # 质量数值显示
        self.quality_value_label = ctk.CTkLabel(
            self.settings_frame,
            text="80%",
            font=("SF Pro Display", 12, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.quality_value_label.pack(anchor="e", pady=(0, 12))

        # 输出路径
        self.path_label = ctk.CTkLabel(
            self.settings_frame,
            text="输出路径",
            font=("SF Pro Display", 12),
            text_color=COLORS["text_secondary"]
        )
        self.path_label.pack(anchor="w", pady=(0, 6))

        self.path_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.path_frame.pack(fill="x")

        self.path_entry = ctk.CTkEntry(
            self.path_frame,
            placeholder_text="选择输出目录...",
            font=("SF Pro Display", 12),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"]
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.browse_btn = ctk.CTkButton(
            self.path_frame,
            text="浏览",
            width=60,
            height=32,
            corner_radius=6,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=("SF Pro Display", 12),
            command=self.browse_output_path
        )
        self.browse_btn.pack(side="right")

    def browse_output_path(self):
        """浏览输出路径"""
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, path)

class HistoryPanel(ctk.CTkFrame):
    """历史记录面板"""
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.configure(
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"]
        )

        # 标题
        self.title_label = ctk.CTkLabel(
            self,
            text="转换历史",
            font=("SF Pro Display", 14, "bold"),
            text_color=COLORS["text_primary"]
        )
        self.title_label.pack(pady=(16, 12), padx=16, anchor="w")

        # 历史列表容器
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=COLORS["accent"],
            scrollbar_button_hover_color=COLORS["accent_hover"]
        )
        self.list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # 空状态提示
        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="暂无转换历史",
            font=("SF Pro Display", 12),
            text_color=COLORS["text_muted"]
        )
        self.empty_label.pack(pady=40)

        self.history_items = []

    def add_item(self, filename, status, output_path=None):
        """添加历史记录项"""
        # 隐藏空状态提示
        self.empty_label.pack_forget()

        # 创建新项目
        item_frame = ctk.CTkFrame(
            self.list_frame,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=8
        )
        item_frame.pack(fill="x", pady=4)

        # 文件名
        filename_label = ctk.CTkLabel(
            item_frame,
            text=filename,
            font=("SF Pro Display", 12, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        filename_label.pack(fill="x", padx=12, pady=(8, 4))

        # 状态和时间
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.pack(fill="x", padx=12, pady=(0, 8))

        # 状态指示
        status_color = COLORS["success"] if status == "完成" else COLORS["error"]
        status_dot = ctk.CTkLabel(
            info_frame,
            text="●",
            font=("SF Pro Display", 8),
            text_color=status_color
        )
        status_dot.pack(side="left", padx=(0, 6))

        status_label = ctk.CTkLabel(
            info_frame,
            text=status,
            font=("SF Pro Display", 11),
            text_color=COLORS["text_secondary"]
        )
        status_label.pack(side="left")

        # 时间戳
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = ctk.CTkLabel(
            info_frame,
            text=timestamp,
            font=("SF Pro Display", 11),
            text_color=COLORS["text_muted"]
        )
        time_label.pack(side="right")

        self.history_items.append(item_frame)

class App(ctk.CTk, TkinterDnD.Tk):
    def __init__(self):
        super().__init__()

        self.lang = "zh"
        self.cancel_event = threading.Event()

        # 窗口配置
        self.title("CINELUT Studio")
        self.geometry("1200x800")
        self.minsize(1000, 700)

        # 设置深色背景
        self.configure(fg_color=COLORS["bg_primary"])

        # 启用拖放
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)

        # 创建主布局
        self.create_layout()

        # 初始化状态
        self.update_status("就绪")

    def create_layout(self):
        """创建主布局"""
        # 主容器
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # 顶部导航栏
        self.create_navbar()

        # 内容区域（三栏布局）
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, pady=(20, 0))
        self.content_frame.grid_columnconfigure(0, weight=1)  # 左侧
        self.content_frame.grid_columnconfigure(1, weight=2)  # 中间
        self.content_frame.grid_columnconfigure(2, weight=1)  # 右侧
        self.content_frame.grid_rowconfigure(0, weight=1)

        # 左侧面板（文件管理）
        self.left_panel = self.create_left_panel()
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 中间面板（预览和转换）
        self.center_panel = self.create_center_panel()
        self.center_panel.grid(row=0, column=1, sticky="nsew", padx=10)

        # 右侧面板（设置和历史）
        self.right_panel = self.create_right_panel()
        self.right_panel.grid(row=0, column=2, sticky="nsew", padx=(10, 0))

        # 底部状态栏
        self.create_statusbar()

    def create_navbar(self):
        """创建顶部导航栏"""
        navbar = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12,
            height=60
        )
        navbar.pack(fill="x")

        # Logo 和标题
        logo_frame = ctk.CTkFrame(navbar, fg_color="transparent")
        logo_frame.pack(side="left", padx=20, pady=12)

        ctk.CTkLabel(
            logo_frame,
            text="CINELUT",
            font=("SF Pro Display", 20, "bold"),
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        ctk.CTkLabel(
            logo_frame,
            text="Studio",
            font=("SF Pro Display", 20),
            text_color=COLORS["text_secondary"]
        ).pack(side="left", padx=(4, 0))

        # 版本标签
        version_label = ctk.CTkLabel(
            logo_frame,
            text="v2.0",
            font=("SF Pro Display", 10),
            text_color=COLORS["text_muted"]
        )
        version_label.pack(side="left", padx=(8, 0), pady=(6, 0))

        # 右侧控件
        controls_frame = ctk.CTkFrame(navbar, fg_color="transparent")
        controls_frame.pack(side="right", padx=20, pady=12)

        # 语言切换
        self.lang_menu = ctk.CTkSegmentedButton(
            controls_frame,
            values=["中文", "EN"],
            width=100,
            font=("SF Pro Display", 12),
            fg_color=COLORS["bg_tertiary"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_tertiary"],
            unselected_hover_color=COLORS["accent"],
            command=self.change_language
        )
        self.lang_menu.pack(side="right", padx=(10, 0))
        self.lang_menu.set("中文")

        # 主题切换
        self.theme_menu = ctk.CTkSegmentedButton(
            controls_frame,
            values=["Dark", "Light", "System"],
            width=150,
            font=("SF Pro Display", 12),
            fg_color=COLORS["bg_tertiary"],
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent_hover"],
            unselected_color=COLORS["bg_tertiary"],
            unselected_hover_color=COLORS["accent"],
            command=self.change_theme
        )
        self.theme_menu.pack(side="right")
        self.theme_menu.set("Dark")

    def create_left_panel(self):
        """创建左侧面板"""
        panel = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12
        )

        # 标签页
        self.left_tabview = ctk.CTkTabview(
            panel,
            fg_color=COLORS["bg_secondary"],
            segmented_button_fg_color=COLORS["bg_tertiary"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["bg_tertiary"],
            segmented_button_unselected_hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"]
        )
        self.left_tabview.pack(fill="both", expand=True, padx=12, pady=12)

        # 添加标签页
        self.left_tabview.add("文件")
        self.left_tabview.add("预设")

        # 文件标签页内容
        self.create_file_tab()

        # 预设标签页内容
        self.create_presets_tab()

        return panel

    def create_file_tab(self):
        """创建文件标签页"""
        tab = self.left_tabview.tab("文件")

        # 拖放区域
        self.drop_zone = ModernDropZone(
            tab,
            on_drop_callback=self.handle_file_drop,
            height=200
        )
        self.drop_zone.pack(fill="x", pady=(0, 12))

        # 最近文件
        recent_label = ctk.CTkLabel(
            tab,
            text="最近文件",
            font=("SF Pro Display", 12, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        recent_label.pack(fill="x", pady=(0, 8))

        # 最近文件列表
        self.recent_frame = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent"
        )
        self.recent_frame.pack(fill="both", expand=True)

        # 添加示例最近文件
        self.add_recent_file("example.cube", "2 分钟前")
        self.add_recent_file("wedding.cube", "1 小时前")
        self.add_recent_file("cinema.cube", "昨天")

    def add_recent_file(self, filename, time_str):
        """添加最近文件项"""
        item = ctk.CTkFrame(
            self.recent_frame,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=8
        )
        item.pack(fill="x", pady=4)

        # 文件图标
        icon_label = ctk.CTkLabel(
            item,
            text="📄",
            font=("SF Pro Display", 16)
        )
        icon_label.pack(side="left", padx=12, pady=8)

        # 文件信息
        info_frame = ctk.CTkFrame(item, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, pady=8)

        filename_label = ctk.CTkLabel(
            info_frame,
            text=filename,
            font=("SF Pro Display", 12, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        filename_label.pack(fill="x")

        time_label = ctk.CTkLabel(
            info_frame,
            text=time_str,
            font=("SF Pro Display", 10),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        time_label.pack(fill="x")

    def create_presets_tab(self):
        """创建预设标签页"""
        tab = self.left_tabview.tab("预设")

        # 预设列表
        self.presets_frame = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent"
        )
        self.presets_frame.pack(fill="both", expand=True)

        # 添加内置预设
        presets = [
            ("Fuji Provia", "经典富士色彩"),
            ("Fuji Velvia", "鲜艳风景"),
            ("Classic Chrome", "复古胶片"),
            ("Classic Negative", "电影负片"),
            ("Astia Soft", "柔和人像"),
            ("Monochrome", "黑白胶片"),
        ]

        for name, desc in presets:
            self.add_preset_item(name, desc)

    def add_preset_item(self, name, description):
        """添加预设项"""
        item = ctk.CTkFrame(
            self.presets_frame,
            fg_color=COLORS["bg_tertiary"],
            corner_radius=8
        )
        item.pack(fill="x", pady=4)

        # 预设信息
        info_frame = ctk.CTkFrame(item, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        name_label = ctk.CTkLabel(
            info_frame,
            text=name,
            font=("SF Pro Display", 12, "bold"),
            text_color=COLORS["text_primary"],
            anchor="w"
        )
        name_label.pack(fill="x")

        desc_label = ctk.CTkLabel(
            info_frame,
            text=description,
            font=("SF Pro Display", 10),
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        desc_label.pack(fill="x")

        # 应用按钮
        apply_btn = ctk.CTkButton(
            item,
            text="应用",
            width=50,
            height=28,
            corner_radius=6,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=("SF Pro Display", 11),
            command=lambda: self.apply_preset(name)
        )
        apply_btn.pack(side="right", padx=12, pady=8)

    def create_center_panel(self):
        """创建中间面板"""
        panel = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12
        )

        # 色彩预览
        self.color_preview = ColorPreviewPanel(panel)
        self.color_preview.pack(fill="x", padx=12, pady=12)

        # 转换按钮
        btn_frame = ctk.CTkFrame(panel, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.convert_btn = ctk.CTkButton(
            btn_frame,
            text="转换为 XMP",
            height=44,
            corner_radius=8,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=("SF Pro Display", 14, "bold"),
            command=self.start_conversion
        )
        self.convert_btn.pack(fill="x")

        # 进度条
        self.progress_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_frame,
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["accent"],
            height=4
        )
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=("SF Pro Display", 11),
            text_color=COLORS["text_secondary"]
        )
        self.progress_label.pack(pady=(4, 0))

        return panel

    def create_right_panel(self):
        """创建右侧面板"""
        panel = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS["bg_secondary"],
            corner_radius=12
        )

        # 标签页
        self.right_tabview = ctk.CTkTabview(
            panel,
            fg_color=COLORS["bg_secondary"],
            segmented_button_fg_color=COLORS["bg_tertiary"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_color=COLORS["bg_tertiary"],
            segmented_button_unselected_hover_color=COLORS["accent"],
            text_color=COLORS["text_primary"]
        )
        self.right_tabview.pack(fill="both", expand=True, padx=12, pady=12)

        # 添加标签页
        self.right_tabview.add("设置")
        self.right_tabview.add("历史")

        # 设置标签页
        self.output_settings = OutputSettingsPanel(
            self.right_tabview.tab("设置")
        )
        self.output_settings.pack(fill="both", expand=True)

        # 历史标签页
        self.history_panel = HistoryPanel(
            self.right_tabview.tab("历史")
        )
        self.history_panel.pack(fill="both", expand=True)

        return panel

    def create_statusbar(self):
        """创建底部状态栏"""
        statusbar = ctk.CTkFrame(
            self.main_container,
            fg_color=COLORS["bg_secondary"],
            corner_radius=8,
            height=40
        )
        statusbar.pack(fill="x", pady=(20, 0))

        # 状态文字
        self.status_label = ctk.CTkLabel(
            statusbar,
            text="就绪",
            font=("SF Pro Display", 12),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", padx=16, pady=8)

        # 文件信息
        self.file_info_label = ctk.CTkLabel(
            statusbar,
            text="",
            font=("SF Pro Display", 11),
            text_color=COLORS["text_muted"]
        )
        self.file_info_label.pack(side="right", padx=16, pady=8)

    def tr(self, key):
        """翻译"""
        return TRANSLATIONS[self.lang].get(key, key)

    def update_status(self, status):
        """更新状态"""
        self.status_label.configure(text=status)

    def change_language(self, choice):
        """切换语言"""
        self.lang = "zh" if choice == "中文" else "en"
        # 更新UI文本
        # 这里可以添加更多UI更新逻辑

    def change_theme(self, choice):
        """切换主题"""
        if choice == "Dark":
            ctk.set_appearance_mode("dark")
        elif choice == "Light":
            ctk.set_appearance_mode("light")
        else:
            ctk.set_appearance_mode("system")

    def handle_drop(self, event):
        """处理拖放"""
        file_path = event.data.strip('{}')
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.cube', '.xmp']:
                self.handle_file_drop(file_path)

    def handle_file_drop(self, file_path):
        """处理文件拖放"""
        self.update_status(f"正在处理: {os.path.basename(file_path)}")
        # 这里添加实际的转换逻辑

    def apply_preset(self, preset_name):
        """应用预设"""
        self.update_status(f"应用预设: {preset_name}")
        # 这里添加预设应用逻辑

    def start_conversion(self):
        """开始转换"""
        self.update_status("正在转换...")
        # 这里添加转换逻辑

if __name__ == "__main__":
    app = App()
    app.mainloop()
