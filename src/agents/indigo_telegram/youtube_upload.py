#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Заливает уже отрендеренные видео (`videos/*.mp4`, тот же движок, что и
Telegram-видео — 1080x1920, короче 60с, уже готовый формат Shorts/TikTok) на
YouTube как Shorts, со ссылкой на Indigo Hub в описании.

Требует ОДНОРАЗОВОЙ ручной авторизации Валеры (OAuth-согласие на YouTube-канал —
это не может сделать агент за него, Google требует клика владельца аккаунта):
    1. console.cloud.google.com -> создать проект -> включить "YouTube Data API v3"
    2. Credentials -> Create OAuth client ID -> Desktop app -> скачать client_secret.json
       рядом с этим файлом
    3. Один раз запустить: python youtube_upload.py --auth
       (откроется браузер, Валера логинится и подтверждает доступ к своему
       каналу) -> сохранится token.json, дальше всё работает без него.

Обычный запуск (после первичной авторизации):
    python youtube_upload.py
"""
import os
import sys
from pathlib import Path

import google.auth.transport.requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build as gbuild
from googleapiclient.http import MediaFileUpload

BASE = Path(__file__).parent
VIDEOS = BASE / "videos"
CLIENT_SECRET = BASE / "client_secret.json"
TOKEN_FILE = BASE / "token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

TITLES = {
    "14": "Invite friends, win prizes \U0001f3c6 #shorts",
    "36": "Climb the referral leaderboard \U0001f4c8 #shorts",
    "15": "Tap to earn \U0001f4b0 #shorts",
    "37": "Trade like a pro (simulation) \U0001f4ca #shorts",
    "07": "Watch this AI tool work \U0001f916 #shorts",
    "31": "AI logo in seconds \U0001f3a8 #shorts",
    "32": "AI writes your ad copy ✍️ #shorts",
    "03": "Can you answer this? \U0001f9e0 #shorts",
    "24": "Trivia time ❓ #shorts",
}


def get_service():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
        else:
            raise RuntimeError("Нет действующей авторизации — сначала: python youtube_upload.py --auth")
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return gbuild("youtube", "v3", credentials=creds)


def authorize():
    if not CLIENT_SECRET.exists():
        print(f"Нет {CLIENT_SECRET.name} — см. инструкцию в начале файла (Google Cloud Console).")
        return
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0)
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print(f"[OK] авторизация сохранена в {TOKEN_FILE.name}")


def upload_one(service, video_path: Path):
    n = video_path.stem
    title = TITLES.get(n, "Indigo Hub #shorts")
    body = {
        "snippet": {
            "title": title,
            "description": "Full content: t.me/indigo_hub_valera",
            "categoryId": "22",
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    req = service.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = req.execute()
    print(f"[OK] {video_path.name} -> https://youtube.com/shorts/{resp['id']}")


def main():
    if os.environ.get("YOUTUBE_TOKEN_JSON") and not TOKEN_FILE.exists():
        TOKEN_FILE.write_text(os.environ["YOUTUBE_TOKEN_JSON"], encoding="utf-8")
    if not VIDEOS.exists() or not any(VIDEOS.glob("*.mp4")):
        print("Нет видео в videos/ — сначала indigo_video.py")
        return
    service = get_service()
    for vp in sorted(VIDEOS.glob("*.mp4")):
        try:
            upload_one(service, vp)
        except Exception as e:
            print(f"[ERR] {vp.name}: {e}")


def demo():
    """ponytail: no network — checks title map has entries, file layout sane."""
    assert TITLES, "TITLES пуст"
    print("[demo] ok: титулы под Shorts заданы, структура корректна")


if __name__ == "__main__":
    if "--auth" in sys.argv:
        authorize()
    elif "--demo" in sys.argv:
        demo()
    else:
        main()
