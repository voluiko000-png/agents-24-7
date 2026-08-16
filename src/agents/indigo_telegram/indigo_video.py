#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Раз в неделю — короткое вертикальное видео для тем, где видео реально
поднимает вовлечённость: розыгрыши/рефералки (нужно объяснить механику),
мини-игры (нужно показать геймплей), AI-инструменты (нужно показать результат).
Не для всех 50 — новостные/рефералки/каталоги обходятся фото, видео туда не
добавляет ценности и тратит время рендера зря.

16.08.2026 21:00, финально: голос + текст ВСЕГДА (референс -- канал Digital
Katya, 90% видео хорошие), текст в безопасной зоне, не за краем экрана.
7 разных кадров на тему (generate_topic_images.VARIANT_ANGLES), чередующийся
зум/панорама, xfade-перетекание (make_video.build), + hook/CTA-текст на
кадрах (make_video.caption_frames) + голос (make_video.add_voice). CTA дублируется
и в подписи Telegram-поста.

Запуск (Task Scheduler/GitHub Actions, 1 раз в неделю):
    python indigo_video.py
Офлайн-проверка:
    python indigo_video.py --demo
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE.parent / "Агент"))
from make_video import add_voice, build, caption_frames  # noqa: E402
from generate_topic_images import generate as generate_image, VARIANT_ANGLES, RATE_LIMIT_S  # noqa: E402

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
CFG = BASE / "channels.json"
VIDEO_IMAGES = BASE / "images" / "video"
VIDEOS = BASE / "videos"

# Ниши, где короткое видео реально поднимает вовлечённость — механика/геймплей/
# демонстрация результата нужно ПОКАЗАТЬ, не только описать текстом.
VIDEO_TOPIC_NAMES = {
    "Indigo Giveaway", "Indigo Referral Race",   # виральные механики — надо объяснить как участвовать
    "Indigo Clicker", "Indigo Trader Game",      # мини-игры — надо показать геймплей
    "Indigo Tools", "Indigo Design", "Indigo Copy",  # AI-боты по кредитам — надо показать результат
    "Indigo Quiz", "Indigo Trivia",              # квизы — видео-вопрос заходит лучше текста
}

CTA_BY_MECHANISM = {
    "viral_growth": "Invite friends in Indigo Hub",
    "tma_game": "Play now in Indigo Hub",
    "credit_bot": "Try it in Indigo Hub",
    "quiz_funnel": "Answer in Indigo Hub",
}


def load():
    return json.loads(CFG.read_text(encoding="utf-8"))


def ensure_variant_images(ch: dict, count: int = 7) -> list:
    """7 разных ракурсов на тему (кэшируется по каналу, портрет 1080x1920 --
    формат Katya-реелов). Валера 16.08: одно фото с Ken Burns не читается как
    видео, нужна реальная смена картинки между кадрами."""
    VIDEO_IMAGES.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        out = VIDEO_IMAGES / f"{ch['n']:02d}_{i:02d}.jpg"
        if not out.exists():
            angle = VARIANT_ANGLES[i % len(VARIANT_ANGLES)]
            img = generate_image(ch["niche"], angle=angle, width=1080, height=1920)
            img.save(out, quality=90)
            time.sleep(RATE_LIMIT_S)
        paths.append(str(out))
    return paths


def send_video(group_chat_id, ch: dict, video_path: Path, cta: str):
    caption = f"{ch['name']}\n\n{cta}"
    with open(video_path, "rb") as f:
        payload = {"chat_id": group_chat_id, "message_thread_id": ch["topic_id"], "caption": caption}
        r = requests.post(f"{API}/sendVideo", data=payload, files={"video": f}, timeout=120)
    j = r.json()
    if not j.get("ok"):
        print(f"[ERR] {ch['name']}: {j}")
    else:
        print(f"[OK] {ch['name']}: video posted")


def main():
    VIDEOS.mkdir(exist_ok=True)
    data = load()
    if not data["group_chat_id"]:
        print("Группа ещё не подключена")
        return
    targets = [c for c in data["channels"] if c["name"] in VIDEO_TOPIC_NAMES and c["topic_id"]]
    for ch in targets:
        out = VIDEOS / f"{ch['n']:02d}.mp4"
        cta = CTA_BY_MECHANISM.get(ch["mechanism"], "Join Indigo Hub")
        try:
            covers = ensure_variant_images(ch)
            captioned = caption_frames(covers, ch["name"], cta)
            try:
                dur = build(captioned, str(out))
                add_voice(str(out), ch, cta, dur)
                send_video(data["group_chat_id"], ch, out, cta)
            finally:
                for p in captioned:
                    os.remove(p)
        except Exception as e:
            print(f"[ERR] {ch['name']}: {e}")


def demo():
    """ponytail: no network/ffmpeg — checks the video-topic set matches real channel names in config."""
    data = load()
    names = {c["name"] for c in data["channels"]}
    missing = VIDEO_TOPIC_NAMES - names
    assert not missing, f"видео-темы не найдены в channels.json: {missing}"
    print(f"[demo] ok: {len(VIDEO_TOPIC_NAMES)} тем помечены под видео, все существуют в конфиге")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
