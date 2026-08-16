#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ежедневный постинг в темы группы Indigo Hub (16.08.2026, v3 — 15 разных
бизнес-механик, не переупаковка категорий Katya). Для каждой темы с
заполненным topic_id пишет 1 пост через бесплатный llm.py-каскад и
публикует через @Valera_AAA_Operator_bot в нужную тему (message_thread_id)
той же группы.

Запуск (Task Scheduler, 2 раза в день):
    python indigo_poster.py
Офлайн-проверка:
    python indigo_poster.py --demo
"""
import json
import os
import sys
from pathlib import Path

import requests

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
from llm import ask  # noqa: E402

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
CFG = BASE / "channels.json"
IMAGES = BASE / "images"

STYLE_GUIDE = (
    "House style, follow strictly like a top-performing Telegram channel writer: "
    "line 1 must be a scroll-stopping hook that works alone in a collapsed preview (no greeting, "
    "no 'in today's world', no throat-clearing) — a sharp claim, number, or question. "
    "Short punchy lines (1-2 sentences each), blank line between them, native Telegram feel, not "
    "a corporate blog paragraph. Use *one* bold phrase for the key idea (Telegram markdown: *text*), "
    "at most 1-2 emoji used as real visual anchors, never as decoration or one per line. Be concrete "
    "— specific numbers, examples, named mechanisms — never vague filler ('unlock', 'game-changing', "
    "'in today's fast-paced world', 'dive into'). End with exactly ONE clear next action, not a stack "
    "of asks. Sound like a sharp human who knows this niche, not an AI assistant. "
)

PROMPTS = {
    "cpa_referral": (
        "Write ONE short Telegram post (2-3 sentences, English) sharing a genuinely useful, "
        "specific tip in the niche '{niche}'. Helpful and concrete, not spammy, no fake links."
    ),
    "high_ticket_referral": (
        "Write ONE short, professional Telegram post (English) with a genuinely useful insight "
        "for someone evaluating options in '{niche}'. Credible, no hype, no fabricated stats or "
        "guarantees, no financial/legal/investment advice — just a helpful framing question or tip."
    ),
    "paid_club": (
        "Write ONE short Telegram post (English) previewing a genuinely useful resource/tip in "
        "the niche '{niche}' to build curiosity for a paid closed area. Give real value, tease more."
    ),
    "quiz_funnel": (
        "Write ONE short fun trivia/quiz question (English) related to '{niche}', with the "
        "answer teased below a spoiler line 'Answer:'. Keep it light and shareable."
    ),
    "paid_pin": (
        "Write ONE short Telegram post (English) with a practical, useful tip related to "
        "'{niche}'. Genuinely useful, community-tone, not an ad."
    ),
    "stars_product": (
        "Write ONE short, upbeat Telegram post (2-3 sentences, English) promoting a digital "
        "bundle in the niche '{niche}'. Bright, positive tone, end with genuine value, not just 'buy now'."
    ),
    "credit_bot": (
        "Write ONE short Telegram post (English) showcasing what the AI tool bot can do for "
        "'{niche}'. Concrete example of output, inviting but not pushy."
    ),
    "utility_free": (
        "Write ONE short Telegram post (English) with a quick practical tip using a free "
        "utility related to '{niche}'. Genuinely useful, no sales pitch."
    ),
    "content_aggregator": (
        "Write ONE short, neutral news-digest-style Telegram post (English) summarizing a "
        "general, well-known recent trend in '{niche}'. Factual tone, no speculation, no financial "
        "advice or price predictions — education and awareness only."
    ),
    "viral_growth": (
        "Write ONE short, exciting Telegram post (English) inviting people to join a giveaway/contest "
        "themed around '{niche}'. Fun, high-energy, clear simple call to action to invite friends."
    ),
    "tma_game": (
        "Write ONE short, playful Telegram post (English) hyping up a tap/clicker mini-game themed "
        "around '{niche}'. Fun, casual gaming tone, inviting people to try it."
    ),
}


def load():
    return json.loads(CFG.read_text(encoding="utf-8"))


def build_post(ch: dict) -> str:
    tmpl = PROMPTS[ch["mechanism"]]
    text = ask(STYLE_GUIDE + tmpl.format(niche=ch["niche"]), max_tokens=220)
    return (text or "").strip()


def send(group_chat_id, ch: dict, text: str):
    img_path = IMAGES / f"{ch['n']:02d}.jpg"
    if img_path.exists():
        with open(img_path, "rb") as f:
            payload = {"chat_id": group_chat_id, "message_thread_id": ch["topic_id"], "caption": text[:1024]}
            r = requests.post(f"{API}/sendPhoto", data=payload, files={"photo": f}, timeout=60)
    else:
        payload = {"chat_id": group_chat_id, "message_thread_id": ch["topic_id"], "text": text}
        r = requests.post(f"{API}/sendMessage", data=payload, timeout=30)
    j = r.json()
    if not j.get("ok"):
        print(f"[ERR] {ch['name']}: {j}")
    else:
        print(f"[OK] {ch['name']}: posted{' (photo)' if img_path.exists() else ''}")


def main():
    data = load()
    if not data["group_chat_id"]:
        print("Группа ещё не подключена — сначала resolve_channels.py")
        return
    channels = [c for c in data["channels"] if c["topic_id"]]
    if not channels:
        print("Группа подключена, но ни одна тема ещё не создана — resolve_channels.py")
        return
    for ch in channels:
        try:
            text = build_post(ch)
            if text:
                send(data["group_chat_id"], ch, text)
        except Exception as e:
            print(f"[ERR] {ch['name']}: {e}")


def demo():
    """ponytail: no network — checks prompt templates cover every mechanism in config."""
    data = load()
    mechanisms = {c["mechanism"] for c in data["channels"]}
    assert mechanisms <= set(PROMPTS), f"нет шаблона поста для {mechanisms - set(PROMPTS)}"
    print(f"[demo] ok: {len(data['channels'])} тем, все механики покрыты шаблонами постов")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
