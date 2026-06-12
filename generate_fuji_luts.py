import os
import math

def rgb_to_hsv(r, g, b):
    maxc = max(r, g, b)
    minc = min(r, g, b)
    v = maxc
    if minc == maxc:
        return 0.0, 0.0, v
    s = (maxc-minc) / maxc
    rc = (maxc-r) / (maxc-minc)
    gc = (maxc-g) / (maxc-minc)
    bc = (maxc-b) / (maxc-minc)
    if r == maxc:
        h = bc-gc
    elif g == maxc:
        h = 2.0+rc-bc
    else:
        h = 4.0+gc-rc
    h = (h/6.0) % 1.0
    return h, s, v

def hsv_to_rgb(h, s, v):
    if s == 0.0:
        return v, v, v
    i = int(h*6.0)
    f = (h*6.0) - i
    p = v*(1.0 - s)
    q = v*(1.0 - s*f)
    t = v*(1.0 - s*(1.0-f))
    i %= 6
    if i == 0: return v, t, p
    if i == 1: return q, v, p
    if i == 2: return p, v, t
    if i == 3: return p, q, v
    if i == 4: return t, p, v
    if i == 5: return v, p, q
    return 0,0,0

def s_curve(x, strength=0.2):
    x = max(0.0, min(1.0, x))
    if x < 0.5:
        return 0.5 * math.pow(2*x, 1.0 + strength)
    else:
        return 1.0 - 0.5 * math.pow(2*(1.0-x), 1.0 + strength)

def generate_lut(name, size=16, style='provia'):
    os.makedirs("built_in_luts", exist_ok=True)
    path = f"built_in_luts/{name}.cube"
    with open(path, 'w') as f:
        f.write(f'TITLE "{name}"\n')
        f.write(f'LUT_3D_SIZE {size}\n')
        for b_idx in range(size):
            for g_idx in range(size):
                for r_idx in range(size):
                    r = r_idx / (size - 1)
                    g = g_idx / (size - 1)
                    b = b_idx / (size - 1)
                    
                    h, s, v = rgb_to_hsv(r, g, b)
                    
                    if style == 'provia':
                        # 标准曲线，稍微加点对比度
                        v = s_curve(v, 0.1)
                        s = min(1.0, s * 1.05)
                    elif style == 'velvia':
                        # 高对比度，高饱和度
                        v = s_curve(v, 0.25)
                        s = min(1.0, s * 1.3)
                    elif style == 'classic_chrome':
                        # 经典正片，低饱和，蓝色偏青，红色偏橙
                        v = s_curve(v, 0.15)
                        s = min(1.0, s * 0.75)
                        if 0.5 < h < 0.7:  # 蓝色
                            h = h - 0.05
                        if h < 0.1 or h > 0.9: # 红色
                            h = h + 0.02
                    elif style == 'astia':
                        # 柔和，对比度低
                        v = s_curve(v, -0.1)
                        s = min(1.0, s * 1.1)
                    elif style == 'monochrome':
                        # 黑白
                        s = 0.0
                        v = s_curve(v, 0.15)
                    elif style == 'classic_negative':
                        # 富士 Classic Negative (NC)：
                        # 高对比度，硬朗。色彩偏冷偏青，暗部浓郁发绿/青，高光带一点洋红/暖色。肤色偏硬。
                        v = s_curve(v, 0.25)  # 较高的对比度
                        s = min(1.0, s * 0.9) # 饱和度稍微降低，但比Classic Chrome高
                        
                        r_out, g_out, b_out = hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
                        
                        # 色彩偏移 (Classic Negative 特征)
                        # 暗部发青绿
                        if v < 0.5:
                            shadow_factor = (0.5 - v) / 0.5
                            r_out = max(0.0, r_out - 0.08 * shadow_factor)
                            g_out = min(1.0, g_out + 0.04 * shadow_factor)
                            b_out = min(1.0, b_out + 0.02 * shadow_factor)
                            
                        # 高光微微偏洋红/暖色
                        if v > 0.6:
                            highlight_factor = (v - 0.6) / 0.4
                            r_out = min(1.0, r_out + 0.05 * highlight_factor)
                            g_out = max(0.0, g_out - 0.02 * highlight_factor)
                            b_out = min(1.0, b_out + 0.01 * highlight_factor)
                            
                        f.write(f"{r_out:.6f} {g_out:.6f} {b_out:.6f}\n")
                        continue
                        
                    r_out, g_out, b_out = hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
                    f.write(f"{r_out:.6f} {g_out:.6f} {b_out:.6f}\n")

if __name__ == "__main__":
    generate_lut('Fuji_Provia_Standard', 16, 'provia')
    generate_lut('Fuji_Velvia_Vivid', 16, 'velvia')
    generate_lut('Fuji_Classic_Chrome', 16, 'classic_chrome')
    generate_lut('Fuji_Astia_Soft', 16, 'astia')
    generate_lut('Fuji_Monochrome', 16, 'monochrome')
    generate_lut('Fuji_Classic_Negative_NC', 16, 'classic_negative')
    print("All LUTs generated.")
