#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Постинг для персон 2/3 (Мия, Лео) -- один движок (engine.py), персонаж
задаётся аргументом. Нора живёт отдельно в nora_persona/ (запущена и
протестирована первой, не трогаем работающий пайплайн).

Нужно один раз от Валеры на каждую новую персону: создать Telegram-канал
(или это делает telegram_create_channel.py с личного аккаунта), добавить
бота админом, вписать @username в personas/<name>_config.json.

    python poster.py mia
    python poster.py leo
    python poster.py mia --demo
"""
import importlib
import sys
from pathlib import Path

import engine

BASE = Path(__file__).parent


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    name = sys.argv[1]
    persona = importlib.import_module(f"personas.{name}")
    cfg_path = BASE / "personas" / f"{name}_config.json"
    if "--demo" in sys.argv:
        demo(persona, cfg_path)
    else:
        engine.run(persona, cfg_path)


def demo(persona, cfg_path):
    """ponytail: no network -- checks persona module + config are well-formed."""
    data = engine.load(cfg_path)
    assert "channel_username" in data and "post_index" in data
    assert len(persona.THEMES) >= 5
    for topic, scene in persona.THEMES:
        p = persona.build_image_prompt(scene)
        assert topic and scene and len(p) > 20
    print(f"[demo] ok: {len(persona.THEMES)} тем, конфиг корректен")


if __name__ == "__main__":
    sys.path.insert(0, str(BASE))
    main()
