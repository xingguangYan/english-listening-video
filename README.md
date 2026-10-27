# English Listening Video Generator

Creates English listening-practice videos: each sentence is shown centred on a
parchment background while a rotating cast of natural AI voices reads it aloud.
Bundled with a Codex skill that regenerates or customises the video in
minutes, fully offline (TTS runs locally with Kokoro-82M).

![sample frame](assets/parchment.png)

## What you get

- `english-listening-1hour.mp4` - one hour of listening practice (1920x1080,
  h264 + AAC, burned-in centred subtitles), published as a GitHub Release
  asset (too large for a plain git push).
- `english-listening-1hour.srt` - matching subtitle file.
- `english-listening-1hour.manifest.json` - full timeline: every sentence with
  start/end times, voice, accent and source work.
- A reusable pipeline: new topics, lengths, voices and backgrounds are one
  command away.

## Content

Public-domain English, interleaved for variety:

- Aesop's Fables (Gutenberg #28)
- The Happy Prince and Other Tales - Oscar Wilde (Gutenberg #902)
- Grimms' Fairy Tales (Gutenberg #2591)

Twelve voices rotate across the video: American and British English, male and
female (Kokoro-82M: af_heart, am_adam, bf_emma, bm_george, af_bella,
am_michael, bf_alice, bm_daniel, af_nicole, am_eric, bf_isabella, bm_lewis).

## Requirements

- ffmpeg/ffprobe, Python 3.10+ with `Pillow` + `numpy`
- A Kokoro-capable Python: `pip install kokoro>=0.9 misaki` plus `torch`, an
  English spaCy model (`en_core_web_sm`), and the `hexgrad/Kokoro-82M`
  weights (auto-downloaded; if huggingface.co is unreachable, the HF mirror
  `https://hf-mirror.com` is used automatically by the TTS worker).

## Usage

```bash
# 1. fetch and clean the public-domain corpus
python scripts/fetch_corpus.py --out corpus

# 2. build a video (one hour by default)
python scripts/build_video.py --minutes 60 --out out/english-listening-1hour.mp4

# quick smoke test
python scripts/build_video.py --minutes 1 --out out/smoke.mp4
```

Useful flags: `--content` (pick works and order), `--voices`, `--speed`,
`--pad` (inter-sentence pause), `--bg` (background image),
`--preview-frame N` (check the layout of one frame). Voices are documented in
[references/voices.md](references/voices.md).

## How it works

1. `fetch_corpus.py` downloads Gutenberg texts and cuts each work's front
   matter, leaving clean story text.
2. `build_video.py` splits the texts into passages/sentences, picks enough
   content to fill the target duration, then for each sentence synthesises
   speech (Kokoro), renders one parchment frame (PIL), and encodes a short
   mp4 (ffmpeg). Segments are concatenated into the final video, and the
   SRT/manifest/thumbnail are written.
3. All steps are resumable: cached audio, frames and segments are reused, so
   re-runs after a failure or a tweak are cheap.

## Credits and licensing

- Texts: Project Gutenberg public domain (Gutenberg license terms apply; the
  manifest records the source works).
- Voices: [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (Apache-2.0).
- Skill scripts: MIT.
