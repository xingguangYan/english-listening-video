---
name: english-listening-video
description: "Create English listening-practice videos, a parchment background with centred English subtitles, narration by a rotating cast of offline Kokoro TTS voices, assembled with ffmpeg into an .mp4 plus SRT and manifest. Use when the user asks for an English listening / dictation / study video, a spoken-English practice video with multiple voices or accents."
---

# English Listening Video

Turns public-domain English texts into listening-practice videos: one parchment
page per sentence, the sentence centred on screen, spoken by a rotating cast of
English voices. Output is an .mp4 plus matching .srt, a manifest with the full
timeline, and a thumbnail.

## Requirements

- ffmpeg + ffprobe on PATH, Python 3.10+ with `Pillow` and `numpy`.
- A Kokoro-capable Python interpreter (has `kokoro`, `torch`, `misaki`, an
  English spaCy model, and the `hexgrad/Kokoro-82M` weights in the HF cache).
  `build_video.py` auto-detects one under `$CODEX_HOME/skills/*/.venv`;
  override with `--tts-python X:\path\python.exe` or the `KOKORO_PYTHON` env
  var. The TTS step is fully offline once the weights are cached.

## Workflow

1. Get content. `python scripts/fetch_corpus.py --out corpus` downloads and
   cleans public-domain texts (Aesop, Grimm, Wilde, Doyle) from Gutenberg,
   cutting each work's front matter. Any other `.txt` works the same way:
   one work per file, paragraphs separated by blank lines.
2. Build. `python scripts/build_video.py --minutes 60 --out out/hour.mp4`
   passes over `corpus/*.txt` (use `--content a.txt b.txt` to pick works and
   their order; works are interleaved round-robin for variety). One pass per
   sentence: Kokoro TTS -> PIL frame -> ffmpeg segment -> concat. Builds
   resume: cached audio/frames/segments are reused.

Helpful flags: `--minutes` (target length), `--voices` (Kokoro voice ids, see
[references/voices.md](references/voices.md)), `--speed` (speech rate),
`--pad` (pause between sentences), `--tts-workers/--workers` (parallelism),
`--preview-frame N` (render one frame png for layout checks), `--no-intro`.

## Layout and pacing defaults

1920x1080, 24fps, x264 stillimage + AAC 160k; static parchment frames compress
to a small file. Work title top, passage title under it, sentence centred,
accent label bottom ("American English · Heart"). Voices rotate per passage so
listeners hear many accents; `--bg` accepts any other background image
(regenerate the bundled one with `scripts/make_parchment.py --seed N`).

## Publishing

See [references/deployment.md](references/deployment.md) for pushing the skill
to GitHub and attaching the video as a Release asset.

## Notes

- Content is public domain; keep attribution in the manifest and description.
- If Kokoro is unavailable, any other TTS can be wired in by replacing the
  `run_kokoro_tts` call; the rest of the pipeline is TTS-agnostic (it just
  needs one wav + duration per sentence).
- Long sentences auto-shrink to fit; sentences under 4 words are merged so
  interjections are never dropped.
