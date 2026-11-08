"""Upload to YouTube with the free YouTube Data API (OAuth). First run opens your browser to sign in once."""
import json, sys
from common import SECRETS, load_config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    import os
    tok, cs = SECRETS / "token.json", SECRETS / "client_secret.json"
    if os.environ.get("YT_REFRESH_TOKEN"):  # cloud runs: refresh token + OAuth client from GitHub secrets
        creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
                            client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"], scopes=SCOPES)
        creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)
    creds = Credentials.from_authorized_user_file(str(tok), SCOPES) if tok.exists() else None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not cs.exists():
            sys.exit("Missing secrets\\client_secret.json - see SETUP.md step 2.")
        creds = InstalledAppFlow.from_client_secrets_file(str(cs), SCOPES).run_local_server(port=0)
        tok.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def upload(video, meta, thumb=None, g=None):
    from googleapiclient.http import MediaFileUpload
    y = load_config()["youtube"]; yt = service()
    g = g or {}
    tags = list(dict.fromkeys((meta.get("tags") or []) + g.get("tags", []) + ["shorts"]))[:15]
    body = {"snippet": {"title": meta["title"][:95] + " #shorts" if "#shorts" not in meta["title"] else meta["title"][:100],
                        "description": meta.get("description", "") + "\n\n#shorts", "tags": tags, "categoryId": g.get("category_id", "24")},
            "status": {"privacyStatus": y["privacy"], "selfDeclaredMadeForKids": y["made_for_kids"],
                       "containsSyntheticMedia": y.get("synthetic_media", True)}}
    req = yt.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(video, chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status: print(f"  uploaded {int(status.progress() * 100)}%")
    vid = resp["id"]; print(f"  done: https://youtu.be/{vid}  ({y['privacy']})")
    if thumb:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb)).execute(); print("  thumbnail set")
        except Exception as e:
            print("  thumbnail not set (needs a phone-verified channel; Shorts may ignore it):", str(e)[:120])
    return vid


if __name__ == "__main__":
    # python pipeline\upload.py output\<name>   -> uploads final.mp4 with meta.json + thumbnail.jpg
    import os
    from common import genre_cfg
    d = sys.argv[1]; meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    upload(os.path.join(d, "final.mp4"), meta, os.path.join(d, "thumbnail.jpg"), genre_cfg(meta.get("genre")))
