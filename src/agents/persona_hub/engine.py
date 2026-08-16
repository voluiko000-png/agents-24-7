# -*- coding: utf-8 -*-
"""Общий движок для AI-персон (фото + подпись + постинг в Telegram-канал),
параметризован модулем персонажа. Используется poster.py для персон 2 и 3
(Мия, Лео) -- та же механика, что уже проверена вживую на Норе
(nora_persona/nora_poster.py), вынесена сюда, чтобы не копипастить файл
на каждую новую персону.
"""
import json
import os
import random
import sys
import time
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE.parent / "indigo_telegram"))
from llm import ask  # noqa: E402

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
POLLINATIONS_MODEL = "flux"
W, H = 1024, 1280


def load(cfg_path: Path):
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def save(cfg_path: Path, data):
    cfg_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_chat_id(cfg_path: Path, data):
    if data.get("chat_id"):
        return data["chat_id"]
    if not data.get("channel_username"):
        return None
    r = requests.get(f"{API}/getChat", params={"chat_id": f"@{data['channel_username']}"}, timeout=15)
    j = r.json()
    if j.get("ok"):
        data["chat_id"] = j["result"]["id"]
        save(cfg_path, data)
        return data["chat_id"]
    print(f"[ERR] канал @{data['channel_username']} не найден: {j}")
    return None


def generate_photo(prompt: str) -> Image.Image:
    seed = random.randint(1, 2_000_000_000)
    url = (
        f"https://image.pollinations.ai/prompt/{quote(prompt)}"
        f"?width={W}&height={H}&model={POLLINATIONS_MODEL}&seed={seed}"
        "&nologo=true&referrer=personahub.local"
    )
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return Image.open(BytesIO(r.content)).convert("RGB")


def generate_caption(caption_system: str, topic: str, scene: str) -> str:
    text = ask(f"Write the caption. Scene: {scene}. Loose theme: {topic}.",
               system=caption_system, max_tokens=100)
    return (text or "").strip()


def send_photo(chat_id, img: Image.Image, caption: str) -> bool:
    buf = BytesIO()
    img.save(buf, "JPEG", quality=92)
    buf.seek(0)
    for attempt in range(2):
        r = requests.post(
            f"{API}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption[:1024]},
            files={"photo": ("persona.jpg", buf, "image/jpeg")},
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
    return False


def run(persona_module, cfg_path: Path):
    """persona_module needs: CHARACTER_DNA, CAPTION_SYSTEM, THEMES,
    build_image_prompt(scene)."""
    data = load(cfg_path)
    chat_id = resolve_chat_id(cfg_path, data)
    if not chat_id:
        print("Канал ещё не подключён -- см. channel_username в конфиге персоны")
        return
    topic, scene = persona_module.THEMES[data["post_index"] % len(persona_module.THEMES)]
    try:
        img = generate_photo(persona_module.build_image_prompt(scene))
        caption = generate_caption(persona_module.CAPTION_SYSTEM, topic, scene)
        if not caption:
            print("[WARN] подпись не сгенерировалась (LLM-каскад лёг), публикую без текста")
        if send_photo(chat_id, img, caption):
            print(f"[OK] опубликовано: {topic}")
            data["post_index"] += 1
            save(cfg_path, data)
    except Exception as e:
        print(f"[ERR] {e}")
