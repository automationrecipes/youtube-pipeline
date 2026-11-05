"""Uploads the video (and thumbnail) with the YouTube Data API using a refresh token."""
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from . import config as C


def client():
    missing = [n for n in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")
               if not getattr(C, n)]
    if missing:
        raise SystemExit(f"Missing secrets: {', '.join(missing)}")
    creds = Credentials(None, refresh_token=C.YT_REFRESH_TOKEN,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=C.YT_CLIENT_ID, client_secret=C.YT_CLIENT_SECRET)
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(pkg, video, thumb=None):
    yt = client()
    desc = pkg["description"].strip()
    if pkg.get("hashtags"):
        desc += "\n\n" + " ".join(pkg["hashtags"][:3])
    body = {
        "snippet": {"title": pkg["title"], "description": desc[:4900],
                    "tags": pkg.get("tags", []), "categoryId": C.CATEGORY_ID,
                    "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": C.PRIVACY, "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": True, "embeddable": True},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=8 << 20,
                                                        resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  upload {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(f"  uploaded: https://youtu.be/{vid}")

    if thumb and not C.IS_SHORT:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
            print("  thumbnail set")
        except HttpError as e:
            # Custom thumbnails need a phone-verified channel.
            print(f"  thumbnail skipped: {e}")
    return vid
