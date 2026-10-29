#!/usr/bin/env python3
"""Kokoro-82M TTS worker: synthesize a JSONL job list with many English voices.

Run this under a Python interpreter that has ``kokoro`` installed (torch +
misaki + an English spaCy model, plus the hexgrad/Kokoro-82M weights in the
local Hugging Face cache). One KPipeline is loaded per worker process and
reused for every job, so model load happens once per worker, not per sentence.

Job line format: {"idx": 0, "text": "...", "voice": "af_heart", "out": "x.wav", "speed": 1.0}

Usage:
    python tts_kokoro.py --jobs jobs.jsonl --workers 4
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import time
import wave
from pathlib import Path


import re

# A sentence needs at least one letter or digit for Kokoro to vocalize it.
_SPEAKABLE = re.compile(r"[A-Za-z0-9]")

def _worker_init(threads: int) -> None:
    global _PIPES
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("OMP_NUM_THREADS", str(threads))
    import torch
    from kokoro import KPipeline
    torch.set_num_threads(threads)
    _PIPES = {"a": KPipeline(lang_code="a"), "b": KPipeline(lang_code="b")}


def _synth(job: dict) -> tuple:
    import numpy as np

    out_path = Path(job["out"])
    if out_path.exists() and out_path.stat().st_size > 2000:
        return job["idx"], "skip", 0.0
    text = str(job.get("text", ""))
    if not _SPEAKABLE.search(text):
        # Symbol-only lines (e.g. "* * * * *" scene breaks) produce no audio
        # from Kokoro; render a short pause instead of failing the whole run.
        arr = np.zeros(int(24000 * 1.5), dtype="<i2")
        with wave.open(str(out_path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(arr.tobytes())
        return job["idx"], "ok", len(arr) / 24000.0
    lang = "b" if str(job["voice"]).startswith("b") else "a"
    pipe = _PIPES[lang]
    speed = float(job.get("speed", 1.0))
    chunks = []
    for attempt in range(3):
        try:
            chunks = list(pipe(text, voice=job["voice"], speed=speed))
        except Exception:  # noqa: BLE001 - transient model hiccups get retried
            chunks = []
        if chunks:
            break
        time.sleep(1.0 + attempt)
    if not chunks:
        raise RuntimeError(f"no audio generated for idx={job['idx']} after retries")
    audio = np.concatenate([np.asarray(c[2].cpu()).ravel() for c in chunks])
    arr = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(arr.tobytes())
    return job["idx"], "ok", len(arr) / 24000.0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", required=True, help="JSONL file with synthesis jobs")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--threads", type=int, default=6, help="torch threads per worker")
    args = ap.parse_args()

    jobs = [json.loads(line) for line in Path(args.jobs).read_text(encoding="utf-8").splitlines() if line.strip()]
    for j in jobs:
        Path(j["out"]).parent.mkdir(parents=True, exist_ok=True)
    print(f"[kokoro] {len(jobs)} jobs, {args.workers} workers", flush=True)
    done = 0
    fails = []
    with mp.get_context("spawn").Pool(args.workers, initializer=_worker_init, initargs=(args.threads,)) as pool:
        for idx, status, dur in pool.imap_unordered(_synth, jobs, chunksize=4):
            done += 1
            if status == "ok":
                print(f"  [{done}/{len(jobs)}] idx={idx} dur={dur:.2f}s", flush=True)
            elif status == "skip":
                print(f"  [{done}/{len(jobs)}] idx={idx} cached", flush=True)
            if status not in ("ok", "skip"):
                fails.append(idx)
    if fails:
        raise SystemExit(f"[kokoro] FAILED jobs: {idx}")
    print(f"[kokoro] all {len(jobs)} jobs synthesized", flush=True)


if __name__ == "__main__":
    main()
