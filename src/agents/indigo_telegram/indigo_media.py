#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Галерея (4 разных фото) + narrated видео (~15с, Ken Burns + edge-tts +
CTA-бэнд) для одного поста -- порт формата Katya (`Агент/digital-product-agent/
post_telegram.py`, `build_gallery`/`build_video`/`post_media`/`send_media_group`),
Валера 16.08.2026: "в посте должно быть четыре разных фотографии и одно видео,
такое как digital Katya, с озвучкой" -- не одна закэшированная фотка на канал
навсегда (старый баг indigo_poster.py: одно фото, генерится один раз и
переиспользуется во всех постах, отсюда "три поста с одной фотографии").

Фото -- Pollinations (те же generate()/VARIANT_ANGLES, что уже используются
для еженедельного видео), не Cloudflare (общий аккаунт с другими проектами
упирается в 429, см. commit фикса digital-product-agent/post_telegram.py).
"""
import asyncio
import os
import re
import subprocess
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

from generate_topic_images import generate as generate_image, VARIANT_ANGLES
from llm import ask

BASE = Path(__file__).parent
TMP = BASE / "_media"
VIDEO_SECONDS = 15
VOICE = "en-US-AndrewNeural"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "arial.ttf",
]
CYRILLIC_RE = re.compile(r"[а-яА-ЯёЁ]")
GALLERY_SIZE = 4


def _font(size):
    for candidate in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_width):
    words, lines, current = text.split(), [], []
    for word in words:
        current.append(word)
        if draw.textbbox((0, 0), " ".join(current), font=font)[2] > max_width:
            current.pop()
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


# Reels/Shorts/TikTok UI (like/comment/share, caption, profile) covers the
# true top/bottom edges on every platform -- text flush to y=0 or y=height
# reads as "cut off" even though it's technically inside the frame. Valera
# 16.08.2026 21:00, referencing the Digital Katya channel: keep voice+text
# everywhere, just raise it into this safe zone instead of removing it.
SAFE_TOP = 0.07
SAFE_BOTTOM = 0.14


def overlay_band(img, text, position="bottom"):
    """Video-only text band (gallery stills stay clean) -- opening purpose line
    + persistent CTA band, same as digital-product-agent's post_telegram.py.
    Bands sit inside the safe zone, not flush to the frame edge."""
    img = img.convert("RGB")
    width, height = img.size
    draw = ImageDraw.Draw(img)
    font = _font(int(height / 16))
    lines = _wrap(draw, text, font, width - 60)

    line_height = font.size + 8
    band_h = len(lines) * line_height + 40
    band_top = (int(height * SAFE_TOP) if position == "top"
                else height - band_h - int(height * SAFE_BOTTOM))

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, band_top, width, band_top + band_h], fill=(0, 0, 0, 175))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        x, y = 30, band_top + 20 + i * line_height
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
    return img


def build_gallery(ch: dict, tag: str) -> list:
    """4 разных ракурсов на тему канала (Pollinations, VARIANT_ANGLES[:4]).
    Возвращает None, если хоть один кадр не удался -- чистый fallback на
    один статичный cover.jpg лучше, чем дырявая галерея."""
    paths = []
    for i, angle in enumerate(VARIANT_ANGLES[:GALLERY_SIZE]):
        try:
            img = generate_image(ch["niche"], angle=angle)
        except Exception as e:
            print(f"gallery photo {i} failed: {e}")
            return None
        path = TMP / f"{tag}_g{i}.jpg"
        img.save(path, "JPEG", quality=90)
        paths.append(path)
    return paths


def _ken_burns_clip(image_path, out_path, seconds, fps=25, zoom_out=False):
    frames = round(seconds * fps)
    z_expr = "if(eq(on,0),1.15,max(zoom-0.0015,1.0))" if zoom_out else "min(zoom+0.0015,1.15)"
    vf = f"scale=1024:1024,zoompan=z='{z_expr}':d={frames}:s=1024x1024:fps={fps},format=yuv420p"
    subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-vf", vf,
         "-t", str(seconds), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out_path)],
        check=True, capture_output=True, timeout=120,
    )
    return out_path


def _loop_tail(last_frame, first_frame, out_path, seconds=1.5, fps=25):
    subprocess.run(
        ["ffmpeg", "-y",
         "-loop", "1", "-t", str(seconds), "-i", str(last_frame),
         "-loop", "1", "-t", str(seconds), "-i", str(first_frame),
         "-filter_complex",
         f"[0:v]scale=1024:1024[a];[1:v]scale=1024:1024[b];"
         f"[a][b]xfade=transition=fade:duration={seconds}:offset=0,format=yuv420p",
         "-c:v", "libx264", "-t", str(seconds), str(out_path)],
        check=True, capture_output=True, timeout=60,
    )
    return out_path


def narration_script(ch: dict, cta: str) -> str:
    prompt = (
        f"Channel topic: {ch['name']}\n"
        f"Niche: {ch['niche']}\n\n"
        f"Write a punchy ~12-second voiceover script (2 short sentences, ~30 words) for a "
        f"vertical video ad. Say plainly what this is about and why it matters, right away, "
        f"then end on this call to action: '{cta}'. Confident, energetic tone. English. No "
        f"markdown, no quotation marks, plain spoken text only."
    )
    text = ask(prompt, system="You write short voiceover scripts for product video ads.", max_tokens=120)
    if text and CYRILLIC_RE.search(text):
        text = ask(prompt + "\n\nTranslate everything to English - zero Cyrillic characters.",
                   system="You write short voiceover scripts for product video ads.", max_tokens=120)
    if not text or CYRILLIC_RE.search(text):
        return None
    return text.strip()


def build_video(gallery: list, ch: dict, cta: str, tag: str):
    """Gallery stills -> opener purpose-band frame -> 4 alternating Ken Burns
    segments -> loop-back crossfade tail -> voiceover mux. Any stage failing
    degrades gracefully (see digital-product-agent/post_telegram.py -- same
    logic, ported)."""
    try:
        seg_seconds = VIDEO_SECONDS / len(gallery)
        opener = overlay_band(Image.open(gallery[0]), ch["name"], position="top")
        opener_path = TMP / f"{tag}_opener.jpg"
        opener.save(opener_path, "JPEG", quality=90)

        frame_paths, seg_paths = [], []
        for i, img_path in enumerate(gallery):
            src = opener_path if i == 0 else img_path
            framed = overlay_band(Image.open(src), cta, position="bottom")
            frame_path = TMP / f"{tag}_frame{i}.jpg"
            framed.save(frame_path, "JPEG", quality=90)
            frame_paths.append(frame_path)
            seg_path = TMP / f"{tag}_seg{i}.mp4"
            _ken_burns_clip(frame_path, seg_path, seg_seconds, zoom_out=(i % 2 == 1))
            seg_paths.append(seg_path)

        try:
            tail_path = TMP / f"{tag}_tail.mp4"
            _loop_tail(frame_paths[-1], frame_paths[0], tail_path)
            seg_paths.append(tail_path)
        except Exception as e:
            print(f"loop tail failed, montage still works without it: {e}")

        concat_list = TMP / f"{tag}_concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in seg_paths), encoding="utf-8"
        )
        silent_path = TMP / f"{tag}_silent.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-c", "copy", str(silent_path)],
            check=True, capture_output=True, timeout=60,
        )
    except Exception as e:
        print(f"video montage failed, falling back to photos only: {e}")
        return None

    try:
        script = narration_script(ch, cta)
        if not script:
            raise ValueError("no clean English narration available")
        voice_path = TMP / f"{tag}_voice.mp3"
        asyncio.run(edge_tts.Communicate(script, VOICE).save(str(voice_path)))
        voice_seconds = float(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(voice_path),
        ]).strip())
        out_seconds = min(VIDEO_SECONDS + 2, voice_seconds + 0.4)
        final_path = TMP / f"{tag}_final.mp4"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(silent_path), "-i", str(voice_path),
             "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
             "-t", str(out_seconds), "-shortest", str(final_path)],
            check=True, capture_output=True, timeout=60,
        )
        return final_path
    except Exception as e:
        print(f"voiceover failed, posting silent video: {e}")
        return silent_path


def build_post_media(ch: dict, cta: str, cover_path) -> list:
    """Returns [(path, 'photo'|'video'), ...]. Falls back to the single cached
    cover.jpg on any gallery failure -- old behaviour, not a regression."""
    TMP.mkdir(exist_ok=True)
    tag = f"{ch['n']:02d}"
    gallery = build_gallery(ch, tag)
    if gallery is None:
        return [(cover_path, "photo")] if cover_path.exists() else []
    items = [(p, "photo") for p in gallery]
    video = build_video(gallery, ch, cta, tag)
    if video:
        items.append((video, "video"))
    return items


def cleanup(ch: dict) -> None:
    tag = f"{ch['n']:02d}_"
    for p in TMP.glob(f"{tag}*"):
        try:
            p.unlink()
        except OSError:
            pass
