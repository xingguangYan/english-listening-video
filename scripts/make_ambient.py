#!/usr/bin/env python3
"""Synthesize a soft ambient bed that follows the story mood of an episode.

Reads the episode manifest (timeline of segments with text + passage), groups
the timeline into ~6-minute sections, assigns each section a chord mood from
keywords in its sentences, renders slow sine pads with crossfades, and writes
one continuous stereo WAV as long as the video.
"""
from __future__ import annotations

import json
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
XF = 10.0           # crossfade seconds between sections
MAX_SECTION = 360.0 # seconds per rendered block
MASTER_FADE_IN = 25.0

MOODS = {
    "night":  dict(freqs=[55.0, 82.41, 110.0, 164.81, 220.0],  amp=[1.0, 0.75, 0.55, 0.40, 0.30], rate=0.045, depth=0.18),
    "water":  dict(freqs=[65.41, 98.0, 130.81, 196.0, 293.66], amp=[1.0, 0.70, 0.50, 0.38, 0.25], rate=0.060, depth=0.16),
    "forest": dict(freqs=[98.0, 146.83, 196.0, 246.94, 392.0], amp=[1.0, 0.70, 0.50, 0.32, 0.22], rate=0.050, depth=0.15),
    "warm":   dict(freqs=[87.31, 130.81, 174.61, 261.63, 349.23], amp=[1.0, 0.72, 0.50, 0.35, 0.24], rate=0.055, depth=0.16),
    "tender": dict(freqs=[73.42, 110.0, 146.83, 220.0, 293.66], amp=[1.0, 0.75, 0.55, 0.40, 0.28], rate=0.040, depth=0.17),
}

KEYWORDS = [
    ("night",  ["night", "moon", "star", "sleep", "dream", "dark", "midnight", "shadow", "quiet", "silver"]),
    ("water",  ["sea", "river", "water", "wave", "ship", "rain", "lake", "stream", "shore", "boat", "swim", "flood"]),
    ("forest", ["forest", "tree", "garden", "flower", "bird", "grass", "wood", "leaf", "wind", "vine", "nest", "rose"]),
    ("warm",   ["sun", "morning", "light", "warm", "fire", "smile", "happy", "gold", "spring", "bright", "glow"]),
]


def mood_for(text: str) -> str:
    t = text.lower()
    counts = {}
    for mood, keys in KEYWORDS:
        counts[mood] = sum(t.count(k) for k in keys)
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else "tender"


def render(mood: str, n: int) -> np.ndarray:
    cfg = MOODS[mood]
    t = np.arange(n, dtype=np.float32) / SR
    out = np.zeros((n, 2), dtype=np.float32)
    vib = 0.02 * np.sin(2 * np.pi * 0.05 * t)
    for k, (f, a) in enumerate(zip(cfg["freqs"], cfg["amp"])):
        lfo = 1.0 + cfg["depth"] * np.sin(2 * np.pi * cfg["rate"] * t + 0.37 * k)
        for ch in range(2):
            ph = 0.6 * ch + 0.37 * k
            out[:, ch] += (a * np.sin(2 * np.pi * f * t + vib + ph) * lfo).astype(np.float32)
    # soft attack/release envelope for smooth crossfades
    atk = int(8.0 * SR)
    rel = int(10.0 * SR)
    env = np.ones(n, dtype=np.float32)
    env[:atk] = np.linspace(0, 1, atk, dtype=np.float32)
    if n > rel:
        env[-rel:] = np.linspace(1, 0, rel, dtype=np.float32)
    out *= env[:, None]
    peak = float(np.max(np.abs(out))) or 1.0
    return (out * (0.55 / peak)).astype(np.float32)


def to_pcm(block: np.ndarray) -> bytes:
    return (np.clip(block, -1.0, 1.0) * 32767).astype("<i2").tobytes()


def main() -> None:
    manifest_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    mf = json.loads(manifest_path.read_text(encoding="utf-8"))
    total = float(mf["duration_seconds"])
    segs = mf["timeline"]

    # ---- group the timeline into sections of at most MAX_SECTION seconds
    sections = []  # (mood, duration)
    cur_text, cur_start, cur_len = [], segs[0]["start"], 0.0
    for s in segs:
        cur_text.append(s.get("text", ""))
        cur_len = s["end"] - cur_start
        if cur_len >= MAX_SECTION:
            sections.append((mood_for(" ".join(cur_text)), cur_len))
            cur_text, cur_start, cur_len = [], s["end"], 0.0
    if cur_text:
        sections.append((mood_for(" ".join(cur_text)), cur_len))
    # cover the intro card at the start and pad to the full duration
    lead = max(0.0, segs[0]["start"])
    if lead > 1.0:
        sections.insert(0, ("tender", lead))
    gap = total - sum(d for _, d in sections)
    sections[-1] = (sections[-1][0], sections[-1][1] + gap + XF)  # tail for release
    print(f"total video {total:.1f}s -> {len(sections)} sections")
    for m, d in sections:
        print(f"  {m:7s} {d:7.1f}s")

    # ---- render with crossfades into one WAV
    w = wave.open(str(out_path), "wb")
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    nxf = int(XF * SR)
    tail = None
    for i, (mood, dur) in enumerate(sections):
        n = int(dur * SR) + 2 * nxf
        block = render(mood, n)
        if i == 0:
            nfi = int(MASTER_FADE_IN * SR)
            block[:nfi] *= np.linspace(0, 1, nfi, dtype=np.float32)[:, None]
        nout = int(dur * SR)
        if tail is not None:
            lin = np.linspace(0, 1, nxf, dtype=np.float32)
            block[:nxf] = block[:nxf] * lin[:, None] + tail * (1 - lin)[:, None]
        w.writeframes(to_pcm(block[:nout]))
        tail = block[nout:nout + nxf].copy()
    if tail is not None:
        w.writeframes(to_pcm(tail))
    w.close()
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
