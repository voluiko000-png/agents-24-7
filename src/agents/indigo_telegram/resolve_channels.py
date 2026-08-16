#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Подхватывает группу по username и создаёт недостающие темы (Topics) —
через официальный Bot API (createForumTopic), без кликов, без риска для
аккаунта. Разным темам — разный цвет иконки (Валера просил различать на глаз).

Нужно один раз от Валеры: создать ОДНУ группу, включить Темы (Settings ->
Topics), добавить @Valera_AAA_Operator_bot админом с правом "Manage Topics".

    python resolve_channels.py
    python resolve_channels.py --demo   # ponytail: офлайн self-check
"""
import json
import os
import sys
from pathlib import Path

import requests

BASE = Path(__file__).parent
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"
CFG = BASE / "channels.json"

# Telegram's fixed forum-topic icon palette (only these 6 exist) — cycled per topic.
ICON_COLORS = [0x6FB9F0, 0xFFD67E, 0xCB86DB, 0x8EEE98, 0xFF93B2, 0xFB6F5F]


def resolve_group(username: str):
    r = requests.get(f"{API}/getChat", params={"chat_id": f"@{username}"}, timeout=15)
    j = r.json()
    return j["result"]["id"] if j.get("ok") else None


def create_topic(chat_id, name: str, color: int):
    r = requests.post(f"{API}/createForumTopic", json={
        "chat_id": chat_id, "name": name, "icon_color": color,
    }, timeout=15)
    j = r.json()
    return j["result"]["message_thread_id"] if j.get("ok") else None, j


def main():
    data = json.loads(CFG.read_text(encoding="utf-8"))
    if not data["group_chat_id"]:
        gid = resolve_group(data["group_username"])
        if not gid:
            print(f"Группа @{data['group_username']} ещё не найдена (не создана или бот не админ)")
            return
        data["group_chat_id"] = gid
        print(f"[OK] группа @{data['group_username']} -> {gid}")

    changed = True
    for i, ch in enumerate(data["channels"]):
        if ch["topic_id"]:
            continue
        color = ICON_COLORS[i % len(ICON_COLORS)]
        tid, raw = create_topic(data["group_chat_id"], ch["name"], color)
        if tid:
            ch["topic_id"] = tid
            print(f"[OK] тема '{ch['name']}' -> {tid}")
        else:
            print(f"[--] тема '{ch['name']}' не создана: {raw}")
    if changed:
        CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def demo():
    """ponytail: no network — checks config parses, colours cycle without index error."""
    data = json.loads(CFG.read_text(encoding="utf-8"))
    assert len(data["channels"]) == 50
    for i in range(15):
        assert ICON_COLORS[i % len(ICON_COLORS)] in ICON_COLORS
    print("[demo] ok: конфиг + цикл цветов иконок корректны")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
