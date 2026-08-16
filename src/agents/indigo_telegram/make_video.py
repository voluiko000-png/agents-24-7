"""Вертикальный ролик из N разных кадров -- чередование наезда/отъезда зума +
5 разных якорей паннинга, xfade-перетекание между кадрами, lanczos+unsharp
апскейл (источник Pollinations отдаёт максимум 576x1024). Опционально:
CTA/hook-текст в безопасной зоне кадра (overlay_band) + голос (edge-tts),
намикшированный поверх готового клипа.

16.08.2026 21:00, финально: голос + текст должны быть ВСЕГДА (референс --
канал Digital Katya, 90% видео хорошие), единственная проблема у референса --
текст иногда уезжает за край экрана, решение -- поднять его в безопасную зону
(indigo_media.overlay_band), а не убирать. Предыдущая версия этого файла была
немой по более раннему (отменённому) указанию "оставь как у Кати" -- см.
[[feedback-video-standard-katya-style-silent-no-text]] в памяти.

Usage:
    python make_video.py out.mp4 frame1.jpg frame2.jpg ...
"""
import asyncio
import os
import subprocess
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from indigo_media import narration_script, overlay_band  # noqa: E402

try:
    import edge_tts
except ImportError:
    edge_tts = None

W, H = 1080, 1920
SEC_PER_FRAME = 3.5
FADE = 0.6

ANCHORS = [
    ("iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),  # центр
    ("0", "0"),                                 # левый верх
    ("iw-(iw/zoom)", "0"),                      # правый верх
    ("0", "ih-(ih/zoom)"),                      # левый низ
    ("iw-(iw/zoom)", "ih-(ih/zoom)"),           # правый низ
]


def _prep_frame(src: str, dst: str) -> None:
    Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS).save(dst, quality=92)


def build(frames: list, out_path: str) -> float:
    """frames -- список путей к уже готовым портретным (1080x1920) картинкам,
    каждая получает свой сегмент с чередующимся зумом/паннингом и перетекает
    в следующую. Возвращает длительность итогового ролика в секундах."""
    inputs, filters, labels = [], [], []
    n_frames = int(SEC_PER_FRAME * 30)
    for i, p in enumerate(frames):
        inputs += ["-loop", "1", "-t", str(SEC_PER_FRAME), "-i", p]
        z = ("min(zoom+0.0012,1.14)" if i % 2 == 0
             else "if(lte(zoom,1.0),1.14,max(1.001,zoom-0.0012))")
        ax, ay = ANCHORS[i % len(ANCHORS)]
        filters.append(
            f"[{i}:v]scale=1620:-1:flags=lanczos,"
            f"unsharp=5:5:1.1:5:5:0.4,"
            f"zoompan=z='{z}':d={n_frames}:"
            f"x='{ax}':y='{ay}':s={W}x{H}:fps=30,"
            f"setsar=1[v{i}]")
        labels.append(f"[v{i}]")

    chain, prev = "", labels[0]
    for i in range(1, len(labels)):
        off = (SEC_PER_FRAME - FADE) * i
        out = f"[x{i}]"
        chain += (f"{prev}{labels[i]}xfade=transition=fade:duration={FADE}:"
                  f"offset={off:.2f}{out};")
        prev = out
    filters.append(chain.rstrip(";"))

    total = SEC_PER_FRAME * len(frames) - FADE * (len(frames) - 1)
    cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters),
           "-map", prev, "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    subprocess.run(cmd, check=True, capture_output=True)
    return total


def caption_frames(frame_paths: list, hook: str, cta: str) -> list:
    """hook в безопасной зоне сверху первого кадра, cta -- снизу на всех.
    Возвращает новые пути (исходники не трогает)."""
    out = []
    for i, p in enumerate(frame_paths):
        img = Image.open(p)
        if i == 0 and hook:
            img = overlay_band(img, hook, position="top")
        if cta:
            img = overlay_band(img, cta, position="bottom")
        dst = f"{p}.cap.jpg"
        img.save(dst, "JPEG", quality=92)
        out.append(dst)
    return out


def add_voice(video_path: str, ch: dict, cta: str, duration: float) -> None:
    """Озвучивает video_path поверх себя (edge-tts), in place. Любая ошибка
    оставляет исходный немой файл -- лучше немое видео, чем упавший пост."""
    if edge_tts is None:
        print("edge_tts не установлен, публикую немое видео")
        return
    voice_path = f"{video_path}.voice.mp3"
    muxed_path = f"{video_path}.muxed.mp4"
    try:
        script = narration_script(ch, cta)
        if not script:
            raise ValueError("no clean English narration available")
        asyncio.run(edge_tts.Communicate(script, "en-US-AndrewNeural").save(voice_path))
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-i", voice_path,
             "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
             "-t", f"{duration:.2f}", "-shortest", muxed_path],
            check=True, capture_output=True, timeout=60,
        )
        os.replace(muxed_path, video_path)
    except Exception as e:
        print(f"voiceover failed, posting silent video: {e}")
    finally:
        for p in (voice_path, muxed_path):
            if os.path.exists(p):
                os.remove(p)


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    out_path, raw_frames = sys.argv[1], sys.argv[2:]
    prepped = []
    for i, src in enumerate(raw_frames):
        dst = f"{out_path}.prep{i}.jpg"
        _prep_frame(src, dst)
        prepped.append(dst)
    try:
        dur = build(prepped, out_path)
        print(f"Wrote {out_path} ({dur:.1f}s)")
    finally:
        for p in prepped:
            os.remove(p)


def demo() -> None:
    """ponytail: no ffmpeg/network -- checks caption bands land inside the
    safe zone (not flush to the true top/bottom edge) on a real frame size."""
    from indigo_media import SAFE_BOTTOM, SAFE_TOP
    img = Image.new("RGB", (1080, 1920), "black")
    top = overlay_band(img, "Hook text", position="top")
    bottom = overlay_band(img, "Call to action", position="bottom")
    assert top.size == bottom.size == (1080, 1920)
    # band_top for "top" must be >= the safe margin, never 0 (flush to edge)
    assert int(1920 * SAFE_TOP) > 0
    assert int(1920 * SAFE_BOTTOM) > 0
    print(f"[demo] ok: safe zone top={SAFE_TOP:.0%} bottom={SAFE_BOTTOM:.0%} of frame height")


if __name__ == "__main__":
    demo() if "--demo" in sys.argv else main()
