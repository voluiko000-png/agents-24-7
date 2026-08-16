#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Генерирует по одному фото на тему (нишу) через Pollinations (Flux, бесплатно,
без ключа и без карты -- image.pollinations.ai/prompt/... отвечает анонимно) --
яркое, позитивное, фотографичное, без текста/логотипов (см. скилл
bright-product-style). Кэширует в images/{n:02d}.jpg -- idempotent, безопасно
перезапускать: уже готовые темы пропускает, генерирует только новые/недостающие.

16.08.2026: ушли с Cloudflare flux-1-schnell (Валера: "фото у нас косячены") --
тот же Flux, но через Pollinations даёт заметно чище картинку и не требует
токена вообще. Анонимный тариф -- 1 запрос/15с, поэтому пауза между вызовами.

Запуск разово (и повторно при добавлении новых тем):
    python generate_topic_images.py
Офлайн-проверка:
    python generate_topic_images.py --demo
"""
import json
import random
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

BASE = Path(__file__).parent
IMAGES = BASE / "images"
CFG = BASE / "channels.json"
POLLINATIONS_MODEL = "flux"
RATE_LIMIT_S = 16  # анонимный тариф Pollinations: 1 запрос/15с
W = H = 1024

# для видео (indigo_video.py) — каждый клип берёт свой ракурс, чтобы 10 картинок
# на одну тему реально отличались друг от друга, а не были вариациями одного кадра
VARIANT_ANGLES = [
    "extreme close-up", "wide establishing shot", "overhead flat lay",
    "hands interacting with objects", "side profile shot", "macro detail texture",
    "in motion action shot", "symbolic still life composition",
    "environmental wide context shot", "abstract artistic composition",
]


def build_prompt(niche: str, angle: str = None) -> str:
    scene = f"bright vibrant photographic scene symbolizing {niche}"
    if angle:
        scene += f", {angle}"
    return (
        f"{scene}, objects, hands, nature or abstract composition only, natural daylight, "
        "cheerful positive mood, real photo, high detail, shallow depth of field, no screens, "
        "no monitors, no signage, no books, no papers, no readable text or letters anywhere in "
        "the image, no logos, no watermark"
    )


def generate(niche: str, angle: str = None, width: int = None, height: int = None,
             attempt: int = 1) -> Image.Image:
    w, h = width or W, height or H
    seed = random.randint(1, 2_000_000_000)  # без seed Pollinations кэширует один и тот же кадр на промпт
    url = (
        f"https://image.pollinations.ai/prompt/{quote(build_prompt(niche, angle))}"
        f"?width={w}&height={h}&model={POLLINATIONS_MODEL}&seed={seed}"
        "&nologo=true&referrer=indigohub.local"
    )
    r = requests.get(url, timeout=90)
    if r.status_code in (429, 500) and attempt < 5:
        time.sleep(RATE_LIMIT_S * attempt)
        return generate(niche, angle, width, height, attempt + 1)
    r.raise_for_status()
    img = Image.open(BytesIO(r.content)).convert("RGB")
    if img.width / img.height > w / h:
        img = img.resize((int(img.width * h / img.height), h))
    else:
        img = img.resize((w, int(img.height * w / img.width)))
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


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
        time.sleep(RATE_LIMIT_S)
    print(f"\nDone. new={made} skipped(existing)={skipped} failed={failed}")


def demo():
    """ponytail: no network — checks prompt builder and dirs without calling the API."""
    p = build_prompt("test niche")
    assert "test niche" in p and "no text" in p
    IMAGES.mkdir(exist_ok=True)
    print("[demo] ok: prompt builder works, images/ dir ready")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
