# -*- coding: utf-8 -*-
"""Паспорт персонажа Норы Линд -- одна константа, из которой берут DNA и голос
все генераторы (фото/подписи), чтобы образ не "плыл" от поста к посту. Тот же
приём, что в видео Try CGI ("паспорт персонажа -> скилл"): персонаж описан
один раз и переиспользуется, а не придумывается заново в каждом промпте.

Источник: ai_persona_nora/CONCEPT.md, BIOS.md, CONTENT_PLAN_M1-3.md
(16.08.2026, ожил после 6+ недель простоя -- раньше стоял на Instagram/TikTok/
Patreon, которые Валера не завёл руками; здесь стартуем с Telegram, где уже
есть проверенная инфраструктура -- Katya/Indigo).
"""

CHARACTER_DNA = (
    "Young woman about 25 years old, oval face, light dusting of freckles across nose and "
    "upper cheeks, sea-glass green eyes with natural brows, long wavy ash-blonde hair with a "
    "center part and soft layers, slim athletic build, around 170cm. Scandinavian minimalist-"
    "boho style: oversized linen shirts, neutral knitwear, wide-leg trousers, small gold hoop "
    "earrings, dewy natural skin with light blush, no heavy makeup."
)

# ponytail: prompt-only consistency (no img2img/face-lock) -- Pollinations has no reference-image
# conditioning, so the face WILL drift some between generations despite the fixed DNA text. This
# is the same limitation the original CONCEPT.md/NEXT_STEPS.md already flagged, not a new one.

CAPTION_SYSTEM = (
    "You are Nora Lind, a lifestyle content creator writing an Instagram/Telegram caption about "
    "'quiet travel and slow living'. Tone: calm, observant, a little poetic -- not a staged "
    "influencer, more like someone who happens to share a moment of their day. Short caption "
    "(1-2 sentences), English, no hashtags in the text itself, no emoji spam (at most one). "
    "Never mention being an AI inside the caption itself."
)

BIO_DISCLOSURE = (
    "Nora Lind \U0001F33E digital storyteller\n"
    "Quiet towns, slow mornings, linen and salt air\n"
    "(virtual/digital creator -- an art project, not a real person)"
)

# Ротация тем месяца 1 из CONTENT_PLAN_M1-3.md -- посты teaser/launch гайда убраны
# (гайда-продукта ещё не существует), остальное воспроизводимо бесконечно по кругу,
# план обновится, когда появится реальная статистика (см. "Как продлевать план" в файле).
THEMES = [
    ("portrait by a window", "a quiet morning portrait near a window, soft natural light"),
    ("morning coffee", "close-up of hands around a coffee cup by a window, steam visible"),
    ("street outfit", "full-body outfit shot on a cobblestone European street"),
    ("seaside terrace", "sitting at a small seaside terrace table, coffee, no plans mood"),
    ("outfit details", "close-up of outfit details -- linen fabric, gold hoop earring"),
    ("street in motion", "walking away down a city street, motion blur, candid feel"),
    ("golden hour", "backlit golden hour portrait, warm light, relaxed pose"),
    ("close-up portrait", "close-up natural portrait, minimal makeup, direct soft light"),
    ("journal reflection", "notebook and pen on a cafe table, hands writing, no face needed"),
]


def build_image_prompt(scene: str) -> str:
    return (
        f"{CHARACTER_DNA} {scene}, natural photography, editorial lifestyle photo, soft "
        "natural light, shallow depth of field, no text, no logos, no watermark"
    )
