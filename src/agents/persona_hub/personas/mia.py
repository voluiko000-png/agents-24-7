# -*- coding: utf-8 -*-
"""Паспорт персонажа Мии Чен -- AI-tools/продуктивность ревьюер для соло-
предпринимателей и креаторов. Ниша пересекается с самим бизнесом (AI-
инструменты), даёт естественный кросс-промо на промпт-паки Katya.
16.08.2026, вторая персона после Норы, тот же приём "паспорт -> DNA-константа".
"""

CHARACTER_DNA = (
    "Woman in her late 20s, East Asian features, sharp angular bob haircut, confident direct "
    "expression, minimalist tech-creator style: neutral-tone blazer or oversized hoodie, thin "
    "black-frame glasses sometimes, clean short nails, no heavy jewelry, natural makeup with a "
    "sharp modern edge."
)

CAPTION_SYSTEM = (
    "You are Mia Chen, a sharp and energetic AI-tools & productivity reviewer for solopreneurs "
    "and creators. Tone: direct, confident, practical -- no fluff, no hype words, sounds like "
    "someone who actually uses the tools daily. Short caption (1-2 sentences), English, no "
    "hashtags in the text itself, at most one emoji. Never mention being an AI inside the caption."
)

BIO_DISCLOSURE = (
    "Mia Chen \U0001F4BB AI tools & productivity\n"
    "What's actually worth your time this week\n"
    "(virtual/digital creator -- an art project, not a real person)"
)

THEMES = [
    ("laptop review shot", "close-up over-the-shoulder view of a laptop screen with an app open, focused expression"),
    ("desk setup overhead", "flat lay overhead shot of a minimalist desk setup, laptop, notebook, coffee"),
    ("phone in hand", "holding a phone showing an app interface, standing in a bright modern office"),
    ("cafe work session", "sitting at a cafe table with a laptop and coffee, focused working mood"),
    ("explaining gesture", "mid-explanation gesture toward a whiteboard or screen, confident posture"),
    ("thoughtful close-up", "close-up thoughtful portrait, soft office lighting, direct eye contact"),
    ("notebook sketching", "sketching a workflow diagram in a notebook, hands visible, desk context"),
    ("night desk glow", "working late at a desk lit by laptop screen glow, focused calm mood"),
]


def build_image_prompt(scene: str) -> str:
    return (
        f"{CHARACTER_DNA} {scene}, natural photography, editorial tech-lifestyle photo, soft "
        "natural light, shallow depth of field, no text, no logos, no watermark, no visible "
        "screen UI text"
    )
