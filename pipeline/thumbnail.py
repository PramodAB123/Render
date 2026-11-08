"""Make a 1280x720 thumbnail locally: a frame from the video + big outlined text (Pillow)."""
import os, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from common import FFMPEG

FONTS = ["C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/arialbd.ttf",
         "/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def make(video, text, out, at=None, total=None, color="#ffe34a"):
    frame = out + ".frame.jpg"; at = at if at is not None else (total or 9) * 0.35
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{at:.2f}", "-i", video, "-frames:v", "1", frame], check=True)
    src = Image.open(frame).convert("RGB"); W, H = 1280, 720
    if src.width > src.height:   # long video (16:9): full-bleed frame, darkened on the left for the text
        bg = src.resize((W, H)); shade = Image.linear_gradient("L").rotate(-90).resize((W, H))
        bg = Image.composite(Image.eval(bg, lambda p: int(p * 0.35)), bg, shade); text_w = int(W * 0.58)
    else:                        # Short (9:16): blurred background + the frame on the right
        bg = src.copy(); bg = bg.resize((W, int(W * bg.height / bg.width))).crop((0, 0, W, H)).filter(ImageFilter.GaussianBlur(18))
        bg = Image.eval(bg, lambda p: int(p * 0.55))
        fg = src.resize((int(H * src.width / src.height), H)); bg.paste(fg, (W - fg.width - 40, 0)); text_w = W - fg.width - 80
    d = ImageDraw.Draw(bg); font_path = next((f for f in FONTS if os.path.exists(f)), None)
    words = text.upper().split(); lines = [" ".join(words[i:i + 2]) for i in range(0, len(words), 2)] or ["WATCH"]
    size = 150
    while size > 50:
        font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
        if all(d.textlength(l, font=font) < text_w for l in lines) and size * 1.1 * len(lines) < H - 80:
            break
        size -= 6
    y = (H - size * 1.1 * len(lines)) / 2
    for i, l in enumerate(lines):
        d.text((40, y + i * size * 1.1), l, font=font, fill=color if i == len(lines) - 1 else "white",
               stroke_width=max(4, size // 14), stroke_fill="black")
    bg.save(out, quality=92); os.remove(frame)
    return out


# Instagram / Shorts cover the top ~220 px and the bottom ~420 px of a 1080x1920 video (safe area from claude-animation-skills)
SAFE_TOP, SAFE_BOTTOM, SAFE_SIDE = 220, 1500, 100


def sheet(video, out, total, n=8):
    """Contact sheet of n frames; on portrait videos the red box is the area the app UI won't cover."""
    try:
        frames = []
        for k in range(n):
            f = f"{out}.{k}.jpg"
            subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{total * (k + 0.5) / n:.2f}", "-i", video, "-frames:v", "1", f], check=True)
            im = Image.open(f).convert("RGB"); os.remove(f)
            if im.height > im.width:
                d = ImageDraw.Draw(im); sx, sy = im.width / 1080, im.height / 1920
                d.rectangle([SAFE_SIDE * sx, SAFE_TOP * sy, im.width - SAFE_SIDE * sx, SAFE_BOTTOM * sy], outline="#ff2e3f", width=6)
            frames.append(im.resize((360, int(360 * im.height / im.width))))
        cols = 4; w, h = frames[0].size; s = Image.new("RGB", (w * cols, h * ((len(frames) + cols - 1) // cols)), "black")
        for i, im in enumerate(frames):
            s.paste(im, ((i % cols) * w, (i // cols) * h))
        s.save(out, quality=85)
    except Exception as e:
        print("  contact sheet skipped:", e)
