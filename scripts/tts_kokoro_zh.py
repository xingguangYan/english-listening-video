#!/usr/bin/env python3
"""Kokoro-82M Mandarin TTS worker: synthesize a JSONL job list with zh voices.

Run under a kokoro-capable interpreter (torch + misaki + pypinyin + jieba +
cn2an + ordered-set). Voices live in the hexgrad/Kokoro-82M HF repo:
zf_xiaobei zf_xiaoni zf_xiaoxiao zf_xiaoyi zm_yunjian zm_yunxi zm_yunxia
zm_yunyang. Set HF_ENDPOINT=https://hf-mirror.com if huggingface.co is
unreachable; the voices cache locally after first use.

Job line format: {"idx": 0, "text": "...", "voice": "zf_xiaobei", "out": "x.wav", "speed": 1.0}
Wavs are 24kHz mono 16-bit, matching the English kokoro worker.

Usage:
    python tts_kokoro_zh.py --jobs jobs.jsonl --workers 4 --threads 4
"""
from __future__ import annotations

import argparse
import json
import os
import time
import wave
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")


def _worker_init(threads: int) -> None:
    global _PIPE
    os.environ.setdefault("OMP_NUM_THREADS", str(threads))
    import torch
    from kokoro import KPipeline
    torch.set_num_threads(threads)
    _PIPE = KPipeline(lang_code="z")


def _synth(job: dict) -> tuple:
    import numpy as np
    out_path = Path(job["out"])
    if out_path.exists() and out_path.stat().st_size > 2000:
        return job["idx"], "skip", 0.0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    chunks = []
    for _graphemes, _phonemes, audio in _PIPE(job["text"], voice=job["voice"],
                                              speed=float(job.get("speed", 1.0))):
        chunks.append(audio)
    audio = np.concatenate(chunks) if chunks else np.zeros(1)
    data = np.clip(audio, -1.0, 1.0)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes((data * 32767).astype("<i2").tobytes())
    return job["idx"], "ok", len(data) / 24000.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--threads", type=int, default=4)
    args = ap.parse_args()

    jobs = [json.loads(l) for l in Path(args.jobs).read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[kokoro-zh] {len(jobs)} jobs, {args.workers} workers", flush=True)
    t0 = time.time()
    with Pool(args.workers, initializer=_worker_init, initargs=(args.threads,)) as pool:
        for done, (idx, status, dur) in enumerate(pool.imap_unordered(_synth, jobs, chunksize=4), 1):
            if done % 50 == 0 or status not in ("ok", "skip"):
                print(f"[kokoro-zh] {done}/{len(jobs)} idx={idx} {status} {dur:.2f}s "
                      f"({(time.time() - t0) / 60:.1f} min)", flush=True)
    print(f"[kokoro-zh] done in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
