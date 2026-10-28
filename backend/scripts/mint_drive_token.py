"""Mint a fresh Google Drive refresh token for this app.

Usage:
    cd backend && source venv/bin/activate && python scripts/mint_drive_token.py

Opens a browser for Google sign-in (use the account that owns the Drive
folder), then prints the new GOOGLE_OAUTH_REFRESH_TOKEN to paste into .env.

Note: if the OAuth consent screen is still in "Testing" mode, Google expires
refresh tokens after 7 days. Publish the app (Google Cloud Console → APIs &
Services → OAuth consent screen → "Publish app") so the token lasts forever.
"""
import os

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

# Load the repo-root .env (backend/scripts/ -> ../../.env)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"))

client_id = os.environ["GOOGLE_OAUTH_CLIENT_ID"]
client_secret = os.environ["GOOGLE_OAUTH_CLIENT_SECRET"]

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    },
    scopes=["https://www.googleapis.com/auth/drive.file"],
)
# prompt=consent forces Google to issue a new refresh token even if one
# was granted before (otherwise it may return only an access token).
creds = flow.run_local_server(port=0, prompt="consent")

print("\n" + "=" * 60)
print("ใส่ค่านี้ใน backend/.env (แทนค่าเดิม):")
print(f"GOOGLE_OAUTH_REFRESH_TOKEN={creds.refresh_token}")
print("=" * 60)
