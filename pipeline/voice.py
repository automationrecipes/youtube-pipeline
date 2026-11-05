"""Free neural voiceover with edge-tts, plus word timings for captions."""
import asyncio
import os
import ssl
import edge_tts
from . import config as C

# Respect a custom CA bundle when running behind a corporate proxy.
if os.environ.get("SSL_CERT_FILE"):
    import edge_tts.communicate as _cm
    _cm._SSL_CTX = ssl.create_default_context(cafile=os.environ["SSL_CERT_FILE"])


async def _speak(text, mp3_path):
    words = []
    com = edge_tts.Communicate(text, C.VOICE, rate=C.VOICE_RATE, boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
    return words


def speak(text, mp3_path, retries=4):
    for i in range(retries):
        try:
            return asyncio.run(_speak(text, mp3_path))
        except Exception:
            if i == retries - 1:
                raise
            asyncio.run(asyncio.sleep(5 * (i + 1)))
