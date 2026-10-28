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
        "text": (58, 42, 26), "title": (66, 48, 30), "small": (80, 58, 34),
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
    # warm amber autumn paper (light)
    "autumn": {
        "paper_top": (240, 214, 170), "paper_bottom": (214, 176, 120),
        "border": (110, 62, 26), "stain": (168, 112, 50),
        "text": (70, 40, 15), "title": (84, 48, 18), "small": (90, 50, 18),
        "shadow": (44, 24, 10), "vignette": 0.5,
    },
    # cool paper-white with black ink (light)
    "ink": {
        "paper_top": (236, 236, 232), "paper_bottom": (214, 214, 208),
        "border": (72, 74, 80), "stain": (150, 152, 158),
        "text": (32, 34, 38), "title": (24, 26, 30), "small": (70, 72, 78),
        "shadow": (18, 18, 20), "vignette": 0.4,
    },
    # warm ivory linen (light)
    "linen": {
        "paper_top": (242, 236, 220), "paper_bottom": (219, 208, 184),
        "border": (98, 82, 56), "stain": (160, 142, 106),
        "text": (58, 50, 36), "title": (68, 58, 42), "small": (84, 72, 52),
        "shadow": (36, 30, 20), "vignette": 0.45,
    },
    # dusty plum paper (light)
    "plum": {
        "paper_top": (222, 202, 212), "paper_bottom": (188, 158, 174),
        "border": (84, 44, 66), "stain": (146, 100, 124),
        "text": (58, 28, 42), "title": (70, 34, 50), "small": (78, 40, 58),
        "shadow": (36, 16, 26), "vignette": 0.45,
    },
    # soft sage paper (light)
    "sage": {
        "paper_top": (214, 220, 202), "paper_bottom": (180, 192, 166),
        "border": (58, 76, 52), "stain": (118, 140, 104),
        "text": (40, 52, 36), "title": (32, 46, 30), "small": (58, 74, 52),
        "shadow": (24, 34, 22), "vignette": 0.45,
    },
    # pale sky paper (light)
    "sky": {
        "paper_top": (220, 232, 242), "paper_bottom": (186, 206, 224),
        "border": (56, 76, 104), "stain": (126, 156, 188),
        "text": (28, 44, 62), "title": (22, 36, 54), "small": (62, 84, 110),
        "shadow": (16, 26, 38), "vignette": 0.4,
    },
    # burnished copper paper (light)
    "copper": {
        "paper_top": (232, 202, 176), "paper_bottom": (198, 154, 122),
        "border": (112, 56, 30), "stain": (172, 108, 70),
        "text": (64, 32, 16), "title": (78, 40, 20), "small": (86, 46, 26),
        "shadow": (40, 20, 10), "vignette": 0.5,
    },
    # charcoal board with cream ink (dark)
    "charcoal": {
        "paper_top": (60, 60, 64), "paper_bottom": (38, 38, 42),
        "border": (196, 194, 186), "stain": (104, 102, 100),
        "text": (236, 232, 220), "title": (244, 240, 228), "small": (196, 192, 180),
        "shadow": (250, 246, 236), "vignette": 0.5,
    },
    # deep sea-green with pale foam ink (dark)
    "seafoam": {
        "paper_top": (38, 74, 68), "paper_bottom": (18, 44, 42),
        "border": (178, 214, 204), "stain": (88, 132, 122),
        "text": (230, 242, 234), "title": (238, 248, 240), "small": (186, 210, 198),
        "shadow": (240, 252, 244), "vignette": 0.45,
    },
    # deep wine with blush ink (dark)
    "wine": {
        "paper_top": (104, 44, 54), "paper_bottom": (62, 22, 32),
        "border": (226, 194, 186), "stain": (142, 78, 88),
        "text": (244, 228, 216), "title": (250, 236, 224), "small": (214, 184, 176),
        "shadow": (250, 240, 230), "vignette": 0.45,
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
