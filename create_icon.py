"""
Generate application icon for CUBE-to-XMP
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # Create a 256x256 icon
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle (dark blue gradient effect)
    for i in range(size//2, 0, -1):
        color = (30 + i//10, 60 + i//8, 120 + i//5)
        draw.ellipse([size//2-i, size//2-i, size//2+i, size//2+i], fill=color)

    # Draw "C" and "X" letters
    try:
        font_large = ImageFont.truetype("arial.ttf", 80)
        font_small = ImageFont.truetype("arial.ttf", 40)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # C letter (cyan)
    draw.text((50, 60), "C", fill=(0, 220, 255), font=font_large)

    # X letter (magenta)
    draw.text((130, 120), "X", fill=(255, 100, 200), font=font_large)

    # Arrow symbol (white)
    draw.text((90, 155), "⇄", fill=(255, 255, 255), font=font_small)

    # Save as ICO
    icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
    img.save(icon_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Icon saved to: {icon_path}")

    # Also save as PNG for preview
    png_path = os.path.join(os.path.dirname(__file__), 'icon.png')
    img.save(png_path, format='PNG')
    print(f"PNG saved to: {png_path}")

if __name__ == '__main__':
    create_icon()
