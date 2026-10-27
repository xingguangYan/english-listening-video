#!/usr/bin/env python3
"""Download public-domain English texts (Project Gutenberg) and clean them.

Saves one plain UTF-8 text file per work. The build script consumes whatever
``.txt`` files are in the corpus dir, so you can also drop in your own texts.

Usage:
    python fetch_corpus.py --out corpus
    python fetch_corpus.py --out corpus --ids 28 2591 902
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

# Curated short-form public-domain works good for listening practice.
# Easy/short: Aesop, Anderson. Mid: Grimm, Wilde. Longer: Doyle.
CATALOG = {
    28: "aesop-fables.txt",        # The Fables of Aesop (short, clear)
    2591: "grimms-fairy-tales.txt",  # Grimms' Fairy Tales
    902: "happy-prince.txt",       # The Happy Prince and Other Tales (Wilde)
    1661: "sherlock-holmes.txt",   # The Adventures of Sherlock Holmes
}

URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"
# Alternative mirrors in case gutenberg.org is slow/blocked.
MIRRORS = [
    "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt",
    "https://www.gutenberg.org/files/{id}/pg{id}.txt",
]

# Body-anchored markers: skip each work's scholarly front matter (title pages,
# prefaces, contents tables) by cutting at the first line of real story text.
START_MARKERS = {
    28: "A cock was once strutting",                    # The Cock and the Pearl
    2591: "A certain king had a beautiful garden",      # The Golden Bird
    902: "HIGH above the city, on a tall column",       # The Happy Prince
    1661: "I had seen little of Holmes lately",         # A Scandal in Bohemia
}

HEADER_RE = re.compile(r"\*\*\*\s*(START|BEGINNING)[^\n]*\*\*\*", re.I)
FOOTER_RE = re.compile(r"\*\*\*\s*END\s+OF[^\n]*\*\*\*", re.I)


def download(url: str, dest: Path) -> None:
    """Download with urllib; fall back to curl.exe for proxied networks."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=45) as resp, dest.open("wb") as fh:
            shutil.copyfileobj(resp, fh)
        return
    except Exception as exc:  # noqa: BLE001 - fallback is deliberate
        print(f"  urllib failed ({exc}); trying curl", file=sys.stderr)
    subprocess.run(
        ["curl.exe", "-sSL", "-m", "120", "-o", str(dest), url],
        check=True,
    )


def trim_to_body(text: str, marker: str) -> str:
    """Cut everything before the story body, keeping the title line above it."""
    i = text.find(marker)
    if i < 0:
        return text
    cut = text.rfind("\n\n", 0, i)
    if cut < 0 or i - cut > 120:
        cut = i
        return text[cut:]
    prev = text.rfind("\n\n", 0, max(cut - 1, 0))
    if prev >= 0:
        title_para = text[prev:cut].strip()
        words = title_para.split()
        if 1 <= len(words) <= 10 and len(title_para) <= 90 and title_para[-1:] not in ".!?" and title_para:
            cut = prev
    return text[cut:]


def clean(raw: str, gid: int = 0) -> str:
    """Strip Gutenberg boilerplate, front matter, and stray indexes."""
    if HEADER_RE.search(raw):
        raw = HEADER_RE.split(raw, maxsplit=1)[-1]
    if FOOTER_RE.search(raw):
        raw = FOOTER_RE.split(raw, maxsplit=1)[0]
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    if gid in START_MARKERS:
        raw = trim_to_body(raw, START_MARKERS[gid])
    lines = []
    for line in raw.split("\n"):
        s = line.strip()
        if not s:
            lines.append("")
            continue
        if s.startswith("[Illustration") or s.startswith("["):
            continue
        if s in ("THE END",) or re.fullmatch(r"[\d\s\.\-]+", s):
            continue
        lines.append(s)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="corpus", help="output directory for cleaned texts")
    ap.add_argument("--ids", type=int, nargs="*", default=list(CATALOG), help="gutenberg ids")
    ap.add_argument("--force", action="store_true", help="re-download and overwrite existing files")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for gid in args.ids:
        name = CATALOG.get(gid, f"pg{gid}.txt")
        dest = out / name
        if dest.exists() and not args.force:
            print(f"[skip] {dest} exists")
            continue
        ok = False
        for tmpl in MIRRORS:
            url = tmpl.format(id=gid)
            print(f"[get ] {url}")
            try:
                download(url, dest)
                text = dest.read_text(encoding="utf-8", errors="replace")
                if len(text) > 5000:
                    cleaned = clean(text, gid)
                    dest.write_text(cleaned, encoding="utf-8")
                    words = len(cleaned.split())
                    print(f"[ok  ] {name}: {words} words")
                    ok = True
                    break
                print(f"[warn] too short, trying next mirror")
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] failed: {exc}")
        if not ok:
            dest.unlink(missing_ok=True)
            print(f"[fail] gutenberg id {gid}")
    print(f"corpus ready in {out}")


if __name__ == "__main__":
    main()
