#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Кросс-постинг того же поста (текст+фото), что ушёл в Telegram, на Bluesky
и Mastodon. Ключи — только из GitHub Secrets (env), не в коде.

ponytail: не зеркалит все 50 тем х 2 раза в день — один аккаунт Bluesky/
Mastodon получил бы 100 постов подряд в ОДНОЙ ленте (в отличие от Telegram,
где у каждой темы своя аудитория) — это спам-паттерн, который сам себя
банит. cross_post() зовётся только для небольшой скользящей выборки за
цикл, см. CROSS_POST_SAMPLE и cross_post_slice() в indigo_poster.py.

Tumblr/Pinterest: ключи ещё не полные (Tumblr — нужен разовый OAuth1.0a
user-token шаг, Pinterest — ждёт одобрения Trial access у площадки), сюда
добавятся, когда придут остальные данные.

Офлайн-проверка:
    python cross_poster.py --demo
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE", "")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD", "")
BLUESKY_PDS = "https://bsky.social"

MASTODON_INSTANCE = os.environ.get("MASTODON_INSTANCE", "https://mastodon.social")
MASTODON_ACCESS_TOKEN = os.environ.get("MASTODON_ACCESS_TOKEN", "")


def post_bluesky(text: str, image_path: Optional[Path]) -> bool:
    if not (BLUESKY_HANDLE and BLUESKY_APP_PASSWORD):
        return False
    try:
        session = requests.post(
            f"{BLUESKY_PDS}/xrpc/com.atproto.server.createSession",
            json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD},
            timeout=20,
        ).json()
        jwt, did = session["accessJwt"], session["did"]
        headers = {"Authorization": f"Bearer {jwt}"}

        embed = None
        if image_path and image_path.exists():
            blob_resp = requests.post(
                f"{BLUESKY_PDS}/xrpc/com.atproto.repo.uploadBlob",
                headers={**headers, "Content-Type": "image/jpeg"},
                data=image_path.read_bytes(),
                timeout=30,
            ).json()
            if "blob" in blob_resp:
                embed = {
                    "$type": "app.bsky.embed.images",
                    "images": [{"alt": text[:100], "image": blob_resp["blob"]}],
                }

        record = {
            "$type": "app.bsky.feed.post",
            "text": text[:300],
            "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if embed:
            record["embed"] = embed

        r = requests.post(
            f"{BLUESKY_PDS}/xrpc/com.atproto.repo.createRecord",
            headers=headers,
            json={"repo": did, "collection": "app.bsky.feed.post", "record": record},
            timeout=20,
        )
        if not r.ok:
            print(f"[ERR] bluesky: {r.text[:300]}")
        return r.ok
    except Exception as e:
        print(f"[ERR] bluesky: {e}")
        return False


def post_mastodon(text: str, image_path: Optional[Path]) -> bool:
    if not MASTODON_ACCESS_TOKEN:
        return False
    headers = {"Authorization": f"Bearer {MASTODON_ACCESS_TOKEN}"}
    try:
        media_ids = []
        if image_path and image_path.exists():
            with open(image_path, "rb") as f:
                r = requests.post(
                    f"{MASTODON_INSTANCE}/api/v2/media",
                    headers=headers,
                    files={"file": f},
                    timeout=30,
                )
            if r.ok:
                media_ids.append(r.json()["id"])

        data = {"status": text[:500]}
        if media_ids:
            data["media_ids[]"] = media_ids
        r = requests.post(f"{MASTODON_INSTANCE}/api/v1/statuses", headers=headers, data=data, timeout=20)
        if not r.ok and media_ids:
            # media still processing server-side ("not finished processing") — retry text-only
            r = requests.post(
                f"{MASTODON_INSTANCE}/api/v1/statuses", headers=headers, data={"status": text[:500]}, timeout=20
            )
        if not r.ok:
            print(f"[ERR] mastodon: {r.text[:300]}")
        return r.ok
    except Exception as e:
        print(f"[ERR] mastodon: {e}")
        return False


def cross_post(text: str, image_path: Optional[Path]) -> None:
    if post_bluesky(text, image_path):
        print("[OK] bluesky: posted")
    if post_mastodon(text, image_path):
        print("[OK] mastodon: posted")


def demo():
    """ponytail: no network — checks both posters no-op cleanly without creds."""
    assert post_bluesky("test", None) is False
    assert post_mastodon("test", None) is False
    print("[demo] ok: cross_poster no-ops safely without credentials")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else print("standalone run needs text/image — call cross_post() from indigo_poster.py")
