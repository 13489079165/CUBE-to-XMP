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

# Configure global customtkinter settings
ctk.set_appearance_mode("System")
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
    "en": {
        "title": "LUT to XMP Converter",
        "tab_custom": "Custom .cube",
        "tab_presets": "Film Presets",
        "custom_desc": "Convert your custom .cube LUT files to Adobe Camera Raw (.xmp) profiles.\nDrag and drop files here or click the button below.",
        "btn_select": "Select File & Convert",
        "preset_desc": "Export built-in film style LUTs (Fuji/NC) to XMP profiles.",
        "btn_export": "Export Selected Preset",
        "no_presets": "No presets found. Please run generate_fuji_luts.py first.",
        "ready": "Ready",
        "parsing": "Parsing file...",
        "building": "Building profile (this might take a moment if resampling)...",
        "success": "Success: Saved to {filename}",
        "cancelled": "Cancelled",
        "error": "Error occurred",
        "theme": "Theme",
        "language": "Language",
        "warn_no_preset": "No preset selected!",
        "btn_convert_xmp_to_cube": "Convert XMP to .cube",
        "dialog_save_xmp": "Save XMP File",
        "dialog_save_cube": "Save CUBE File",
        "processing": "Processing...",
        "cancel": "Cancel",
        "preview_title": "Color Preview",
        "before": "Original",
        "after": "With LUT"
    },
    "zh": {
        "title": "LUT / XMP 转换器",
        "tab_custom": "双向转换",
        "tab_presets": "内置胶片预设",
        "custom_desc": "在 .cube (LUT) 和 .xmp (Adobe 配置) 之间进行双向转换。\n拖放文件到此处或点击下方按钮。",
        "btn_select": "选择文件并转换",
        "preset_desc": "导出内置的胶片风格 LUT（富士/NC滤镜）为 XMP 配置文件。",
        "btn_export": "导出所选预设",
        "no_presets": "未找到预设。请先运行 generate_fuji_luts.py。",
        "ready": "就绪",
        "parsing": "正在解析文件...",
        "building": "正在构建配置文件...",
        "success": "成功：已保存至 {filename}",
        "cancelled": "已取消",
        "error": "发生错误",
        "theme": "外观",
        "language": "语言",
        "warn_no_preset": "未选择预设！",
        "btn_convert_xmp_to_cube": "XMP 转 .cube",
        "dialog_save_xmp": "保存 XMP 文件",
        "dialog_save_cube": "保存 CUBE 文件",
        "processing": "处理中...",
        "cancel": "取消",
        "preview_title": "颜色预览",
        "before": "原始",
        "after": "应用 LUT"
    }
}

class ProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, lang="en"):
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.progress_var = tk.DoubleVar(value=0)
        self.cancelled = False
        self.geometry("350x150")
        self.grid_columnconfigure(0, weight=1)
        self.message_label = ctk.CTkLabel(self, text=message, wraplength=300)
        self.message_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.progress_bar = ctk.CTkProgressBar(self, variable=self.progress_var)
        self.progress_bar.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        cancel_text = "Cancel" if lang == "en" else "取消"
        self.cancel_btn = ctk.CTkButton(self, text=cancel_text, fg_color="red",
                                        hover_color="darkred", command=self.cancel)
        self.cancel_btn.grid(row=2, column=0, pady=10)

    def cancel(self):
        self.cancelled = True
        self.progress_bar.configure(mode="indeterminate")

    def update_progress(self, value):
        self.progress_var.set(value)

    def update_message(self, message):
        self.message_label.configure(text=message)

    def close(self):
        self.grab_release()
        self.destroy()

class App(ctk.CTk, TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.lang = "zh"
        self.cancel_event = threading.Event()
        self.title(self.tr("title"))
        self.geometry("800x500")
        self.minsize(600, 400)
        
        # Enable drag and drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_drop)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text=self.tr("title"), font=ctk.CTkFont(size=24, weight="bold"))
        self.title_lbl.grid(row=0, column=0, sticky="w")
        
        # Settings
        self.settings_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.settings_frame.grid(row=0, column=1, sticky="e")
        
        self.lang_switch = ctk.CTkOptionMenu(self.settings_frame, values=["中文", "English"], width=80, command=self.change_language)
        self.lang_switch.set("中文")
        self.lang_switch.pack(side="left", padx=(0, 10))
        
        self.theme_switch = ctk.CTkOptionMenu(self.settings_frame, values=["System", "Dark", "Light"], width=90, command=self.change_theme)
        self.theme_switch.pack(side="left")
        
        # Tab view
        self.tabview = ctk.CTkTabview(self.main_frame, corner_radius=10)
        self.tabview.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        
        self.tab_1_name = self.tr("tab_custom")
        self.tab_2_name = self.tr("tab_presets")
        self.tabview.add(self.tab_1_name)
        self.tabview.add(self.tab_2_name)
        
        # Tab 1: Custom
        self.tabview.tab(self.tab_1_name).grid_columnconfigure(0, weight=1)
        self.tabview.tab(self.tab_1_name).grid_rowconfigure(2, weight=1)
        
        self.lbl_custom = ctk.CTkLabel(self.tabview.tab(self.tab_1_name), text=self.tr("custom_desc"), font=ctk.CTkFont(size=14))
        self.lbl_custom.grid(row=0, column=0, pady=(20, 10))
        
        btn_color = ("#4A4A4A", "#333333")
        btn_hover_color = ("#5A5A5A", "#444444")
        
        self.btn_convert = ctk.CTkButton(self.tabview.tab(self.tab_1_name), text=self.tr("btn_select"), height=40, font=ctk.CTkFont(size=14, weight="bold"), 
                                         fg_color=btn_color, hover_color=btn_hover_color, command=self.convert)
        self.btn_convert.grid(row=1, column=0, pady=10)
        
        # Preview area
        self.preview_frame = ctk.CTkFrame(self.tabview.tab(self.tab_1_name), corner_radius=10)
        self.preview_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.preview_frame.grid_columnconfigure(0, weight=1)
        self.preview_frame.grid_columnconfigure(1, weight=1)
        
        self.lbl_preview_title = ctk.CTkLabel(self.preview_frame, text=self.tr("preview_title"), font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_preview_title.grid(row=0, column=0, columnspan=2, pady=(10, 5))
        
        self.lbl_before = ctk.CTkLabel(self.preview_frame, text=self.tr("before"), font=ctk.CTkFont(size=11))
        self.lbl_before.grid(row=1, column=0, pady=5)
        
        self.lbl_after = ctk.CTkLabel(self.preview_frame, text=self.tr("after"), font=ctk.CTkFont(size=11))
        self.lbl_after.grid(row=1, column=1, pady=5)
        
        self.canvas_before = tk.Canvas(self.preview_frame, width=150, height=100, bg='#808080')
        self.canvas_before.grid(row=2, column=0, padx=10, pady=10)
        
        self.canvas_after = tk.Canvas(self.preview_frame, width=150, height=100, bg='#808080')
        self.canvas_after.grid(row=2, column=1, padx=10, pady=10)
        
        self.draw_color_patches()
        
        # Tab 2: Presets
        self.tabview.tab(self.tab_2_name).grid_columnconfigure(0, weight=1)
        self.tabview.tab(self.tab_2_name).grid_rowconfigure(2, weight=1)
        
        self.lbl_preset = ctk.CTkLabel(self.tabview.tab(self.tab_2_name), text=self.tr("preset_desc"), font=ctk.CTkFont(size=14))
        self.lbl_preset.grid(row=0, column=0, pady=(30, 20))
        
        self.preset_var = tk.StringVar()
        self.presets = []
        if os.path.exists("built_in_luts"):
            self.presets = [f for f in os.listdir("built_in_luts") if f.endswith(".cube") or f.endswith(".xmp")]
            
        if not self.presets:
            self.lbl_no_presets = ctk.CTkLabel(self.tabview.tab(self.tab_2_name), text=self.tr("no_presets"), text_color="red")
            self.lbl_no_presets.grid(row=1, column=0)
        else:
            self.combo_presets = ctk.CTkOptionMenu(self.tabview.tab(self.tab_2_name), variable=self.preset_var, values=self.presets, width=250, height=35,
                                                   fg_color=btn_color, button_color=btn_color, button_hover_color=btn_hover_color)
            self.combo_presets.grid(row=1, column=0, pady=10)
            
            self.btn_export_preset = ctk.CTkButton(self.tabview.tab(self.tab_2_name), text=self.tr("btn_export"), height=40, font=ctk.CTkFont(size=14, weight="bold"), 
                                                   fg_color=btn_color, hover_color=btn_hover_color, command=self.export_preset)
            self.btn_export_preset.grid(row=2, column=0, pady=10)
        
        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set(self.tr("ready"))
        self.status_bar = ctk.CTkLabel(self.main_frame, textvariable=self.status_var, font=ctk.CTkFont(size=12), text_color="gray")
        self.status_bar.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="w")
        
    def tr(self, key):
        return TRANSLATIONS[self.lang].get(key, key)
        
    def update_ui_text(self):
        self.title(self.tr("title"))
        self.title_lbl.configure(text=self.tr("title"))
        self.lbl_custom.configure(text=self.tr("custom_desc"))
        self.btn_convert.configure(text=self.tr("btn_select"))
        self.lbl_preset.configure(text=self.tr("preset_desc"))
        self.lbl_preview_title.configure(text=self.tr("preview_title"))
        self.lbl_before.configure(text=self.tr("before"))
        self.lbl_after.configure(text=self.tr("after"))
        
        if hasattr(self, 'btn_export_preset'):
            self.btn_export_preset.configure(text=self.tr("btn_export"))
        if hasattr(self, 'lbl_no_presets'):
            self.lbl_no_presets.configure(text=self.tr("no_presets"))
            
        if self.status_var.get() in [TRANSLATIONS["en"]["ready"], TRANSLATIONS["zh"]["ready"]]:
            self.status_var.set(self.tr("ready"))

    def change_language(self, choice):
        self.lang = "zh" if choice == "中文" else "en"
        self.update_ui_text()
        
    def change_theme(self, choice):
        ctk.set_appearance_mode(choice)

    def draw_color_patches(self):
        self.canvas_before.delete('all')
        colors = [
            ('#FF0000', 10, 10),
            ('#00FF00', 60, 10),
            ('#0000FF', 110, 10),
            ('#FFFF00', 10, 60),
            ('#FF00FF', 60, 60),
            ('#00FFFF', 110, 60),
        ]
        for color, x, y in colors:
            self.canvas_before.create_rectangle(x, y, x+40, y+40, fill=color, outline='')
        self.canvas_after.delete('all')
        for color, x, y in colors:
            self.canvas_after.create_rectangle(x, y, x+40, y+40, fill=color, outline='')

    def apply_lut_to_color(self, r, g, b, samples, size):
        r_idx = r * (size - 1)
        g_idx = g * (size - 1)
        b_idx = b * (size - 1)
        r0, g0, b0 = int(r_idx), int(g_idx), int(b_idx)
        r1, g1, b1 = min(r0 + 1, size - 1), min(g0 + 1, size - 1), min(b0 + 1, size - 1)
        fr, fg, fb = r_idx - r0, g_idx - g0, b_idx - b0
        
        def get_sample(ri, gi, bi):
            idx = ri + gi * size + bi * size * size
            if idx < len(samples):
                return samples[idx]
            return (0.0, 0.0, 0.0)
        
        c000 = get_sample(r0, g0, b0)
        c100 = get_sample(r1, g0, b0)
        c010 = get_sample(r0, g1, b0)
        c110 = get_sample(r1, g1, b0)
        c001 = get_sample(r0, g0, b1)
        c101 = get_sample(r1, g0, b1)
        c011 = get_sample(r0, g1, b1)
        c111 = get_sample(r1, g1, b1)
        
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
        return result

    def update_preview(self, samples, size):
        colors = [
            ((1.0, 0.0, 0.0), 10, 10),
            ((0.0, 1.0, 0.0), 60, 10),
            ((0.0, 0.0, 1.0), 110, 10),
            ((1.0, 1.0, 0.0), 10, 60),
            ((1.0, 0.0, 1.0), 60, 60),
            ((0.0, 1.0, 1.0), 110, 60),
        ]
        self.canvas_after.delete('all')
        for (r, g, b), x, y in colors:
            new_r, new_g, new_b = self.apply_lut_to_color(r, g, b, samples, size)
            hex_color = f'#{int(new_r*255):02x}{int(new_g*255):02x}{int(new_b*255):02x}'
            self.canvas_after.create_rectangle(x, y, x+40, y+40, fill=hex_color, outline='')

    def set_status(self, msg_key, **kwargs):
        msg = self.tr(msg_key)
        if kwargs:
            msg = msg.format(**kwargs)
        self.status_var.set(msg)
        self.update()

    def handle_drop(self, event):
        file_path = event.data.strip('{}')
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.cube', '.xmp']:
                self.set_status("parsing")
                if ext == '.cube':
                    self._process_cube_to_xmp(file_path)
                else:
                    self._process_xmp_to_cube(file_path)
            else:
                messagebox.showerror("Error", "Unsupported file format. Please drop .cube or .xmp file.")
        else:
            messagebox.showerror("Error", "Invalid file path.")

    def convert(self):
        file_path = filedialog.askopenfilename(filetypes=[("LUT or XMP files", "*.cube *.xmp"), ("CUBE files", "*.cube"), ("XMP files", "*.xmp")])
        if not file_path:
            return
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.cube':
            self._process_cube_to_xmp(file_path)
        elif ext == '.xmp':
            self._process_xmp_to_cube(file_path)
        else:
            messagebox.showerror("Error", "Unsupported file format. Please select .cube or .xmp file.")
        
    def export_preset(self):
        selected = self.preset_var.get()
        if not selected:
            messagebox.showwarning("Warning", self.tr("warn_no_preset"))
            return
        file_path = os.path.join("built_in_luts", selected)
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.cube':
            self._process_cube_to_xmp(file_path, is_preset=True)
        elif ext == '.xmp':
            self._process_xmp_to_cube(file_path)
        
    def _process_cube_to_xmp(self, file_path, is_preset=False):
        self.cancel_event.clear()
        dialog = ProgressDialog(self, self.tr("processing"), self.tr("parsing"), self.lang)
        def process():
            try:
                title, size, samples = parse_cube(file_path)
                if not samples:
                    raise ValueError("No valid color samples found in CUBE file")
                if dialog.cancelled:
                    self.set_status("cancelled")
                    dialog.close()
                    return
                dialog.update_progress(0.3)
                dialog.update_message(self.tr("building"))
                self.update_preview(samples, size)
                xmp_content = build_xmp(title, size, samples)
                if dialog.cancelled:
                    self.set_status("cancelled")
                    dialog.close()
                    return
                dialog.update_progress(0.7)
                default_name = title.replace(" ", "_") + ".xmp" if is_preset else os.path.basename(file_path).replace(".cube", ".xmp")
                dialog.update_progress(0.9)
                dialog.close()
                out_path = filedialog.asksaveasfilename(
                    title=self.tr("dialog_save_xmp"),
                    defaultextension=".xmp",
                    filetypes=[("XMP files", "*.xmp")],
                    initialfile=default_name
                )
                if out_path:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(xmp_content)
                    self.set_status("success", filename=os.path.basename(out_path))
                    messagebox.showinfo("Success", f"{self.tr('success').format(filename=os.path.basename(out_path))}\n{out_path}")
                else:
                    self.set_status("cancelled")
            except Exception as e:
                dialog.close()
                self.set_status("error")
                messagebox.showerror("Error", f"Failed to convert CUBE to XMP:\n{str(e)}")
        threading.Thread(target=process, daemon=True).start()

    def _process_xmp_to_cube(self, file_path):
        self.cancel_event.clear()
        dialog = ProgressDialog(self, self.tr("processing"), self.tr("parsing"), self.lang)
        def process():
            try:
                title, size, samples = parse_xmp(file_path)
                if not samples:
                    raise ValueError("No valid color samples found in XMP file")
                if dialog.cancelled:
                    self.set_status("cancelled")
                    dialog.close()
                    return
                dialog.update_progress(0.3)
                dialog.update_message(self.tr("building"))
                self.draw_color_patches()
                cube_content = build_cube(title, size, samples)
                if dialog.cancelled:
                    self.set_status("cancelled")
                    dialog.close()
                    return
                dialog.update_progress(0.7)
                dialog.close()
                out_path = filedialog.asksaveasfilename(
                    title=self.tr("dialog_save_cube"),
                    defaultextension=".cube",
                    filetypes=[("CUBE files", "*.cube")],
                    initialfile=os.path.basename(file_path).replace(".xmp", ".cube")
                )
                if out_path:
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(cube_content)
                    self.set_status("success", filename=os.path.basename(out_path))
                    messagebox.showinfo("Success", f"{self.tr('success').format(filename=os.path.basename(out_path))}\n{out_path}")
                else:
                    self.set_status("cancelled")
            except Exception as e:
                dialog.close()
                self.set_status("error")
                messagebox.showerror("Error", f"Failed to convert XMP to CUBE:\n{str(e)}")
        threading.Thread(target=process, daemon=True).start()

if __name__ == "__main__":
    app = App()
    app.mainloop()
