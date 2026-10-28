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

Public-domain English, interleaved for variety. `fetch_corpus.py` ships a
catalog of ten works:

- Aesop's Fables (Gutenberg #28)
- The Happy Prince and Other Tales - Oscar Wilde (Gutenberg #902)
- Grimms' Fairy Tales (Gutenberg #2591)
- Alice's Adventures in Wonderland (Gutenberg #11)
- Treasure Island (Gutenberg #120)
- Black Beauty (Gutenberg #271)
- The Call of the Wild (Gutenberg #215)
- Walden (Gutenberg #205)
- Pride and Prejudice (Gutenberg #1342)
- The Adventures of Sherlock Holmes (Gutenberg #1661)

Up to 28 English voices rotate across a video: American and British English,
male and female (the full Kokoro-82M English set; `--voices` picks any subset).

## Themes

Twenty parchment scenes ship in `scripts/themes.py`, each with its own paper,
ink and vignette colours (all pairs meet WCAG AA contrast):

| theme | scene |
|-------|-------|
| classic | warm aged parchment |
| midnight | deep blue night |
| rose | dusty rose |
| fog | grey mist |
| sea | teal ocean |
| dream | lavender dusk |
| earth | warm brown |
| frost | icy pale blue |
| forest | sage green |
| regency | soft blush paper |
| autumn | warm amber paper |
| ink | paper white, black ink |
| linen | warm ivory |
| plum | dusty plum |
| sage | soft sage |
| sky | pale sky |
| copper | burnished copper |
| charcoal | charcoal board, cream ink |
| seafoam | deep sea green, pale ink |
| wine | deep wine, blush ink |

Omit `--bg` and the theme paper is generated on the fly. Pass an explicit
`--bg` image to use any background you like.

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

# pick a scene theme (default: classic)
python scripts/build_video.py --minutes 60 --theme midnight --out out/night.mp4

# quick smoke test
python scripts/build_video.py --minutes 1 --out out/smoke.mp4

# build a whole themed collection: one episode per catalog work
python scripts/make_collection.py --out out/collection --minutes 63
```

Useful flags: `--content` (pick works and order), `--voices`, `--theme`,
`--fps` (static slides look identical at 8-12 fps and encode much faster),
`--speed`, `--pad` (inter-sentence pause), `--bg` (background image),
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
