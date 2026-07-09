#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
DEFAULT_TOKEN = Path("/Users/jaitoor/Downloads/april-tools-day-segments/youtube/token.json")
DEFAULT_CLIENT_SECRET = Path("/Users/jaitoor/Downloads/april-tools-day-segments/youtube/client_secret.json")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_path(path: str) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return repo_root() / p


def get_youtube():
    token_path = Path(os.environ.get("YOUTUBE_TOKEN_PATH", DEFAULT_TOKEN))
    client_secret_path = Path(os.environ.get("YOUTUBE_CLIENT_SECRET_PATH", DEFAULT_CLIENT_SECRET))

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, entry: dict) -> str:
    video_path = resolve_path(entry["file"])
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": entry["title"],
                "description": entry["description"],
                "tags": entry.get("tags", []),
                "categoryId": "28",
            },
            "status": {
                "privacyStatus": entry.get("privacy", "private"),
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(str(video_path), chunksize=-1, resumable=True),
    )

    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]


def set_thumbnail(youtube, video_id: str, thumbnail_path: str) -> None:
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(str(resolve_path(thumbnail_path))),
    ).execute()


def upload_caption(youtube, video_id: str, caption_path: str) -> bool:
    path = resolve_path(caption_path)
    if not path.exists():
        return False
    try:
        youtube.captions().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "language": "en",
                    "name": "English",
                    "isDraft": False,
                }
            },
            media_body=MediaFileUpload(str(path), mimetype="application/octet-stream"),
        ).execute()
        return True
    except HttpError as error:
        print(f"caption upload skipped for {video_id}: {error}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--results", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip-slug", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest_path = resolve_path(args.manifest)
    entries = json.loads(manifest_path.read_text())
    if args.skip_slug:
        entries = [entry for entry in entries if entry["slug"] not in set(args.skip_slug)]
    if args.limit:
        entries = entries[: args.limit]

    if args.dry_run:
        for entry in entries:
            print(f"DRY RUN: {entry['title']} -> {entry['file']}")
        return

    youtube = get_youtube()
    results = []

    for entry in entries:
        video_id = upload_video(youtube, entry)
        set_thumbnail(youtube, video_id, entry["thumbnail"])
        caption_uploaded = False
        if entry.get("caption"):
            caption_uploaded = upload_caption(youtube, video_id, entry["caption"])
        result = {
            "slug": entry["slug"],
            "title": entry["title"],
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "privacy": entry.get("privacy", "private"),
            "caption_uploaded": caption_uploaded,
        }
        print(json.dumps(result))
        results.append(result)
        results_path = resolve_path(args.results)
        results_path.write_text(json.dumps(results, indent=2) + "\n")



if __name__ == "__main__":
    main()
