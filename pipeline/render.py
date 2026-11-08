"""Turns the script into a finished MP4: voice + stock footage + burned-in captions."""
import json
import random
import subprocess
import time
import requests
from . import config as C
from .voice import speak


def run(cmd, cwd=None):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(map(str, cmd))}\n{p.stderr[-2000:]}")
    return p.stdout


def duration(path):
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "json", str(path)])
    return float(json.loads(out)["format"]["duration"])


# ---------------------------------------------------------------- footage --
_used_ids = set()


def fetch_footage(query, dest):
    """Download a free Pexels clip for the query. Returns path or None."""
    if not C.PEXELS_API_KEY:
        return None
    orient = "portrait" if C.IS_SHORT else "landscape"
    for q in (query, " ".join(query.split()[:2]), "technology office"):
        try:
            r = requests.get("https://api.pexels.com/videos/search",
                             params={"query": q, "orientation": orient, "per_page": 15},
                             headers={"Authorization": C.PEXELS_API_KEY}, timeout=30)
            r.raise_for_status()
            vids = [v for v in r.json().get("videos", []) if v["id"] not in _used_ids]
        except Exception:
            continue
        random.shuffle(vids)
        for v in vids:
            files = [f for f in v["video_files"]
                     if f.get("file_type") == "video/mp4" and f.get("width")
                     and min(f["width"], f["height"]) >= 720]
            if not files:
                continue
            f = min(files, key=lambda f: abs(max(f["width"], f["height"]) - 1920))
            try:
                with requests.get(f["link"], stream=True, timeout=120) as resp:
                    resp.raise_for_status()
                    with open(dest, "wb") as out:
                        for chunk in resp.iter_content(1 << 20):
                            out.write(chunk)
                _used_ids.add(v["id"])
                return dest
            except Exception:
                continue
    return None


# ---------------------------------------------------------------- images --
_img_disabled = False


def fetch_image(query, dest):
    """Free AI background image (Pollinations, no key). Tried once per video;
    if the service is blocked or slow it is skipped for the rest of the run."""
    global _img_disabled
    if _img_disabled or C.env("AI_IMAGES", "0") != "1":   # off by default: consistent slides
        return None
    prompt = (f"{query}, modern clean tech illustration, cinematic lighting, "
              "high detail, no text, no words")
    url = "https://image.pollinations.ai/prompt/" + requests.utils.quote(prompt)
    try:
        r = requests.get(url, params={"width": C.WIDTH, "height": C.HEIGHT,
                                      "nologo": "true", "seed": random.randint(1, 10**6)},
                         timeout=60)
        if r.ok and r.headers.get("content-type", "").startswith("image"):
            dest.write_bytes(r.content)
            return dest
        reason = f"HTTP {r.status_code} {r.headers.get('content-type', '')}"
    except Exception as e:
        reason = type(e).__name__
    print(f"  AI image unavailable ({reason}); using branded slides", flush=True)
    _img_disabled = True
    return None


# ---------------------------------------------------------------- slides --
PALETTES = [((10, 15, 40), (37, 99, 235)), ((15, 10, 40), (124, 58, 237)),
            ((5, 30, 45), (8, 145, 178)), ((10, 35, 25), (22, 163, 74)),
            ((40, 12, 10), (234, 88, 12)), ((35, 8, 30), (219, 39, 119))]
ACCENT = (255, 204, 0)


def _font(size):
    from PIL import ImageFont
    for path in (C.FONT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        test = f"{cur} {w}".strip()
        if cur and draw.textlength(test, font=font) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


def make_slide(headline, idx, total, dest):
    """Branded background for one scene: gradient, glow, step tag, big headline.
    Drawn locally with Pillow, so it always works (no network, no keys)."""
    from PIL import Image, ImageDraw, ImageFilter
    W, H = C.WIDTH, C.HEIGHT
    top, bot = PALETTES[idx % len(PALETTES)]

    grad = Image.new("RGB", (1, H))
    for y in range(H):
        t = y / (H - 1)
        grad.putpixel((0, y), tuple(int(top[k] + (bot[k] - top[k]) * t) for k in range(3)))
    img = grad.resize((W, H))

    glow = Image.new("RGB", (W, H), (0, 0, 0))
    gd = ImageDraw.Draw(glow)
    rnd = random.Random(idx * 7919 + total)
    for _ in range(3):
        r = rnd.randint(W // 4, W // 2)
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        gd.ellipse([x - r, y - r, x + r, y + r], fill=tuple(min(255, c + 60) for c in bot))
    glow = glow.filter(ImageFilter.GaussianBlur(W // 8))
    img = Image.blend(img, glow, 0.35)

    d = ImageDraw.Draw(img)
    # thin grid lines for a "tech" look
    step = W // 9
    for x in range(0, W, step):
        d.line([(x, 0), (x, H)], fill=tuple(min(255, c + 18) for c in top), width=1)
    for y in range(0, H, step):
        d.line([(0, y), (W, y)], fill=tuple(min(255, c + 18) for c in top), width=1)

    # tag pill: hook / step n / last
    if idx == 0:
        tag = "AUTOMATION RECIPE"
    elif idx == total - 1:
        tag = "FOLLOW FOR MORE"
    else:
        tag = f"STEP {idx}"
    tf = _font(int(W * 0.045))
    tw = d.textlength(tag, font=tf)
    px, py = int(W * 0.04), int(W * 0.022)
    ty = int(H * 0.17)
    d.rounded_rectangle([(W - tw) / 2 - px, ty - py, (W + tw) / 2 + px, ty + tf.size + py],
                        radius=40, fill=ACCENT)
    d.text(((W - tw) / 2, ty), tag, font=tf, fill=(15, 15, 15))

    # big headline (Roman letters only, so the bold Latin font is safe)
    text = (headline or "").upper().strip() or tag
    size = int(W * (0.12 if idx == 0 else 0.10))
    while True:
        hf = _font(size)
        lines = _wrap(d, text, hf, W * 0.86)
        if len(lines) <= 4 or size < W * 0.05:
            break
        size = int(size * 0.9)
    lh = int(size * 1.18)
    y0 = int(H * 0.36) - (lh * len(lines)) // 2
    for n, ln in enumerate(lines[:4]):
        lw = d.textlength(ln, font=hf)
        fill = ACCENT if (idx == 0 and n == len(lines[:4]) - 1) else (255, 255, 255)
        d.text(((W - lw) / 2, y0 + n * lh), ln, font=hf, fill=fill,
               stroke_width=max(4, size // 18), stroke_fill=(0, 0, 0))
    bar_y = y0 + lh * len(lines[:4]) + int(size * 0.25)
    d.rounded_rectangle([W * 0.38, bar_y, W * 0.62, bar_y + 14], radius=7, fill=ACCENT)

    img.save(dest, quality=93)
    return dest


# --------------------------------------------------------------- captions --
def _ts(t):
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _clean(t):
    return t.replace("{", "").replace("}", "").replace("\\", "")


def write_ass(words, path, total):
    """Burned-in captions: a few words at a time, the spoken word highlighted yellow."""
    per = 3 if C.IS_SHORT else 6
    size = 92 if C.IS_SHORT else 58
    margin_v = 430 if C.IS_SHORT else 70
    hi = "{\\c&H0000CCFF&}"   # yellow (BGR)
    lines = []
    for i in range(0, len(words), per):
        chunk = words[i:i + per]
        nxt = words[i + per][0] if i + per < len(words) else total
        chunk_end = max(chunk[-1][1], min(nxt, chunk[-1][1] + 0.6))
        for j, (start, end, _) in enumerate(chunk):
            w_end = chunk[j + 1][0] if j + 1 < len(chunk) else chunk_end
            parts = []
            for k, w in enumerate(chunk):
                t = _clean(w[2])
                if C.IS_SHORT and t.isascii():
                    t = t.upper()
                parts.append(f"{hi}{t}{{\\c&H00FFFFFF&}}" if k == j else t)
            lines.append(f"Dialogue: 0,{_ts(start)},{_ts(w_end)},Cap,,0,0,0,,{' '.join(parts)}")
    path.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {C.WIDTH}
PlayResY: {C.HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{C.CAPTION_FONT},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,6,3,2,70,70,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ build --
def build_scene(i, scene, work, total=1):
    audio = work / f"s{i}.mp3"
    words = speak(scene["narration"], audio)
    dur = duration(audio) + 0.35
    write_ass(words, work / f"s{i}.ass", dur)

    query = scene.get("footage", "technology")
    clip = fetch_footage(query, work / f"s{i}_src.mp4")
    img = None if clip else fetch_image(query, work / f"s{i}_bg.jpg")
    if not clip and not img:
        img = make_slide(scene.get("headline") or "", i, total, work / f"s{i}_slide.jpg")
    W, H = C.WIDTH, C.HEIGHT
    if clip:
        inputs = ["-stream_loop", "-1", "-i", clip.name]
        base = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"setsar=1,fps={C.FPS},eq=brightness=-0.06:saturation=1.05[bg]")
    else:  # still image (AI image or branded slide) with a slow Ken Burns zoom
        frames = int(dur * C.FPS) + C.FPS
        dim = "eq=brightness=-0.08," if img.name.endswith("_bg.jpg") else ""
        inputs = ["-i", img.name]
        base = (f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
                f"crop={W * 2}:{H * 2},"
                f"zoompan=z='min(zoom+0.0005,1.08)':d={frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={C.FPS},"
                f"{dim}setsar=1[bg]")

    logo = C.ASSETS / "logo.png"
    filt = base
    extra = []
    if logo.exists():
        extra = ["-i", str(logo)]
        lw = 150 if C.IS_SHORT else 130
        filt += (f";[2:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa=0.85[lg]"
                 f";[bg][lg]overlay=W-w-40:40[bg2]")
        last = "bg2"
    else:
        last = "bg"
    filt += f";[{last}]ass=s{i}.ass[v]"

    run(["ffmpeg", "-y", *inputs, "-i", audio.name, *extra,
         "-filter_complex", filt, "-map", "[v]", "-map", "1:a",
         "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
         "-pix_fmt", "yuv420p", "-r", str(C.FPS),
         "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-ac", "2",
         f"s{i}.mp4"], cwd=work)
    return work / f"s{i}.mp4"


def render(pkg, work):
    work.mkdir(parents=True, exist_ok=True)
    parts = []
    for i, scene in enumerate(pkg["scenes"]):
        print(f"  scene {i + 1}/{len(pkg['scenes'])}")
        parts.append(build_scene(i, scene, work, len(pkg["scenes"])))

    (work / "list.txt").write_text("".join(f"file '{p.name}'\n" for p in parts))
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt",
         "-c", "copy", "joined.mp4"], cwd=work)

    final = work / "final.mp4"
    music = C.ASSETS / "music.mp3"
    if music.exists():
        run(["ffmpeg", "-y", "-i", "joined.mp4", "-stream_loop", "-1", "-i", str(music),
             "-filter_complex",
             "[1:a]volume=0.07[m];[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
             final.name], cwd=work)
    else:
        (work / "joined.mp4").rename(final)
    return final
