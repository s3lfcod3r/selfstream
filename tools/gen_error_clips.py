#!/usr/bin/env python3
"""Dev-only: render the 'max streams' / 'banned' info screens and encode them
to short MPEG-TS clips that real HLS players will actually play.

Run ONCE locally (needs imageio-ffmpeg in the venv). The resulting .ts files
are committed to backend/assets/ and served statically by the proxy — the
server never runs ffmpeg, so there is no runtime CPU cost.

    .venv/Scripts/python.exe tools/gen_error_clips.py
"""
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(REPO, "backend", "assets")
LOGO = os.path.join(REPO, "frontend", "logo.png")

WIDTH, HEIGHT = 1280, 720
# Match the logo PNG's own (non-transparent) background so the logo blends into
# the canvas seamlessly instead of showing a cut-off box. frontend/logo.png is
# RGB with a (19, 22, 27) background.
BG = (19, 22, 27)
RED = (248, 81, 73)

# A couple of common Windows font paths as a fallback to DejaVu (Linux).
FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
]
FONT_CANDIDATES_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
]


def _font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_image(out_png, title, line1, line2):
    img = Image.new("RGB", (WIDTH, HEIGHT), color=BG)
    draw = ImageDraw.Draw(img)

    # Logo, centered near the top
    try:
        logo = Image.open(LOGO).convert("RGBA")
        logo.thumbnail((240, 240), Image.LANCZOS)
        patch = Image.new("RGBA", logo.size, (*BG, 255))
        patch.paste(logo, (0, 0), logo)
        logo_rgb = patch.convert("RGB")
        img.paste(logo_rgb, ((WIDTH - logo_rgb.width) // 2, 70))
    except Exception as exc:  # noqa: BLE001 - logo is cosmetic
        print(f"  (logo skipped: {exc})")

    # Stop symbol
    draw.ellipse([540, 300, 740, 500], outline=RED, width=8)
    draw.rectangle([600, 370, 680, 430], fill=RED)

    font_large = _font(FONT_CANDIDATES_BOLD, 46)
    font_med = _font(FONT_CANDIDATES_REG, 28)
    font_small = _font(FONT_CANDIDATES_REG, 22)

    for font, text, y, color in [
        (font_large, title, 540, RED),
        (font_med, line1, 604, (180, 190, 200)),
        (font_small, line2, 646, (139, 148, 158)),
    ]:
        if not text:
            continue
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((WIDTH - w) // 2, y), text, font=font, fill=color)

    draw.rectangle([20, 20, WIDTH - 20, HEIGHT - 20], outline=(30, 40, 55), width=2)
    img.save(out_png, "PNG")


def encode_ts(png_path, ts_path, ffmpeg, seconds=8):
    # Still image -> H.264 baseline + silent AAC, MPEG-TS. Low fps/bitrate keeps
    # the file tiny; baseline/yuv420p maximizes player compatibility (VLC,
    # ExoPlayer, tablet apps). Silent audio track avoids "no audio" stalls.
    cmd = [
        ffmpeg, "-y",
        "-loop", "1", "-i", png_path,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(seconds),
        "-r", "10",
        "-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0",
        "-pix_fmt", "yuv420p", "-b:v", "500k", "-g", "20",
        "-c:a", "aac", "-b:a", "64k",
        "-shortest",
        "-f", "mpegts", ts_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def main():
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(ASSETS, exist_ok=True)

    screens = [
        ("error-max-streams.ts", "Max. Streams erreicht",
         "Bitte beende einen anderen Stream", "und versuche es erneut."),
        ("error-banned.ts", "Zugang gesperrt",
         "Dein Zugang wurde deaktiviert.", "Bitte kontaktiere den Betreiber."),
    ]

    with tempfile.TemporaryDirectory() as tmp:
        for name, title, l1, l2 in screens:
            png = os.path.join(tmp, name.replace(".ts", ".png"))
            ts = os.path.join(ASSETS, name)
            print(f"Rendering {name} ...")
            render_image(png, title, l1, l2)
            encode_ts(png, ts, ffmpeg)
            size = os.path.getsize(ts)
            print(f"  -> {ts} ({size/1024:.1f} KiB)")

    print("Done.")


if __name__ == "__main__":
    sys.exit(main())
