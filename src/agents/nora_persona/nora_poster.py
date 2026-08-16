#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Постинг для Норы Линд (AI lifestyle-персонаж, ai_persona_nora/CONCEPT.md) --
одно фото + подпись в её Telegram-канал, тема берётся по кругу из nora.THEMES.

Нужно один раз от Валеры: создать Telegram-канал, добавить туда
@Valera_AAA_Operator_bot админом (тот же бот, что у Indigo/Katya), вписать
@username канала в nora_config.json -> channel_username.

Запуск (Task Scheduler, 2-3 раза в неделю -- ритм из CONTENT_PLAN_M1-3.md):
    python nora_poster.py
Офлайн-проверка:
    python nora_poster.py --demo
"""
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE.parent / "indigo_telegram"))
from llm import ask  # noqa: E402
from nora import CAPTION_SYSTEM, THEMES, build_image_prompt  # noqa: E402

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
CFG = BASE / "nora_config.json"
POLLINATIONS_MODEL = "flux"
W, H = 1024, 1280


def load():
    return json.loads(CFG.read_text(encoding="utf-8"))


def save(data):
    CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_chat_id(data):
    if data.get("chat_id"):
        return data["chat_id"]
    if not data.get("channel_username"):
        return None
    r = requests.get(f"{API}/getChat", params={"chat_id": f"@{data['channel_username']}"}, timeout=15)
    j = r.json()
    if j.get("ok"):
        data["chat_id"] = j["result"]["id"]
        save(data)
        return data["chat_id"]
    print(f"[ERR] канал @{data['channel_username']} не найден (не создан или бот не админ): {j}")
    return None


def generate_photo(scene: str) -> Image.Image:
    import random
    seed = random.randint(1, 2_000_000_000)
    url = (
        f"https://image.pollinations.ai/prompt/{quote(build_image_prompt(scene))}"
        f"?width={W}&height={H}&model={POLLINATIONS_MODEL}&seed={seed}"
        "&nologo=true&referrer=noralind.local"
    )
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGB")


def generate_caption(topic: str, scene: str) -> str:
    text = ask(
        f"Write the caption. Scene: {scene}. Loose theme: {topic}.",
        system=CAPTION_SYSTEM, max_tokens=100,
    )
    return (text or "").strip()


def send_photo(chat_id, img: Image.Image, caption: str):
    buf = BytesIO()
    img.save(buf, "JPEG", quality=92)
    buf.seek(0)
    for attempt in range(2):
        r = requests.post(
            f"{API}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption[:1024]},
            files={"photo": ("nora.jpg", buf, "image/jpeg")},
            timeout=60,
        )
        j = r.json()
        if j.get("ok"):
            return True
        if j.get("error_code") == 429 and attempt == 0:
            wait = j.get("parameters", {}).get("retry_after", 5) + 1
            print(f"[WAIT] flood limit, retrying in {wait}s")
            time.sleep(wait)
            buf.seek(0)
            continue
        print(f"[ERR] {j}")
        return False


def main():
    data = load()
    chat_id = resolve_chat_id(data)
    if not chat_id:
        print("Канал ещё не подключён -- см. docstring: создать канал, добавить бота, "
              "вписать channel_username в nora_config.json")
        return
    topic, scene = THEMES[data["post_index"] % len(THEMES)]
    try:
        img = generate_photo(scene)
        caption = generate_caption(topic, scene)
        if not caption:
            print("[WARN] подпись не сгенерировалась (LLM-каскад лёг), публикую без текста")
        if send_photo(chat_id, img, caption):
            print(f"[OK] опубликовано: {topic}")
            data["post_index"] += 1
            save(data)
    except Exception as e:
        print(f"[ERR] {e}")


def demo():
    """ponytail: no network -- checks themes/config are well-formed and prompts build."""
    data = load()
    assert "channel_username" in data and "post_index" in data
    assert len(THEMES) >= 5
    for topic, scene in THEMES:
        p = build_image_prompt(scene)
        assert topic and scene and len(p) > 20
    print(f"[demo] ok: {len(THEMES)} тем, конфиг корректен")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
