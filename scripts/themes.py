"""Scene themes for listening videos: paper palette + on-screen text colors.

Each theme drives both make_parchment.py (how the paper looks) and
build_video.py (which text colors stay readable on that paper). Light themes
use dark ink; dark themes use cream ink with a faint light halo shadow.
"""

from __future__ import annotations

THEMES = {
    # classic warm parchment (the original look)
    "classic": {
        "paper_top": (232, 219, 184), "paper_bottom": (206, 183, 138),
        "border": (96, 70, 42), "stain": (148, 108, 56),
        "text": (58, 42, 26), "title": (66, 48, 30), "small": (96, 72, 46),
        "shadow": (40, 28, 14), "vignette": 0.55,
    },
    # deep indigo night
    "midnight": {
        "paper_top": (42, 46, 84), "paper_bottom": (16, 18, 40),
        "border": (196, 190, 232), "stain": (84, 94, 156),
        "text": (238, 232, 216), "title": (246, 240, 224), "small": (196, 190, 222),
        "shadow": (240, 232, 212), "vignette": 0.45,
    },
    # rose-gold parchment
    "rose": {
        "paper_top": (244, 224, 222), "paper_bottom": (228, 186, 182),
        "border": (128, 62, 70), "stain": (176, 110, 108),
        "text": (74, 34, 42), "title": (88, 42, 50), "small": (120, 62, 70),
        "shadow": (48, 24, 30), "vignette": 0.5,
    },
    # charcoal victorian fog
    "fog": {
        "paper_top": (66, 68, 74), "paper_bottom": (32, 34, 40),
        "border": (206, 200, 190), "stain": (96, 98, 106),
        "text": (240, 234, 218), "title": (248, 242, 228), "small": (198, 192, 178),
        "shadow": (242, 236, 220), "vignette": 0.5,
    },
    # deep sea teal
    "sea": {
        "paper_top": (24, 66, 74), "paper_bottom": (10, 34, 42),
        "border": (180, 224, 226), "stain": (40, 100, 108),
        "text": (226, 244, 244), "title": (236, 250, 250), "small": (176, 214, 214),
        "shadow": (220, 240, 240), "vignette": 0.5,
    },
    # soft lavender dream (light paper)
    "dream": {
        "paper_top": (238, 232, 246), "paper_bottom": (214, 202, 230),
        "border": (104, 82, 140), "stain": (150, 128, 190),
        "text": (52, 40, 86), "title": (64, 50, 104), "small": (92, 74, 132),
        "shadow": (36, 28, 62), "vignette": 0.45,
    },
    # dark earthy umber
    "earth": {
        "paper_top": (78, 58, 42), "paper_bottom": (40, 28, 20),
        "border": (216, 196, 168), "stain": (108, 80, 58),
        "text": (244, 234, 216), "title": (250, 242, 226), "small": (204, 188, 166),
        "shadow": (246, 236, 218), "vignette": 0.5,
    },
    # icy winter paper (light)
    "frost": {
        "paper_top": (232, 240, 248), "paper_bottom": (198, 214, 230),
        "border": (58, 88, 120), "stain": (120, 150, 180),
        "text": (26, 42, 66), "title": (34, 52, 80), "small": (62, 84, 114),
        "shadow": (24, 38, 60), "vignette": 0.4,
    },
    # sage forest paper (light)
    "forest": {
        "paper_top": (228, 238, 222), "paper_bottom": (198, 218, 190),
        "border": (62, 96, 60), "stain": (126, 160, 116),
        "text": (28, 56, 34), "title": (36, 68, 42), "small": (66, 96, 68),
        "shadow": (22, 46, 28), "vignette": 0.45,
    },
    # cream-blush regency paper (light)
    "regency": {
        "paper_top": (246, 238, 228), "paper_bottom": (232, 214, 200),
        "border": (132, 66, 84), "stain": (178, 122, 126),
        "text": (66, 32, 44), "title": (82, 40, 54), "small": (116, 58, 76),
        "shadow": (46, 22, 32), "vignette": 0.45,
    },
}

DEFAULT_THEME = "classic"


def get_theme(name: str) -> dict:
    if name not in THEMES:
        raise KeyError(f"unknown theme {name!r}; available: {', '.join(THEMES)}")
    return THEMES[name]


def is_dark(theme: dict) -> bool:
    r, g, b = theme["paper_bottom"]
    return (0.299 * r + 0.587 * g + 0.114 * b) < 128
