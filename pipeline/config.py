"""All settings in one place. Override any of them with environment variables
(or GitHub Actions repository *variables*)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
OUT = ROOT / "out"

def env(name, default=None):
    v = (os.environ.get(name) or "").strip()
    return v if v not in (None, "") else default

# --- Channel ---------------------------------------------------------------
CHANNEL_NAME = env("CHANNEL_NAME", "Automation Recipes")
NICHE = env("NICHE", "AI and software tools for small businesses and marketers: "
            "practical automations, workflows and tool walkthroughs that save time or make money")
AUDIENCE = env("AUDIENCE", "small business owners, freelancers and marketers who are not developers")

# --- Format ----------------------------------------------------------------
# "long"  = 16:9 video, ~4-6 minutes, custom thumbnail
# "short" = 9:16 YouTube Short, under 60 seconds
VIDEO_FORMAT = env("VIDEO_FORMAT", "long").lower()
IS_SHORT = VIDEO_FORMAT == "short"
WIDTH, HEIGHT = (1080, 1920) if IS_SHORT else (1920, 1080)
FPS = 30

# --- Free services ---------------------------------------------------------
GEMINI_API_KEY = env("GEMINI_API_KEY")                  # free key: aistudio.google.com
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-flash-latest")
PEXELS_API_KEY = env("PEXELS_API_KEY")                  # free key: pexels.com/api
VOICE = env("TTS_VOICE", "en-US-AndrewNeural")          # any edge-tts voice
VOICE_RATE = env("TTS_RATE", "+5%")

# --- YouTube ---------------------------------------------------------------
YT_CLIENT_ID = env("YT_CLIENT_ID")
YT_CLIENT_SECRET = env("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = env("YT_REFRESH_TOKEN")
# Until Google approves your API audit, YouTube forces uploads to private anyway.
PRIVACY = env("PRIVACY", "private")                     # private | unlisted | public
CATEGORY_ID = env("CATEGORY_ID", "28")                  # 28 = Science & Technology
DRY_RUN = env("DRY_RUN", "0") == "1"                    # build video, skip upload

# --- Fonts -----------------------------------------------------------------
FONT_BOLD = env("FONT_BOLD", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
CAPTION_FONT = env("CAPTION_FONT", "DejaVu Sans")
