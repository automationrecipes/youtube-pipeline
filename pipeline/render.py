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
def fetch_image(query, dest):
    """Free AI background image (Pollinations, no key). Returns path or None."""
    prompt = (f"{query}, modern clean tech illustration, cinematic lighting, "
              "high detail, no text, no words")
    url = "https://image.pollinations.ai/prompt/" + requests.utils.quote(prompt)
    for attempt in range(3):
        try:
            r = requests.get(url, params={"width": C.WIDTH, "height": C.HEIGHT,
                                          "nologo": "true",
                                          "seed": random.randint(1, 10**6)},
                             timeout=120)
            if r.ok and r.headers.get("content-type", "").startswith("image"):
                dest.write_bytes(r.content)
                return dest
        except Exception:
            pass
        time.sleep(5 * (attempt + 1))
    return None


# --------------------------------------------------------------- captions --
def _ts(t):
    h, rem = divmod(max(t, 0), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_ass(words, path, total):
    per = 3 if C.IS_SHORT else 6
    size = 82 if C.IS_SHORT else 58
    margin_v = 520 if C.IS_SHORT else 70
    lines = []
    for i in range(0, len(words), per):
        chunk = words[i:i + per]
        start = chunk[0][0]
        nxt = words[i + per][0] if i + per < len(words) else total
        end = max(chunk[-1][1], min(nxt, chunk[-1][1] + 0.6))
        text = " ".join(w[2] for w in chunk).replace("{", "").replace("}", "")
        if C.IS_SHORT:
            text = text.upper()
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Cap,,0,0,0,,{text}")
    path.write_text(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {C.WIDTH}
PlayResY: {C.HEIGHT}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{C.CAPTION_FONT},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,5,2,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(lines) + "\n")


# ------------------------------------------------------------------ build --
def build_scene(i, scene, work):
    audio = work / f"s{i}.mp3"
    words = speak(scene["narration"], audio)
    dur = duration(audio) + 0.35
    write_ass(words, work / f"s{i}.ass", dur)

    clip = fetch_footage(scene.get("footage", "technology"), work / f"s{i}_src.mp4")
    img = None if clip else fetch_image(scene.get("footage", "technology"),
                                        work / f"s{i}_bg.jpg")
    W, H = C.WIDTH, C.HEIGHT
    if clip:
        inputs = ["-stream_loop", "-1", "-i", clip.name]
        base = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"setsar=1,fps={C.FPS},eq=brightness=-0.06:saturation=1.05[bg]")
    elif img:  # free AI image with a slow Ken Burns zoom
        frames = int(dur * C.FPS) + C.FPS
        inputs = ["-i", img.name]
        base = (f"[0:v]scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,"
                f"crop={W * 2}:{H * 2},"
                f"zoompan=z='min(zoom+0.0007,1.2)':d={frames}:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={C.FPS},"
                f"setsar=1,eq=brightness=-0.08[bg]")
    else:  # no footage and no image: clean branded background
        inputs = ["-f", "lavfi", "-i", f"color=c=0x0f172a:s={W}x{H}:r={C.FPS}"]
        base = "[0:v]setsar=1[bg]"

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
        parts.append(build_scene(i, scene, work))

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
