#!/usr/bin/env python3
"""Generate a procedural themed background (aged paper / night scene) with PIL.

No network or image API required. Pass a scene theme to recolour the paper and
its texture; the matching text colours live in themes.py so subtitles stay
readable on any scene.

Usage:
    python make_parchment.py --out parchment.png --seed 7
    python make_parchment.py --out night.png --theme midnight --seed 11
"""
from __future__ import annotations

import argparse
import importlib.util
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("themes", _HERE / "themes.py")
_themes = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_themes)
get_theme = _themes.get_theme
THEMES = _themes.THEMES


def _gradient(palette: dict, width: int, height: int) -> np.ndarray:
    """Vertical paper gradient with a soft horizontal bias for a lit feel."""
    y = np.linspace(0.0, 1.0, height, dtype=np.float32)
    x = np.linspace(0.0, 1.0, width, dtype=np.float32)
    top = np.array(palette["paper_top"], dtype=np.float32)
    bot = np.array(palette["paper_bottom"], dtype=np.float32)
    vertical = top[None, None, :] + (bot - top)[None, None, :] * y[:, None, None]
    shift = 0.5 * (x[None, :, None] - 0.5)
    img = vertical + shift * np.array([6.0, 4.0, -4.0], dtype=np.float32)[None, None, :]
    return np.clip(img, 0, 255)


def _grain(img: Image.Image, rng: random.Random, strength: int = 9) -> Image.Image:
    """Fine paper grain blended at low alpha."""
    noise = Image.effect_noise(img.size, strength).convert("L")
    return Image.composite(
        Image.merge("RGB", [noise] * 3).point(lambda v: v), img, noise.point(lambda v: 12)
    )


def _fibres(img: Image.Image, rng: random.Random, palette: dict, count: int = 900) -> Image.Image:
    """Short translucent strokes that read as paper fibres."""
    w, h = img.size
    dark_fibre = tuple(int(c * 0.55) for c in palette["paper_bottom"])
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for _ in range(count):
        x0, y0 = rng.uniform(0, w), rng.uniform(0, h)
        length = rng.uniform(6, 26)
        angle = rng.uniform(0, 2 * np.pi)
        x1, y1 = x0 + length * np.cos(angle), y0 + length * np.sin(angle)
        color = (dark_fibre[0], dark_fibre[1], dark_fibre[2], rng.randint(5, 14)) \
            if rng.random() < 0.5 else (255, 250, 235, rng.randint(6, 16))
        draw.line([(x0, y0), (x1, y1)], fill=color, width=1)
    comp = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    return comp


def _stains(img: Image.Image, rng: random.Random, palette: dict, count: int = 9) -> Image.Image:
    """Large soft blobs with radial falloff."""
    w, h = img.size
    base = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(count):
        cx, cy = rng.uniform(0, w), rng.uniform(0, h)
        r = rng.uniform(w * 0.08, w * 0.28)
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        alpha = np.clip(1.0 - dist / r, 0.0, 1.0) ** 2
        strength = rng.uniform(6, 22)
        for ch, tone in enumerate(palette["stain"]):
            base[:, :, ch] += alpha * (tone - base[:, :, ch]) * (strength / 100.0)
        if rng.random() < 0.6:
            sx = rng.uniform(cx - r / 2, cx + r / 2)
            sy = rng.uniform(cy - r / 2, cy + r / 2)
            sr = rng.uniform(2, 7)
            sd = np.sqrt((xx - sx) ** 2 + (yy - sy) ** 2)
            mask = np.clip(1.0 - sd / sr, 0.0, 1.0) ** 2
            for ch in range(3):
                base[:, :, ch] -= mask * rng.uniform(8, 26)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def _vignette(img: Image.Image, strength: float) -> Image.Image:
    """Darken the corners so the page reads as an aged sheet."""
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt(((xx - cx) / (w * 0.62)) ** 2 + ((yy - cy) / (h * 0.62)) ** 2)
    falloff = np.clip(dist - 0.55, 0.0, None) ** 1.6
    base = np.asarray(img).astype(np.float32)
    base *= (1.0 - falloff[..., None] * strength)
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))


def _frame(img: Image.Image, palette: dict, margin_ratio: float = 0.035) -> Image.Image:
    """Thin double decorative border, plus a soft edge shadow."""
    w, h = img.size
    m = int(min(w, h) * margin_ratio)
    border = palette["border"]
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([m, m, w - m, h - m], outline=border + (140,), width=3)
    draw.rectangle([m + 10, m + 10, w - m - 10, h - m - 10], outline=border + (70,), width=2)
    shadow = Image.new("L", img.size, 0)
    sd = ImageDraw.Draw(shadow)
    sd.rectangle([m + 3, m + 3, w - m - 3, h - m - 3], outline=60, width=14)
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    dark = Image.new("RGBA", img.size, (40, 26, 10, 0))
    overlay = Image.composite(dark, overlay, shadow)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def generate(width: int = 1920, height: int = 1080, seed: int = 7, theme: str = "classic") -> Image.Image:
    palette = get_theme(theme)
    rng = random.Random(seed)
    img = Image.fromarray(_gradient(palette, width, height).astype(np.uint8))
    img = _grain(img, rng)
    img = _fibres(img, rng, palette)
    img = _stains(img, rng, palette)
    img = _vignette(img, palette.get("vignette", 0.55))
    img = _frame(img, palette)
    return img.filter(ImageFilter.GaussianBlur(0.6))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, help="output PNG path")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--theme", default="classic", choices=sorted(THEMES))
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    generate(args.width, args.height, args.seed, args.theme).save(out)
    print(f"background -> {out} ({args.width}x{args.height}, theme={args.theme})")


if __name__ == "__main__":
    main()
