#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генерирует по одному фото на тему (нишу) через Cloudflare Flux (бесплатно) —
яркое, позитивное, фотографичное, без текста/логотипов (см. скилл
bright-product-style). Кэширует в images/{n:02d}.jpg — idempotent, безопасно
перезапускать: уже готовые темы пропускает, генерирует только новые/недостающие.

Запуск разово (и повторно при добавлении новых тем):
    python generate_topic_images.py
Офлайн-проверка:
    python generate_topic_images.py --demo
"""
import base64
import os
import json
import sys
import time
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image

BASE = Path(__file__).parent
IMAGES = BASE / "images"
CFG = BASE / "channels.json"
CF_ACCOUNT_ID = "712103fd9046a3d9f5db3aba677aa20b"
CF_TOKEN = os.environ["CLOUDFLARE_API_KEY"]
CF_IMAGE_MODEL = "@cf/black-forest-labs/flux-1-schnell"
W = H = 1024


def build_prompt(niche: str) -> str:
    return (
        f"bright vibrant photographic close-up scene symbolizing {niche}, objects, hands, nature "
        "or abstract composition only, natural daylight, cheerful positive mood, real photo, high "
        "detail, shallow depth of field, no screens, no monitors, no signage, no books, no papers, "
        "no readable text or letters anywhere in the image, no logos, no watermark"
    )


def generate(niche: str, attempt: int = 1) -> Image.Image:
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{CF_IMAGE_MODEL}"
    r = requests.post(
        url,
        json={"prompt": build_prompt(niche)},
        headers={"Authorization": f"Bearer {CF_TOKEN}"},
        timeout=60,
    )
    if r.status_code == 429 and attempt < 5:
        time.sleep(10 * attempt)
        return generate(niche, attempt + 1)
    r.raise_for_status()
    raw = base64.b64decode(r.json()["result"]["image"])
    img = Image.open(BytesIO(raw)).convert("RGB")
    if img.width / img.height > 1:
        img = img.resize((int(img.width * H / img.height), H))
    else:
        img = img.resize((W, int(img.height * W / img.width)))
    left, top = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((left, top, left + W, top + H))


def main():
    IMAGES.mkdir(exist_ok=True)
    data = json.loads(CFG.read_text(encoding="utf-8"))
    made = skipped = failed = 0
    for ch in data["channels"]:
        out = IMAGES / f"{ch['n']:02d}.jpg"
        if out.exists():
            skipped += 1
            continue
        try:
            img = generate(ch["niche"])
            img.save(out, quality=90)
            made += 1
            print(f"[OK] {ch['name']}: {out.name}")
        except Exception as e:
            failed += 1
            print(f"[ERR] {ch['name']}: {e}")
        time.sleep(1)
    print(f"\nDone. new={made} skipped(existing)={skipped} failed={failed}")


def demo():
    """ponytail: no network — checks prompt builder and dirs without calling the API."""
    p = build_prompt("test niche")
    assert "test niche" in p and "no text" in p
    IMAGES.mkdir(exist_ok=True)
    print("[demo] ok: prompt builder works, images/ dir ready")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
