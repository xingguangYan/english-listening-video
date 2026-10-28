#!/usr/bin/env python3
"""Build a themed multi-episode listening collection from the corpus catalog.

One episode per catalog work, cycling through the scene themes:

    python scripts/make_collection.py --out D:/collection

Re-runs are resumable: cached audio, frames and segments inside each
episode's _build folder are reused.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from fetch_corpus import CATALOG  # noqa: E402
from themes import THEMES  # noqa: E402

DEFAULT_THEMES = ["classic", "fog", "midnight", "rose", "dream",
                  "sea", "earth", "frost", "forest", "regency"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="output collection folder")
    ap.add_argument("--corpus", default="corpus", help="folder with fetched .txt works")
    ap.add_argument("--minutes", type=float, default=63,
                    help="target minutes per episode (default: 63)")
    ap.add_argument("--voices", default="", help="comma list (default: skill cast)")
    ap.add_argument("--themes", default=",".join(DEFAULT_THEMES),
                    help="comma list of scene themes, cycled per episode")
    ap.add_argument("--skip", default="", help="comma-separated work stems to skip")
    args = ap.parse_args()

    themes = [t.strip() for t in args.themes.split(",") if t.strip()]
    for t in themes:
        if t not in THEMES:
            raise SystemExit(f"unknown theme {t!r}; choose from {sorted(THEMES)}")
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    results = []
    for i, (_gid, name) in enumerate(CATALOG.items()):
        stem = Path(name).stem
        if stem in skip:
            continue
        content = Path(args.corpus) / name
        if not content.exists():
            print(f"[skip] {name} (missing in {args.corpus})")
            continue
        theme = themes[i % len(themes)]
        num = f"{len(results) + 1:02d}"
        outdir = out / f"{num}-{stem}"
        outdir.mkdir(parents=True, exist_ok=True)
        video = outdir / f"english-listening-{num}-{stem}.mp4"
        cmd = [sys.executable, str(HERE / "build_video.py"),
               "--minutes", str(args.minutes), "--theme", theme,
               "--content", str(content), "--out", str(video),
               "--tmp", str(outdir / "_build")]
        if args.voices:
            cmd += ["--voices", args.voices]
        print(f"[{num}] {stem} theme={theme}", flush=True)
        code = subprocess.call(cmd)
        results.append((num, stem, theme, code, video.exists()))

    print("\n=== summary ===")
    ok = sum(1 for r in results if r[3] == 0 and r[4])
    for num, stem, theme, code, exists in results:
        status = "ok" if code == 0 and exists else f"FAILED({code})"
        print(f"{num} {stem} [{theme}]: {status}")
    print(f"{ok}/{len(results)} episodes built")
    if ok != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
