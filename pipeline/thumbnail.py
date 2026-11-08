"""Make a 1280x720 thumbnail locally: a frame from the video + big outlined text (Pillow)."""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from common import FFMPEG

FONTS = ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/arialbd.ttf",
         "/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def make(video, text, out, at=None, total=None):
    frame = out + ".frame.jpg"; at = at if at is not None else (total or 9) * 0.35
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", video, "-frames:v", "1", frame], check=True)
    src = Image.open(frame).convert("RGB"); W, H = 1280, 720
    bg = src.copy(); bg = bg.resize((W, int(W * bg.height / bg.width))).crop((0, 0, W, H)).filter(ImageFilter.GaussianBlur(18))
    bg = Image.eval(bg, lambda p: int(p * 0.55))
    fg = src.resize((int(H * src.width / src.height), H)); bg.paste(fg, (W - fg.width - 40, 0))
    d = ImageDraw.Draw(bg); font_path = next((f for f in FONTS if os.path.exists(f)), None)
    words = text.upper().split(); lines = [" ".join(words[i:i + 2]) for i in range(0, len(words), 2)] or ["WATCH"]
    size = 150
    while size > 50:
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        if all(d.textlength(l, font=font) < W - fg.width - 80 for l in lines) and size * 1.1 * len(lines) < H - 80:
            break
        size -= 6
    y = (H - size * 1.1 * len(lines)) / 2
    for i, l in enumerate(lines):
        d.text((40, y + i * size * 1.1), l, font=font, fill="#ffe34a" if i == len(lines) - 1 else "white",
               stroke_width=max(4, size // 14), stroke_fill="black")
    bg.save(out, quality=92); os.remove(frame)
    return out
