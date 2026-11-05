"""
One-time sign-in for the Automation Recipes YouTube uploader.

1. Put this file in the same folder as client_secret.json (the file you downloaded).
2. Run:
       pip install google-auth-oauthlib
       python get_refresh_token.py
3. A browser opens. Sign in with the account that owns the Automation Recipes
   channel, pick the Automation Recipes channel (brand account) if asked,
   click Advanced -> "Go to app" on the unverified-app warning, then Allow.
4. Your client ID, client secret and refresh token are saved to youtube_token.json.
   Keep that file private. Never commit it or paste it publicly.
"""
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",     # upload videos + set thumbnails
    "https://www.googleapis.com/auth/youtube.readonly",   # read channel/playlist info
]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

if not creds.refresh_token:
    raise SystemExit("No refresh token returned. Remove the app at "
                     "https://myaccount.google.com/permissions and run again.")

with open("youtube_token.json", "w") as f:
    json.dump({
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "refresh_token": creds.refresh_token,
    }, f, indent=2)

print("Done. Saved youtube_token.json. Keep it private.")
