#!/usr/bin/env python3
"""Build an English-listening video: parchment background, centred English
subtitles, spoken by a rotating cast of Kokoro-82M voices.

Pipeline: load public-domain texts -> split into passages/sentences -> pick
enough content to fill the target duration -> TTS every sentence (offline via
Kokoro; the worker runs under a kokoro-capable interpreter, auto-detected) ->
render one parchment frame per sentence -> encode with ffmpeg -> concat ->
video + SRT + manifest + thumbnail.

Examples:
    python build_video.py --content corpus/aesop-fables.txt --minutes 60 --out out/hour.mp4
    python build_video.py --minutes 0.5 --out out/smoke.mp4     # quick test
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BG = SKILL_DIR / "assets" / "parchment.png"
SKILL_SCRIPTS = SKILL_DIR / "scripts"

import importlib.util as _ilu


def _load_module(name: str):
    spec = _ilu.spec_from_file_location(name, SKILL_SCRIPTS / f"{name}.py")
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_themes_mod = _load_module("themes")
get_theme = _themes_mod.get_theme
THEMES = _themes_mod.THEMES

# Rotating cast: 12 Kokoro-82M English voices across two accents.
# voice id -> on-screen accent label
DEFAULT_VOICES = [
    ("af_heart", "American English · Heart"),
    ("am_adam", "American English · Adam"),
    ("bf_emma", "British English · Emma"),
    ("bm_george", "British English · George"),
    ("af_bella", "American English · Bella"),
    ("am_michael", "American English · Michael"),
    ("bf_alice", "British English · Alice"),
    ("bm_daniel", "British English · Daniel"),
    ("af_nicole", "American English · Nicole"),
    ("am_eric", "American English · Eric"),
    ("bf_isabella", "British English · Isabella"),
    ("bm_lewis", "British English · Lewis"),
    ("af_alloy", "American English · Alloy"),
    ("af_aoede", "American English · Aoede"),
    ("af_jessica", "American English · Jessica"),
    ("af_kore", "American English · Kore"),
    ("af_nova", "American English · Nova"),
    ("af_river", "American English · River"),
    ("af_sarah", "American English · Sarah"),
    ("af_sky", "American English · Sky"),
    ("am_echo", "American English · Echo"),
    ("am_fenrir", "American English · Fenrir"),
    ("am_liam", "American English · Liam"),
    ("am_onyx", "American English · Onyx"),
    ("am_puck", "American English · Puck"),
    ("bf_lily", "British English · Lily"),
    ("bm_fable", "British English · Fable"),
]

WORK_TITLES = {
    "aesop-fables": "Aesop's Fables",
    "grimms-fairy-tales": "Grimms' Fairy Tales",
    "happy-prince": "The Happy Prince and Other Tales",
    "sherlock-holmes": "The Adventures of Sherlock Holmes",
}

FONT_BODY = ["georgia.ttf", "times.ttf", "DejaVuSerif.ttf", "FreeSerif.ttf"]
FONT_BOLD = ["georgiab.ttf", "timesbd.ttf", "DejaVuSerif-Bold.ttf", "FreeSerifBold.ttf"]

ABBREV = ["Mr", "Mrs", "Ms", "Dr", "Prof", "Sr", "Jr", "St", "vs", "etc", "Co",
           "Inc", "Ltd", "Hon", "Rev", "Capt", "Lt", "Sgt", "Col", "Gen", "Esq"]

def find_font(candidates: List[str]) -> Path:
    here = Path("C:/Windows/Fonts")
    for name in candidates:
        for root in (here, SKILL_DIR / "assets", Path("/usr/share/fonts/truetype/dejavu")):
            p = root / name
            if p.exists():
                return p
    return Path("")  # caller falls back to PIL default


def load_font(candidates: List[str], size: int) -> ImageFont.FreeTypeFont:
    p = find_font(candidates)
    if str(p):
        return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


# ----------------------------------------------------------------------------- parsing

@dataclass
class Work:
    title: str
    text: str


@dataclass
class Passage:
    work: str
    title: str
    body: str
    voice: str = ""
    label: str = ""


@dataclass
class Segment:
    idx: int
    work: str
    passage_title: str
    text: str
    voice: str
    label: str
    audio: Path = None  # type: ignore[assignment]
    dur: float = 0.0
    frame: Path = None  # type: ignore[assignment]
    video: Path = None  # type: ignore[assignment]


def prettify(stem: str) -> str:
    return WORK_TITLES.get(stem, stem.replace("-", " ").replace("_", " ").title())


def load_works(paths: List[Path]) -> List[Work]:
    return [Work(title=prettify(p.stem), text=p.read_text(encoding="utf-8", errors="replace")) for p in paths]


def looks_like_title(line: str) -> bool:
    words = line.split()
    if not (1 <= len(words) <= 10) or len(line) > 90:
        return False
    if line[-1] in ".!?;:,\"\u201d\u2019)":
        return False
    caps = sum(1 for w in words if w[:1].isupper() or w[:1].isdigit())
    return caps >= max(2, int(len(words) * 0.7))


def is_toc(para: str) -> bool:
    lines = [l.strip() for l in para.split("\n") if l.strip()]
    if len(lines) < 6:
        return False
    short = sum(1 for l in lines if len(l.split()) < 9)
    ends = sum(1 for l in lines if l.endswith("."))
    return short >= len(lines) * 0.8 and ends < len(lines) * 0.2


def strip_markup(s: str) -> str:
    """Remove Project Gutenberg _italic_ emphasis markers."""
    return re.sub(r"_([^_]+)_", r"\1", s)


def is_low_quality_sentence(s: str) -> bool:
    """Drop headings, footnotes, and bare citations that read badly aloud."""
    words = s.split()
    if not words:
        return True
    if len(words) <= 12:
        upper = sum(1 for w in words if w.isupper() and any(c.isalpha() for c in w))
        if upper >= max(3, int(len(words) * 0.6)):
            return True  # ALL-CAPS heading or title page
    if re.search(r"\bpp\.|\bvol\.|\bcf\.|\bop\. cit|ibid", s, re.I):
        return True  # scholarly citation
    if len(words) <= 10 and re.search(r"\b(1[0-9]{3})\b", s):
        return True  # bare year / page number
    return False


def split_sentences(text: str) -> List[str]:
    t = re.sub(r"\s+", " ", text).strip()
    for a in ABBREV:
        t = re.sub(rf"\b{a}\.", f"{a}<P>", t)
    t = re.sub(r"(\d)\.(\d)", r"\1<P>\2", t)
    parts = re.split(r'(?<=[.!?…])["\u201d\u2019\')\]]?\s+', t)
    out = []
    for part in parts:
        s = part.replace("<P>", ".").strip()
        if s and not is_low_quality_sentence(s):
            out.append(strip_markup(s))
    # short interjections ("Ho! ho!") should not become their own segment:
    # merge them into the next sentence so nothing gets dropped
    merged: List[str] = []
    for s in out:
        if merged and len(s.split()) < 4:
            merged[-1] = f"{merged[-1]} {s}"
        else:
            merged.append(s)
    if len(merged) > 1 and len(merged[-1].split()) < 4:
        merged[-2] = f"{merged[-2]} {merged[-1]}"
        merged.pop()
    return merged


def parse_passages(work: Work, max_words: int = 380) -> List[Passage]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", work.text) if p.strip()]
    passages: List[tuple] = []
    cur_title, cur_body = "", []
    for para in paras:
        if is_toc(para):
            continue
        lines = [l.strip() for l in para.split("\n") if l.strip()]
        if len(lines) == 1 and looks_like_title(lines[0]):
            if cur_body:
                passages.append((cur_title, " ".join(cur_body)))
            cur_title, cur_body = lines[0], []
        else:
            cur_body.append(" ".join(lines))
    if cur_body:
        passages.append((cur_title, " ".join(cur_body)))

    result: List[Passage] = []
    for title, body in passages:
        sents = split_sentences(body)
        if len(body.split()) < 20 or len(sents) < 2:
            continue
        caps = sum(1 for w in body.split() if w.isupper() and any(c.isalpha() for c in w))
        if caps >= len(body.split()) * 0.45:
            continue  # title-page / dedication block
        words = body.split()
        if len(words) > max_words:  # chunk long passages at sentence boundaries
            chunks, cur, n = [], [], 0
            for s in sents:
                w = len(s.split())
                if cur and n + w > max_words:
                    chunks.append(cur)
                    cur, n = [s], w
                else:
                    cur.append(s)
                    n += w
            if cur:
                chunks.append(cur)
            for i, ch in enumerate(chunks):
                t = title if i == 0 else (f"{title} (part {i + 1})" if title else "")
                result.append(Passage(work.title, t, " ".join(ch)))
        else:
            result.append(Passage(work.title, title, body))
    return result


# ----------------------------------------------------------------------------- kokoro runner

# ----------------------------------------------------------------------------- kokoro runner

def find_kokoro_python() -> Optional[Path]:
    """Locate a Python interpreter with kokoro/torch installed."""
    import os

    candidates: List[Path] = [Path(sys.executable)]
    env_hint = os.environ.get("KOKORO_PYTHON", "")
    if env_hint:
        candidates.insert(0, Path(env_hint))
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    for base in (home / "skills", SKILL_DIR, Path.cwd()):
        candidates.extend(sorted(base.glob("*/.venv/Scripts/python.exe")))
        candidates.extend(sorted(base.glob(".venv/Scripts/python.exe")))
        candidates.extend(sorted(base.glob("*/venv/Scripts/python.exe")))
    for cand in candidates:
        if not cand.exists():
            continue
        try:
            r = subprocess.run([str(cand), "-c", "import kokoro, torch"],
                               capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                return cand
        except Exception:  # noqa: BLE001 - keep scanning
            continue
    return None


def run_kokoro_tts(jobs: List[dict], interpreter: Path, workers: int, threads: int,
                   jobs_file: Path) -> None:
    with jobs_file.open("w", encoding="utf-8") as fh:
        for j in jobs:
            fh.write(json.dumps(j, ensure_ascii=False) + "\n")
    cmd = [str(interpreter), str(SKILL_SCRIPTS / "tts_kokoro.py"),
           "--jobs", str(jobs_file), "--workers", str(workers), "--threads", str(threads)]
    print(f"[tts ] running kokoro with {interpreter.name} ({workers} workers)")
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, text=True)
    code = proc.wait()
    if code != 0:
        raise SystemExit(f"kokoro TTS failed with exit code {code}")


# ----------------------------------------------------------------------------- ffmpeg

def run(cmd: List[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{r.stderr[-2000:]}")


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or 0)


def encode_segment(frame: Path, audio: Path, dur: float, pad: float, out: Path, fps: int) -> None:
    total = max(dur + pad, 0.4)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-loop", "1", "-framerate", str(fps), "-i", str(frame),
           "-i", str(audio),
           "-af", f"apad=pad_dur={pad}",
           "-t", f"{total:.3f}",
           "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast", "-crf", "30",
           "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
           str(out)]
    run(cmd)


def make_intro(card: Path, seconds: float, fps: int, out: Path) -> None:
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-loop", "1", "-framerate", str(fps), "-i", str(card),
           "-f", "lavfi", "-t", f"{seconds:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
           "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast", "-crf", "30",
           "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
           "-t", f"{seconds:.2f}", "-shortest", str(out)]
    run(cmd)


def concat(segments: List[Path], out: Path, tmp: Path) -> None:
    lst = tmp / "list.txt"
    lst.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in segments), encoding="utf-8")
    copy = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat",
            "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)]
    r = subprocess.run(copy, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  concat copy failed ({r.stderr[-300:]}); re-encoding", file=sys.stderr)
        reenc = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "concat",
                 "-safe", "0", "-i", str(lst), "-c:v", "libx264", "-crf", "28",
                 "-preset", "medium", "-c:a", "aac", "-b:a", "160k",
                 "-movflags", "+faststart", str(out)]
        run(reenc)


# ----------------------------------------------------------------------------- frames

def wrap_text(text: str, font, max_w: float) -> List[str]:
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if font.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_spaced(img: ImageDraw.Image, text: str, font, y: float, fill, spacing: float,
                center_w: float) -> None:
    widths = [font.getlength(ch) for ch in text]
    total = sum(widths) + spacing * max(0, len(text) - 1)
    x = (center_w - total) / 2
    for ch, w in zip(text, widths):
        img.text((x, y), ch, font=font, fill=fill)
        x += w + spacing


def fit_text(text: str, font_path: Path, max_w: float, max_h: float,
             min_size: int, max_size: int, gap: float = 1.28):
    size = max_size
    while size >= min_size:
        font = ImageFont.truetype(str(font_path), size) if str(font_path) else ImageFont.load_default()
        lines = wrap_text(text, font, max_w)
        h = len(lines) * size * gap
        if h <= max_h and all(font.getlength(l) <= max_w for l in lines):
            return font, lines, h
        size -= 2
    font = ImageFont.truetype(str(font_path), min_size) if str(font_path) else ImageFont.load_default()
    lines = wrap_text(text, font, max_w)
    return font, lines, len(lines) * min_size * gap

def render_frame(bg: Image.Image, work: str, passage_title: str, text: str, label: str,
                 fonts: dict, w: int, h: int, colors: Optional[dict] = None) -> Image.Image:
    colors = colors or get_theme("classic")
    img = bg.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)
    inner = w - 2 * 220
    # small work label on top
    draw_spaced(draw, work.upper(), fonts["small"], y=92, fill=tuple(colors["small"]) + (190,),
                spacing=5, center_w=w)
    # passage title
    if passage_title:
        draw_spaced(draw, passage_title.upper(), fonts["title"], y=150,
                    fill=tuple(colors["title"]) + (220,), spacing=3, center_w=w)
    # body: centred block
    body_font, lines, block_h = fit_text(
        text, fonts["body_path"], inner, h * 0.56, min_size=30, max_size=52
    )
    lh = body_font.size * 1.28
    y = 560 - block_h / 2
    for line in lines:
        x = (w - body_font.getlength(line)) / 2
        draw.text((x, y + 2), line, font=body_font, fill=tuple(colors["shadow"]) + (60,))
        draw.text((x, y), line, font=body_font, fill=tuple(colors["text"]) + (245,))
        y += lh
    # accent label at the bottom
    if label:
        draw_spaced(draw, label, fonts["bottom"], y=h - 96, fill=tuple(colors["small"]) + (170,),
                    spacing=2, center_w=w)
    return img.convert("RGB")


def render_intro_frame(bg: Image.Image, fonts: dict, w: int, h: int, title: str,
                       subtitle: str, colors: Optional[dict] = None) -> Image.Image:
    colors = colors or get_theme("classic")
    img = bg.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)
    f1 = ImageFont.truetype(str(fonts["title_path"]), 88)
    f2 = ImageFont.truetype(str(fonts["body_path"]), 40)
    tlen = f1.getlength(title)
    draw.text(((w - tlen) / 2, h / 2 - 110), title, font=f1, fill=tuple(colors["title"]) + (240,))
    slen = f2.getlength(subtitle)
    draw.text(((w - slen) / 2, h / 2 + 20), subtitle, font=f2, fill=tuple(colors["small"]) + (200,))
    return img.convert("RGB")


# ----------------------------------------------------------------------------- srt

def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    hh, ms = divmod(ms, 3600_000)
    mm, ms = divmod(ms, 60_000)
    ss, ms = divmod(ms, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def write_srt(segments: List[dict], path: Path) -> None:
    lines = []
    for i, s in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{srt_time(s['start'])} --> {srt_time(s['end'])}")
        lines.append(s["text"])
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ----------------------------------------------------------------------------- main

def parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--content", nargs="*", default=None, help="txt files; default corpus/*.txt")
    ap.add_argument("--minutes", type=float, default=60.0)
    ap.add_argument("--out", default="out/english-listening.mp4")
    ap.add_argument("--bg", default=None, help="background image; omit to use the theme paper")
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--theme", default="classic", choices=sorted(THEMES),
                    help="scene theme: colours the generated paper and the subtitle ink")
    ap.add_argument("--voices", default=",".join(v for v, _ in DEFAULT_VOICES),
                    help="comma-separated kokoro voice ids")
    ap.add_argument("--speed", type=float, default=1.0, help="kokoro speech speed")
    ap.add_argument("--pad", type=float, default=0.45, help="silence after each sentence")
    ap.add_argument("--workers", type=int, default=6, help="ffmpeg/frame workers")
    ap.add_argument("--tts-workers", type=int, default=4, help="kokoro worker processes")
    ap.add_argument("--tts-threads", type=int, default=6, help="torch threads per tts worker")
    ap.add_argument("--tts-python", default=None, help="interpreter with kokoro; auto-detected")
    ap.add_argument("--tmp", default=None)
    ap.add_argument("--no-intro", action="store_true")
    ap.add_argument("--title", default="English Listening Practice")
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--preview-frame", type=int, default=None,
                    help="render only this segment's frame png and exit (debug)")
    return ap.parse_args(argv)


def main() -> None:
    args = parse_args()
    t0 = time.time()
    tmp = Path(args.tmp) if args.tmp else Path(args.out).with_suffix("") / "_build"
    tmp.mkdir(parents=True, exist_ok=True)
    audio_dir, frame_dir, seg_dir = (tmp / "audio", tmp / "frames", tmp / "segs")
    for d in (audio_dir, frame_dir, seg_dir):
        d.mkdir(exist_ok=True)

    if args.bg:
        bg_path = Path(args.bg)
        if not bg_path.exists():
            raise SystemExit(f"background image not found: {bg_path}")
    elif args.theme == "classic" and DEFAULT_BG.exists():
        bg_path = DEFAULT_BG
    else:
        # no explicit background: generate a themed paper on the fly
        make_parchment = _load_module("make_parchment")
        bg_path = tmp / f"bg_{args.theme}.png"
        if not bg_path.exists():
            seed = sum(ord(c) for c in args.theme) % 997
            make_parchment.generate(args.width, args.height, seed, args.theme).save(bg_path)
            print(f"[bg  ] generated themed background ({args.theme}) -> {bg_path}")
    bg = Image.open(bg_path).convert("RGB").resize((args.width, args.height))

    theme = get_theme(args.theme)
    colors = {"text": theme["text"], "title": theme["title"],
              "small": theme["small"], "shadow": theme["shadow"]}

    fonts = {
        "small": load_font(FONT_BODY, 28),
        "title": load_font(FONT_BOLD, 44),
        "bottom": load_font(FONT_BODY, 24),
        "body_path": find_font(FONT_BODY),
        "title_path": find_font(FONT_BOLD),
    }

    content = [Path(p) for p in args.content] if args.content else sorted(Path("corpus").glob("*.txt"))
    if not content:
        raise SystemExit("no content: run fetch_corpus.py or pass --content files")
    works = load_works(content)

    voice_names = [v.strip() for v in args.voices.split(",") if v.strip()]
    label_by_voice = dict(DEFAULT_VOICES)

    work_lists = [parse_passages(w) for w in works]
    if not any(work_lists):
        raise SystemExit("no usable passages parsed from content")
    # round-robin across works so genres alternate through the video
    passages: List[Passage] = []
    while any(work_lists):
        for wl in work_lists:
            if wl:
                passages.append(wl.pop(0))
    for i, p in enumerate(passages):
        p.voice = voice_names[i % len(voice_names)]
        p.label = label_by_voice.get(p.voice, p.voice)

    target = max(args.minutes * 60 - (0 if args.no_intro else 6.0), 5)

    # ---- plan by rough estimate (chars -> seconds), then verify with real audio
    def est_seconds(text: str) -> float:
        return len(text) / 15.0 + 0.6

    planned: List[Segment] = []
    approx = 0.0
    for p in passages:
        if approx >= target:
            break
        for sent in split_sentences(p.body):
            if len(sent.split()) < 3:
                continue
            seg = Segment(idx=len(planned), work=p.work, passage_title=p.title,
                          text=sent, voice=p.voice, label=p.label,
                          audio=audio_dir / f"{len(planned):04d}.wav")
            planned.append(seg)
            approx += est_seconds(seg.text)
    if approx < target * 0.9:
        print(f"[warn] only ~{approx / 60:.1f} min of content found; target was {target / 60:.1f} min")
    print(f"[plan] {len(planned)} segments over {len(works)} works (est {approx / 60:.1f} min)")

    if args.preview_frame is not None:
        seg = planned[min(args.preview_frame, len(planned) - 1)]
        frame = render_frame(bg, seg.work, seg.passage_title, seg.text, seg.label,
                             fonts, args.width, args.height, colors)
        outp = tmp / f"preview_{args.preview_frame:04d}.png"
        frame.save(outp)
        print(f"preview -> {outp}")
        return

    # ---- tts via kokoro worker (cached wavs are skipped)
    todo = [s for s in planned if not (s.audio.exists() and s.audio.stat().st_size > 2000)]
    if todo:
        interpreter = Path(args.tts_python) if args.tts_python else find_kokoro_python()
        if interpreter is None:
            raise SystemExit("no kokoro-capable python found; install kokoro/torch/misaki "
                             "and pass --tts-python /path/to/python.exe")
        jobs = [{"idx": s.idx, "text": s.text, "voice": s.voice, "out": str(s.audio),
                 "speed": args.speed} for s in todo]
        print(f"[tts ] {len(todo)} sentences -> kokoro ({len(voice_names)} voices)")
        run_kokoro_tts(jobs, interpreter, args.tts_workers, args.tts_threads,
                      tmp / "jobs.jsonl")

    # ---- real durations, trim to target window [target, target*1.03]
    durations = [probe_duration(s.audio) for s in planned]
    for s, d in zip(planned, durations):
        s.dur = max(d, 0.5)
    total = sum(s.dur + args.pad for s in planned)
    while total > target * 1.03 and len(planned) > 1 and total - planned[-1].dur - args.pad >= target:
        total -= planned[-1].dur + args.pad
        planned.pop()
    print(f"[time] {total / 60:.2f} min of spoken content (target {target / 60:.2f})")

    # ---- frames + encode in parallel
    def build_one(s: Segment) -> Path:
        s.frame = frame_dir / f"{s.idx:04d}.png"
        if not s.frame.exists():
            frame = render_frame(bg, s.work, s.passage_title, s.text, s.label,
                                 fonts, args.width, args.height, colors)
            frame.save(s.frame, compress_level=4)
        s.video = seg_dir / f"{s.idx:04d}.mp4"
        if not (s.video.exists() and s.video.stat().st_size > 5000):
            encode_segment(s.frame, s.audio, s.dur, args.pad, s.video, 24)
        return s.video

    print(f"[render+encode] {len(planned)} segments with {args.workers} workers")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        seg_videos = list(pool.map(build_one, planned))

    # ---- assemble
    parts: List[Path] = []
    intro_dur = 0.0
    if not args.no_intro:
        subtitle = args.subtitle or f"{args.minutes:g} minutes · {len(set(s.voice for s in planned))} voices · centred subtitles"
        card = tmp / "intro_card.png"
        render_intro_frame(bg, fonts, args.width, args.height, args.title, subtitle, colors).save(card)
        intro = seg_dir / "intro.mp4"
        if not intro.exists():
            make_intro(card, 6.0, 24, intro)
        parts.append(intro)
        intro_dur = 6.0

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    concat(parts + seg_videos, out, tmp)

    # ---- srt + manifest + thumbnail
    cursor = intro_dur
    rows = []
    for s in planned:
        start = cursor
        cursor += s.dur + args.pad
        rows.append({"idx": s.idx, "start": start, "end": cursor, "text": s.text,
                     "voice": s.voice, "accent": s.label, "work": s.work,
                     "passage": s.passage_title})
    srt = out.with_suffix(".srt")
    write_srt(rows, srt)

    label_set = sorted(set(s.label for s in planned))
    manifest = {
        "video": str(out),
        "duration_seconds": round(cursor, 2),
        "duration_minutes": round(cursor / 60, 2),
        "target_minutes": args.minutes,
        "segments": len(planned),
        "voices": sorted(set(s.voice for s in planned)),
        "accents": label_set,
        "works": sorted(set(s.work for s in planned)),
        "settings": {"width": args.width, "height": args.height, "speed": args.speed,
                     "pad": args.pad, "background": str(bg_path)},
        "timeline": rows,
    }
    out.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    thumb = out.with_suffix(".thumbnail.jpg")
    if planned and planned[0].frame:
        with Image.open(planned[0].frame) as im:
            im.convert("RGB").save(thumb, quality=92)

    print(f"[done] {out}")
    print(f"       duration {cursor / 60:.2f} min · {len(planned)} segments · "
          f"{len(manifest['voices'])} voices · srt: {srt.name}")
    print(f"       total build {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
