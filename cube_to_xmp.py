import os
import re
import struct
import zlib
import hashlib
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Configure global customtkinter settings
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("dark-blue")  # We'll switch away from standard blue, "dark-blue" is more muted, or we can use custom colors in widgets

kEncodeTable = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-:+=^!/*?`'|()[]{}@%$#"

def parse_xmp(file_path):
    import xml.etree.ElementTree as ET
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Extract title
    title = "Extracted_LUT"
    title_match = re.search(r'<crs:Name>\s*<rdf:Alt>\s*<rdf:li xml:lang="x-default">(.*?)</rdf:li>', content, re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()
        
    # Find the table block
    table_match = re.search(r'crs:Table_[A-F0-9]+="([^"]+)"', content)
    if not table_match:
        raise ValueError("Valid RGBTable data not found in XMP.")
        
    encoded_str = table_match.group(1)
    
    # Decode Base85
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
            
    # Handle remainder if any (though usually padded)
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
        # Some padding issues might occur, try to decompress with larger buffer or ignore trailing garbage
        block_data = zlib.decompress(z_data, bufsize=uncompressed_size)
        
    if len(block_data) != uncompressed_size:
        pass # Not critical if it decompressed
        
    # Parse header
    # header[4] = { version, version, dimensions, size }
    if len(block_data) < 16:
        raise ValueError("Invalid uncompressed data block")
        
    h_v1, h_v2, dims, size = struct.unpack('<4I', block_data[:16])
    
    if dims != 3:
        raise ValueError(f"Only 3D LUTs are supported (found {dims}D)")
        
    nopValue = [(i * 0xFFFF + (size // 2)) // (size - 1) for i in range(size)]
    
    samples = []
    
    # Read samples
    # CUBE format requires: r changes fastest, then g, then b
    # XMP packed it as: b changes fastest, then g, then r
    
    # We will read it into a 3D array first
    # [r][g][b]
    lut_3d = [[[ (0,0,0) for _ in range(size)] for _ in range(size)] for _ in range(size)]
    
    offset = 16
    for b in range(size):
        for g in range(size):
            for r in range(size):
                if offset + 6 > len(block_data):
                    break
                temp_r, temp_g, temp_b = struct.unpack('<HHH', block_data[offset:offset+6])
                offset += 6
                
                # Reverse the nopValue adjustment
                r_val = (temp_r + nopValue[r]) / 65535.0
                g_val = (temp_g + nopValue[g]) / 65535.0
                b_val = (temp_b + nopValue[b]) / 65535.0
                
                lut_3d[r][g][b] = (r_val, g_val, b_val)
                
    # Flatten it in CUBE order: R fast, G, B slow
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
                # assume it's data
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
    
    # Pack the binary block
    # header[4] = { 1,1,3,size }
    block_data = bytearray()
    block_data.extend(struct.pack('<4I', 1, 1, 3, size))
    
    # samples (bIndex fast, gIndex, rIndex slow)
    # The input `samples` from CUBE is usually rIndex fast? 
    # Wait, CUBE standard: R changes fastest, then G, then B.
    # So the order in the list `samples` is:
    # index = r + g*size + b*size*size
    # In C++, the loop is:
    # bIndex, gIndex, rIndex
    # j is the index in samples (r changes fastest)
    # idx = 16 + (rIndex * size * size + gIndex * size + bIndex) * 3 * 2;
    # So the output block wants:
    # bIndex fastest, gIndex, rIndex slowest.
    
    # Let's create an empty array of the right size
    sample_bytes = bytearray(size * size * size * 6)
    
    for b in range(size):
        for g in range(size):
            for r in range(size):
                cube_idx = r + g * size + b * size * size
                r_val, g_val, b_val = samples[cube_idx]
                
                # output idx where b changes fastest, then g, then r
                out_idx = (r * size * size + g * size + b) * 6
                
                # int_round(val * 65535) - nopValue
                temp_r = (int(round(r_val * 65535)) - nopValue[r]) & 0xFFFF
                temp_g = (int(round(g_val * 65535)) - nopValue[g]) & 0xFFFF
                temp_b = (int(round(b_val * 65535)) - nopValue[b]) & 0xFFFF
                
                struct.pack_into('<HHH', sample_bytes, out_idx, temp_r, temp_g, temp_b)
                
    block_data.extend(sample_bytes)
    
    # footer[3] = { colors, gamma, gamut }
    # sRGB = 0, 1, 0
    block_data.extend(struct.pack('<3I', 0, 1, 0))
    
    # range[2] = { min, max }
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

# ... (Keep existing parser and encoder code above) ...

TRANSLATIONS = {
    "en": {
        "title": "LUT to XMP Converter",
        "tab_custom": "Custom .cube",
        "tab_presets": "Film Presets",
        "custom_desc": "Convert your custom .cube LUT files to Adobe Camera Raw (.xmp) profiles.",
        "btn_select": "Select File & Convert",
        "preset_desc": "Export built-in film style LUTs (Fuji/NC) to XMP profiles.",
        "btn_export": "Export Selected Preset",
        "no_presets": "No presets found. Please run generate_fuji_luts.py first.",
        "ready": "Ready",
        "parsing": "Parsing CUBE file...",
        "building": "Building XMP profile (this might take a moment if resampling)...",
        "success": "Success: Saved to {filename}",
        "cancelled": "Cancelled",
        "error": "Error occurred",
        "theme": "Theme",
        "language": "Language",
        "warn_no_preset": "No preset selected!",
        "btn_convert_xmp_to_cube": "Convert XMP to .cube"
    },
    "zh": {
        "title": "LUT / XMP 转换器",
        "tab_custom": "双向转换",
        "tab_presets": "内置胶片预设",
        "custom_desc": "在 .cube (LUT) 和 .xmp (Adobe 配置) 之间进行双向转换。\n选择文件后程序会自动识别格式。",
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
        "btn_convert_xmp_to_cube": "XMP 转 .cube"
    }
}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.lang = "zh"  # Default language
        
        self.title(self.tr("title"))
        self.geometry("600x400")
        self.minsize(500, 350)  # Make it resizable with a minimum size
        
        # Main layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)
        
        # Header / Top bar
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)
        
        self.title_lbl = ctk.CTkLabel(self.header_frame, text=self.tr("title"), font=ctk.CTkFont(size=24, weight="bold"))
        self.title_lbl.grid(row=0, column=0, sticky="w")
        
        # Settings (Language & Theme)
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
        self.tabview.tab(self.tab_1_name).grid_rowconfigure(1, weight=1)
        
        self.lbl_custom = ctk.CTkLabel(self.tabview.tab(self.tab_1_name), text=self.tr("custom_desc"), font=ctk.CTkFont(size=14))
        self.lbl_custom.grid(row=0, column=0, pady=(30, 20))
        
        # UI Button Tweaks (avoiding bright blue)
        btn_color = ("#4A4A4A", "#333333")
        btn_hover_color = ("#5A5A5A", "#444444")
        
        self.btn_convert = ctk.CTkButton(self.tabview.tab(self.tab_1_name), text=self.tr("btn_select"), height=40, font=ctk.CTkFont(size=14, weight="bold"), 
                                         fg_color=btn_color, hover_color=btn_hover_color, command=self.convert)
        self.btn_convert.grid(row=1, column=0, pady=10)
        
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
        
        # Rename tabs
        old_tab1, old_tab2 = self.tab_1_name, self.tab_2_name
        self.tab_1_name = self.tr("tab_custom")
        self.tab_2_name = self.tr("tab_presets")
        
        self.lbl_custom.configure(text=self.tr("custom_desc"))
        self.btn_convert.configure(text=self.tr("btn_select"))
        self.lbl_preset.configure(text=self.tr("preset_desc"))
        
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

    def set_status(self, msg_key, **kwargs):
        msg = self.tr(msg_key)
        if kwargs:
            msg = msg.format(**kwargs)
        self.status_var.set(msg)
        self.update()

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
            # 如果内置预设已经是 xmp，我们可以选择直接让用户另存为 xmp，或者提供转换为 cube 的选项
            # 既然叫导出预设，通常用户希望得到最终的 xmp 或 cube。我们弹出一个对话框让用户选择要保存为什么格式。
            # 为了简单起见，如果内置是 xmp，我们将其转换为 cube（如果用户需要的话），或者直接另存。
            # 这里统一按照双向转换逻辑处理：如果选了 xmp，默认转成 cube；如果选了 cube，默认转成 xmp。
            # 也可以直接调用 _process_xmp_to_cube
            self._process_xmp_to_cube(file_path)
        
    def _process_cube_to_xmp(self, file_path, is_preset=False):
        try:
            self.set_status("parsing")
            title, size, samples = parse_cube(file_path)
            
            self.set_status("building")
            xmp_content = build_xmp(title, size, samples)
            
            default_name = title.replace(" ", "_") + ".xmp" if is_preset else os.path.basename(file_path).replace(".cube", ".xmp")
            
            out_path = filedialog.asksaveasfilename(
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
            self.set_status("error")
            messagebox.showerror("Error", str(e))

    def _process_xmp_to_cube(self, file_path):
        try:
            self.set_status("parsing")
            title, size, samples = parse_xmp(file_path)
            
            self.set_status("building")
            cube_content = build_cube(title, size, samples)
            
            out_path = filedialog.asksaveasfilename(
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
            self.set_status("error")
            messagebox.showerror("Error", f"Failed to convert XMP to CUBE:\n{str(e)}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
