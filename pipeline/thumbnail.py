"""1280x720 thumbnail: video frame + bold text + optional AI-avatar cut-out."""
import subprocess
import textwrap
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from . import config as C

ACCENT = (255, 196, 0)


def make(video, text, dest):
    frame = dest.with_name("frame.jpg")
    # use raw stock footage (no burned-in captions) for the background
    sources = sorted(video.parent.glob("s*_src.mp4"))
    if sources:
        subprocess.run(["ffmpeg", "-y", "-ss", "2", "-i", str(sources[0]),
                        "-frames:v", "1", str(frame)], capture_output=True)
    W, H = 1280, 720
    if frame.exists():
        bg = Image.open(frame).convert("RGB").resize((W, H))
        bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(3))).enhance(0.45)
    else:
        bg = Image.new("RGB", (W, H), (15, 23, 42))

    # dark gradient on the left for text contrast
    grad = Image.new("L", (W, 1))
    grad.putdata([int(220 * max(0, 1 - x / (W * 0.75))) for x in range(W)])
    bg.paste(Image.new("RGB", (W, H), (0, 0, 0)), (0, 0), grad.resize((W, H)))

    avatar = C.ASSETS / "avatar.png"          # transparent PNG of the AI host
    text_w = W - 80
    if avatar.exists():
        av = Image.open(avatar).convert("RGBA")
        av.thumbnail((560, 700))
        bg.paste(av, (W - av.width - 10, H - av.height), av)
        text_w = W - av.width - 60

    d = ImageDraw.Draw(bg)
    words = text.upper().strip()
    size = 150
    while size > 50:
        font = ImageFont.truetype(C.FONT_BOLD, size)
        lines = textwrap.wrap(words, width=max(4, int(text_w / (size * 0.62))))
        block_h = len(lines) * int(size * 1.08)
        widest = max(d.textlength(l, font=font) for l in lines)
        if widest <= text_w and block_h <= H - 140 and len(lines) <= 3:
            break
        size -= 6
    y = (H - block_h) // 2
    for n, line in enumerate(lines):
        color = ACCENT if n == len(lines) - 1 else (255, 255, 255)
        d.text((50, y), line, font=font, fill=color, stroke_width=8, stroke_fill=(0, 0, 0))
        y += int(size * 1.08)

    logo = C.ASSETS / "logo.png"
    if logo.exists():
        lg = Image.open(logo).convert("RGBA")
        lg.thumbnail((110, 110))
        bg.paste(lg, (40, 30), lg)

    bg.save(dest, "JPEG", quality=92)
    return dest
