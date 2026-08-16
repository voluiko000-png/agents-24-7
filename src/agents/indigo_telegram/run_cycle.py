#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Один прогон кластера: сначала подхватить новые channel_id (если Валера
создал ещё каналы), потом опубликовать посты в уже подключённые. Это и есть
задача для Task Scheduler — 2 раза в день."""
import resolve_channels
import generate_topic_images
import indigo_poster

if __name__ == "__main__":
    resolve_channels.main()
    generate_topic_images.main()  # idempotent — генерирует фото только для новых тем
    indigo_poster.main()
