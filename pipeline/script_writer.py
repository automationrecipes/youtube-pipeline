"""Picks a fresh topic and writes the full video package with Gemini (free tier)."""
import json
import re
import time
import requests
from . import config as C

HISTORY = C.DATA / "history.json"


def load_history():
    if HISTORY.exists():
        return json.loads(HISTORY.read_text())
    return []


def save_history(entry):
    hist = load_history()
    hist.append(entry)
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    HISTORY.write_text(json.dumps(hist[-500:], indent=2))


def _gemini(prompt, temperature=0.9):
    if not C.GEMINI_API_KEY:
        raise SystemExit("GEMINI_API_KEY is missing.")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{C.GEMINI_MODEL}:generateContent")
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature,
                             "responseMimeType": "application/json"},
    }
    for attempt in range(5):
        try:
            r = requests.post(url, json=body, timeout=180,
                              headers={"x-goog-api-key": C.GEMINI_API_KEY})
        except requests.exceptions.RequestException:
            time.sleep(20 * (attempt + 1))
            continue
        if r.status_code in (429, 500, 503):
            time.sleep(20 * (attempt + 1))
            continue
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = re.sub(r"^```(json)?|```$", "", text.strip()).strip()
        return json.loads(text)
    raise RuntimeError("Gemini kept failing (rate limit or outage).")


def write_package():
    past = [h["title"] for h in load_history()][-80:]
    if C.IS_SHORT:
        length = ("a YouTube Short of 110-140 words total (about 45-55 seconds), "
                  "5-7 scenes, first line is a scroll-stopping hook, ends with "
                  "'Follow for more automation recipes.'")
    else:
        length = ("a 4-6 minute YouTube video of 650-850 words total, 10-14 scenes. "
                  "Scene 1 is a 15-second hook that promises a concrete result. "
                  "Then deliver step-by-step value with specific tool names, settings "
                  "and examples. Last scene: quick recap and ask viewers to subscribe "
                  "for a new automation recipe every day.")

    prompt = f"""You are the head writer of the faceless YouTube channel "{C.CHANNEL_NAME}".
Niche: {C.NICHE}.
Audience: {C.AUDIENCE}.

Pick ONE fresh, specific, high-search-intent topic (e.g. "Automate your invoice follow-ups with
Gmail + Google Sheets for free", "5 free AI tools that replace a $500/mo marketing stack").
Prefer tools that have free plans. Do not repeat or closely mirror these past titles:
{json.dumps(past)}

Write {length}
Rules: plain spoken English, short sentences, no emojis in narration, no "[music]" cues,
do not invent prices, statistics or features you are unsure of; say "check the current
pricing" instead. Do not claim to be a human or show a face.

For every scene give a 2-4 word stock-footage search query showing something generic and
filmable (e.g. "laptop typing", "office teamwork", "phone notifications"), never brand logos.

Return ONLY JSON with this exact shape:
{{
  "title": "YouTube title under 70 characters, curiosity + keyword",
  "description": "150-250 word SEO description with 3 short timestamps-free paragraphs and a call to subscribe",
  "tags": ["10-15 search tags"],
  "hashtags": ["#3", "#hashtags", "#max"],
  "thumbnail_text": "2-4 punchy words in CAPS for the thumbnail",
  "scenes": [{{"narration": "...", "footage": "..."}}]
}}"""
    pkg = _gemini(prompt)
    assert pkg.get("scenes"), "Gemini returned no scenes"
    pkg["tags"] = [t[:30] for t in pkg.get("tags", [])][:15]
    pkg["title"] = pkg["title"][:95]
    if C.IS_SHORT and "#shorts" not in pkg["title"].lower():
        pkg["title"] = (pkg["title"][:88] + " #shorts")
    return pkg
