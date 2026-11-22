#!/usr/bin/env python3
"""render.py: turn demo/receipts.cast (from record.py) into docs/assets/receipts.gif, .mp4 and a poster frame.
Every frame is drawn from the recorded output at its recorded time; nothing is typed in by hand.
Needs Pillow, ffmpeg and the JetBrains Mono font.   python3 demo/render.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

here = Path(__file__).resolve().parent
assets = here.parent / "docs" / "assets"  # the README and the Pages site both use these
W, H, FPS, HOLD = 1280, 720, 10, 4.0
COLS, LINE, PAD, TOP = 98, 25, 34, 52
BG, FG, BAR, EDGE = "#ffffff", "#1f2328", "#f6f8fa", "#d1d9e0"
SGR = {"0": FG, "1;33": "#9a6700", "1;35": "#8250df", "2": "#6e7781", "1;32": "#1a7f37", "1;31": "#cf222e"}
BOLD = {"1;33", "1;35", "1;32", "1;31"}


def font(name):
    for d in (Path.home() / "Library/Fonts", Path("/Library/Fonts"), Path("/usr/share/fonts/truetype/jetbrains-mono")):
        if (d / name).exists():
            return ImageFont.truetype(str(d / name), 15)
    sys.exit(f"render: font {name} not found")


REG, BLD = font("JetBrainsMono-Regular.ttf"), font("JetBrainsMono-Bold.ttf")
CW = REG.getlength("M")


def lines_from(text):
    """Split terminal text into lines of (colour code, chunk) runs, wrapped at COLS."""
    out, code = [], "0"
    for raw in text.replace("\r\n", "\n").split("\n"):
        runs, plain = [], ""
        for part in re.split(r"(\x1b\[[0-9;]*m)", raw):
            m = re.fullmatch(r"\x1b\[([0-9;]*)m", part)
            if m:
                code = m.group(1) or "0"
            elif part:
                runs.append((code, part))
                plain += part
        # wrap at the last space before COLS, keeping each character's colour; continuation lines indent to match
        flat = [(c, ch) for c, s in runs for ch in s]
        indent = len(plain) - len(plain.lstrip(" ")) + (2 if plain.lstrip().startswith("- ") else 0)
        line = flat
        while len(line) > COLS:
            cut = max((k for k in range(indent + 1, COLS) if line[k][1] == " "), default=COLS)
            out.append(line[:cut])
            line = [("0", " ")] * indent + [x for x in line[cut:]][1 if line[cut][1] == " " else 0:]
        out.append(line)
    return out


def frame(lines):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, TOP - 14], fill=BAR)
    d.line([0, TOP - 14, W, TOP - 14], fill=EDGE)
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        d.ellipse([18 + i * 20, 13, 30 + i * 20, 25], fill=c)
    title = "shop — the agent's terminal"
    d.text(((W - REG.getlength(title)) / 2, 11), title, font=REG, fill="#59636e")
    rows = (H - TOP - PAD) // LINE
    for r, line in enumerate(lines[-rows:]):
        x = PAD
        for code, ch in line:
            f = BLD if code in BOLD else REG
            d.text((x, TOP + 6 + r * LINE), ch, font=f, fill=SGR.get(code, FG))
            x += CW
    return img


def main():
    cast = here / "receipts.cast"
    events = [json.loads(x) for x in cast.read_text().splitlines()][1:]
    end = events[-1][0] + HOLD
    tmp = Path(tempfile.mkdtemp())
    try:
        n, i, text = int(end * FPS), 0, ""
        for k in range(n):
            t = k / FPS
            while i < len(events) and events[i][0] <= t:
                text += events[i][2]
                i += 1
            frame(lines_from(text)).save(tmp / f"f{k:05d}.png")
        ff = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%05d.png")]
        subprocess.run(ff + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
                             str(assets / "receipts.mp4")], check=True)
        subprocess.run(ff + ["-vf", "scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=32[p];[b][p]paletteuse=dither=none",
                             str(assets / "receipts.gif")], check=True)
        frame(lines_from(text)).save(assets / "receipts-poster.png")
        print(f"rendered {n} frames, {end:.1f}s into docs/assets: receipts.mp4, receipts.gif, receipts-poster.png")
    finally:
        shutil.rmtree(tmp)


if __name__ == "__main__":
    main()
