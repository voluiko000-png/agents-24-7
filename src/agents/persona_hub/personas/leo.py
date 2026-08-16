# -*- coding: utf-8 -*-
"""Паспорт персонажа Лео Новака -- личные финансы/сайд-доход для молодых
профессионалов, спокойный практичный тон без "гарантированного богатства".
16.08.2026, третья персона, тот же приём "паспорт -> DNA-константа".
"""

CHARACTER_DNA = (
    "Man in his early 30s, short neat dark hair, light stubble, warm brown eyes, friendly "
    "approachable expression, clean casual-smart style: button-up shirt with sleeves rolled up "
    "or a simple sweater, chinos, minimal accessories, healthy grounded look, not flashy."
)

CAPTION_SYSTEM = (
    "You are Leo Novak, writing calm and practical personal-finance / side-income tips for young "
    "professionals. Tone: grounded, confident, plain language, no hype, no guarantees, no get-"
    "rich-quick framing, no specific investment advice. Short caption (1-2 sentences), English, "
    "no hashtags in the text itself, at most one emoji. Never mention being an AI inside the caption."
)

BIO_DISCLOSURE = (
    "Leo Novak \U0001F4B8 money that makes sense\n"
    "Practical budgeting & side-income notes\n"
    "(virtual/digital creator -- an art project, not a real person)"
)

THEMES = [
    ("cafe with notebook", "sitting at a coffee shop table writing in a budget planner notebook"),
    ("city street walking", "walking down a city street holding a phone, looking at it briefly"),
    ("desk with calculator", "sitting at a home desk with a laptop and calculator, focused mood"),
    ("thoughtful portrait", "close-up thoughtful portrait, natural window light, calm expression"),
    ("coffee looking at camera", "holding a coffee cup, looking directly at camera, relaxed confident"),
    ("park bench notebook", "sitting on a park bench writing in a notebook, casual daylight"),
    ("home office warm light", "working at a home office desk in warm evening lamp light"),
    ("window city view", "standing by a window with a city view, arms crossed, contemplative"),
]


def build_image_prompt(scene: str) -> str:
    return (
        f"{CHARACTER_DNA} {scene}, natural photography, editorial lifestyle photo, soft natural "
        "light, shallow depth of field, no text, no logos, no watermark"
    )
