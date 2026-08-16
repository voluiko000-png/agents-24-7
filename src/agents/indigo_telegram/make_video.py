"""Cover + avatar + LLM-written narration -> vertical 1080x1920 mp4 with burned-in
word-synced captions, edge-tts voice, Ken Burns zoom on both cover and avatar, CTA plate.

Reuses edge_tts (SubMaker/WordBoundary events -> captions, no extra subtitle lib),
llm.py (same free-provider cascade as the Telegram pipeline -> fresh script every call,
nothing hardcoded), and ffmpeg (libx264/aac/subtitles/zoompan/drawtext -> Gyan.dev full
builds have all of these).

Usage:
    python make_video.py cover.png out.mp4 CTA PRODUCT BENEFIT [avatar.png] [voice]

PRODUCT/BENEFIT feed the LLM prompt that writes the voiceover line (retention hook in
the first few words, then the benefit) -- every call gets a different script, nothing
is repeated. Pass avatar.png to composite a talking-head frame under the product cover
(vstack, both independently Ken-Burns'd so neither reads as a dead still image).
"""
import asyncio
import os
import subprocess
import sys
import tempfile

import edge_tts

from llm import ask

DEFAULT_VOICE = "en-US-AndrewNeural"


def generate_narration(product: str, benefit: str) -> str:
    """Fresh ~20-word voiceover line per call via the free LLM cascade -- never hardcoded."""
    prompt = (
        f"Write ONE spoken voiceover line (18-26 words) for a vertical social ad about "
        f"'{product}'. It must hook attention in the first 3-4 words, then explain this "
        f"benefit: {benefit}. Plain spoken English, no hashtags, no quotes, no emoji, "
        f"one sentence or two short ones."
    )
    text = ask(prompt, system="You write short, high-retention video ad voiceover scripts.")
    # ponytail: fallback keeps the pipeline alive if every free provider is cold-down'd
    return text or f"Stop scrolling -- {product} helps you {benefit}, starting today."


def _fmt_ts(seconds: float) -> str:
    ms = max(0, int(round(seconds * 1000)))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def render_narration_with_captions(text: str, voice: str, mp3_path: str) -> list:
    """One edge-tts pass -> audio bytes + WordBoundary cues (start_s, end_s, word)."""
    async def _run():
        # edge-tts 7.x defaults to SentenceBoundary; force word-level so captions can be
        # grouped into short multi-word chunks instead of one giant sentence-long cue
        communicate = edge_tts.Communicate(text, voice, boundary="WordBoundary")
        cues = []
        with open(mp3_path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / 1e7  # 100ns ticks -> seconds
                    end = (chunk["offset"] + chunk["duration"]) / 1e7
                    cues.append((start, end, chunk["text"]))
        return cues
    return asyncio.run(_run())


def write_srt(cues: list, srt_path: str, group: int = 4) -> None:
    """Group words into short multi-word captions (readable) instead of a word-flash."""
    blocks = []
    for i, start_i in enumerate(range(0, len(cues), group), 1):
        chunk = cues[start_i:start_i + group]
        start, end = chunk[0][0], chunk[-1][1]
        words = " ".join(w for _, _, w in chunk)
        blocks.append(f"{i}\n{_fmt_ts(start)} --> {_fmt_ts(end)}\n{words}\n")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(blocks) if blocks else "")


def probe_duration(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ])
    return float(out.strip())


def _ff_posix(path: str) -> str:
    """ffmpeg filtergraph parser splits on ':' even inside quotes -- escape the drive letter too."""
    return os.path.abspath(path).replace("\\", "/").replace(":", r"\:")


def build(cover: str, out_path: str, cta: str, product: str, benefit: str,
          avatar: str = None, voice: str = DEFAULT_VOICE, text: str = None,
          overlay: bool = True, max_dur: float = None) -> None:
    """overlay=False + max_dur=10 -> glov_media style: pure Ken Burns + voice,
    no burned-in captions/CTA plate, hard-capped to ~10s (proof-of-result loop,
    caption/link lives in the post text instead of on screen)."""
    text = text or generate_narration(product, benefit)

    with tempfile.TemporaryDirectory() as tmp:
        mp3 = os.path.join(tmp, "narration.mp3")
        srt = os.path.join(tmp, "captions.srt")
        cues = render_narration_with_captions(text, voice, mp3)
        write_srt(cues, srt)
        dur = probe_duration(mp3) + 0.4
        if max_dur:
            dur = min(dur, max_dur)
        frames = int(dur * 25)

        cta_escaped = cta.replace(":", r"\:").replace("'", r"\'")
        sub_style = (
            "FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,"
            "OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=0,"
            "Alignment=2,MarginV=90"
        )
        subs = f"subtitles=filename='{_ff_posix(srt)}':force_style='{sub_style}'"
        cta_plate = (
            f"drawtext=text='{cta_escaped}':fontcolor=white:fontsize=40:"
            "box=1:boxcolor=black@0.55:boxborderw=20:x=(w-text_w)/2:y=h-70"
        )

        inputs = ["-loop", "1", "-i", cover]
        if avatar:
            h_cover, h_avatar = 1152, 768  # 60/40 split, sums to 1920
            inputs += ["-loop", "1", "-i", avatar]
            vf_complex = (
                # ponytail: 2200px pre-scale (2x output width) is plenty for smooth zoompan and
                # far cheaper than the 8000px trick below on Reve's ~3500px-wide avatar renders
                f"[0:v]scale=2200:-1,zoompan=z='min(zoom+0.0012,1.18)':d={frames}:"
                f"s=1080x{h_cover}:fps=25[bg];"
                f"[1:v]scale=2200:-1,zoompan=z='min(zoom+0.0008,1.12)':d={frames}:"
                f"s=1080x{h_avatar}:fps=25[av];"
                "[bg][av]vstack=inputs=2[stacked];"
                f"[stacked]{subs}[subbed];"
                f"[subbed]{cta_plate}[outv]"
            )
            audio_input_idx = 2
            cmd = [
                "ffmpeg", "-y", *inputs, "-i", mp3,
                "-filter_complex", vf_complex,
                "-map", "[outv]", "-map", f"{audio_input_idx}:a",
                "-t", f"{dur:.2f}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-shortest", out_path,
            ]
        else:
            vf = (
                "scale=8000:-1,"
                f"zoompan=z='min(zoom+0.0012,1.18)':d={frames}:s=1080x1920:fps=25"
            )
            if overlay:
                vf += f",{subs},{cta_plate}"
            cmd = [
                "ffmpeg", "-y", *inputs, "-i", mp3,
                "-vf", vf, "-t", f"{dur:.2f}",
                "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                "-shortest", out_path,
            ]

        subprocess.run(cmd, check=True, capture_output=True)


def main() -> None:
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)
    cover, out_path, cta, product, benefit = sys.argv[1:6]
    rest = sys.argv[6:]
    avatar = rest[0] if rest else None
    voice = rest[1] if len(rest) > 1 else DEFAULT_VOICE
    build(cover, out_path, cta, product, benefit, avatar=avatar, voice=voice)
    print(f"Wrote {out_path} ({probe_duration(out_path):.1f}s)")


if __name__ == "__main__":
    main()
