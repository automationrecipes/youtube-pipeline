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
    models = [C.GEMINI_MODEL, "gemini-flash-lite-latest"]
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature,
                             "responseMimeType": "application/json"},
    }
    last = "no response"
    for attempt in range(6):
        model = models[attempt % len(models)]
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{model}:generateContent")
        try:
            r = requests.post(url, json=body, timeout=240,
                              headers={"x-goog-api-key": C.GEMINI_API_KEY})
        except requests.exceptions.RequestException as e:
            last = f"{model}: {type(e).__name__}"
            print("Gemini retry:", last, flush=True)
            time.sleep(15 * (attempt + 1))
            continue
        if r.status_code in (404, 429, 500, 502, 503, 504):
            last = f"{model}: HTTP {r.status_code} {r.text[:200]}"
            print("Gemini retry:", last, flush=True)
            time.sleep(15 * (attempt + 1))
            continue
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        text = re.sub(r"^```(json)?|```$", "", text.strip()).strip()
        return json.loads(text)
    raise RuntimeError(f"Gemini kept failing. Last error: {last}")


def _is_hinglish():
    return (getattr(C, "LANGUAGE", "") or "").lower().startswith("hing")


def write_package():
    past = [h["title"] for h in load_history()][-80:]
    hinglish = _is_hinglish()
    if C.IS_SHORT:
        length = ("a YouTube Short of 110-150 words of narration in total (about 40-55 seconds), "
                  "exactly 5-7 scenes. Structure: scene 1 = HOOK (one punchy line that makes the "
                  "viewer stop scrolling: a bold claim, a painful problem or a surprising result), "
                  "scene 2 = PROMISE (what they will get from this Short), middle scenes = 3-4 quick, "
                  "concrete STEPS with real tool names and exact clicks, settings or prompts, "
                  "last scene = one short line that loops naturally back into the hook, then "
                  "'Follow karo, roz ek nayi automation recipe.' (or the English equivalent). "
                  "One idea only. No intro, no greeting, no channel name at the start.")
    else:
        length = ("a 4-6 minute YouTube video of 650-850 words total, 10-14 scenes. "
                  "Scene 1 is a 15-second hook that promises a concrete result. "
                  "Then deliver step-by-step value with specific tool names, settings "
                  "and examples. Last scene: quick recap and ask viewers to subscribe "
                  "for a new automation recipe every day.")

    if hinglish:
        lang = ("LANGUAGE: natural spoken HINGLISH, the way young Indian tech creators talk on "
                "YouTube: Hindi sentence flow with English tech words. Write Hindi words in "
                "DEVANAGARI script and English/tech words (tool names, automation, email, formula, "
                "click, settings, free, AI) in LATIN script, for example: "
                "'आज हम Google Sheets में leads को automatically sort करेंगे, बिल्कुल free में.' "
                "Keep it conversational and energetic (dekho, simple hai, bas itna karo style), "
                "address the viewer as आप. Title, description and hashtags in ROMAN Hinglish with "
                "English keywords, e.g. 'Google Sheets se Leads Automate Karo FREE | AI Trick'.")
        audience = (f"{C.AUDIENCE} in India (Hindi-speaking small business owners, "
                    "freelancers, shop owners and students)")
    else:
        lang = "LANGUAGE: plain spoken English, short sentences."
        audience = C.AUDIENCE

    prompt = f"""You are the head writer of the faceless YouTube channel "{C.CHANNEL_NAME}".
Niche: {C.NICHE}.
Audience: {audience}.

Pick ONE fresh, specific, high-search-intent topic that gives a real, useful result
(e.g. "Gmail + Google Sheets se invoice follow-ups automate karo", "ChatGPT se 10 minute mein
1 hafte ka Instagram content"). Prefer tools with free plans. Give genuine information gain:
a specific trick, setting, prompt or workflow, never generic advice. Do not repeat or closely
mirror these past titles:
{json.dumps(past, ensure_ascii=False)}

Write {length}
{lang}
Rules: no emojis in narration, no "[music]" cues, no stage directions. Do not invent prices,
statistics or features you are unsure of. Do not claim to be a human or show a face.

For every scene also give:
- "headline": 2-5 word on-screen title in CAPS using ROMAN letters only (English or Roman
  Hinglish), e.g. "STEP 1: SHEET BANAO", "FREE AUTO REPLY". Scene 1 headline is the hook.
- "footage": a 2-4 word ENGLISH stock-footage search query showing something generic and
  filmable (e.g. "laptop typing", "phone notifications"), never brand logos.

Return ONLY JSON with this exact shape:
{{
  "title": "YouTube title under 70 characters, keyword first, curiosity second",
  "description": "80-200 word description: what the viewer learns, the tools used, a call to follow",
  "tags": ["10-15 search tags, Hinglish and English"],
  "hashtags": ["#shorts", "#automation", "3-5 more"],
  "thumbnail_text": "2-4 punchy words in CAPS",
  "scenes": [{{"narration": "...", "headline": "...", "footage": "..."}}]
}}"""
    lo, hi = (90, 190) if C.IS_SHORT else (550, 1000)
    pkg = None
    for attempt in range(3):
        pkg = _gemini(prompt)
        scenes = pkg.get("scenes") or []
        words = sum(len(str(s.get("narration", "")).split()) for s in scenes)
        if scenes and lo <= words <= hi and all(s.get("narration") for s in scenes):
            break
        print(f"  script rejected ({len(scenes)} scenes, {words} words), retrying", flush=True)
    assert pkg and pkg.get("scenes"), "Gemini returned no scenes"
    pkg["tags"] = [t[:30] for t in pkg.get("tags", [])][:15]
    pkg["title"] = pkg["title"][:95]
    if C.IS_SHORT and "#shorts" not in pkg["title"].lower():
        pkg["title"] = (pkg["title"][:88] + " #shorts")
    return pkg
