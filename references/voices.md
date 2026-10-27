# Voices

Speech comes from **Kokoro-82M** (hexgrad/Kokoro-82M, Apache-2.0): a small,
very natural open TTS that runs offline on CPU. Voice ids encode accent and
gender: first letter `a` = American English, `b` = British English; `f`/`m` =
female/male; the suffix is the voice name.

## Default rotation (12 voices)

`build_video.py` rotates through these by default, one voice per passage:

- `af_heart` - American English, female, the flagship voice
- `am_adam` - American English, male
- `bf_emma` - British English, female
- `bm_george` - British English, male
- `af_bella` - American English, female
- `am_michael` - American English, male
- `bf_alice` - British English, female
- `bm_daniel` - British English, male
- `af_nicole` - American English, female
- `am_eric` - American English, male
- `bf_isabella` - British English, female
- `bm_lewis` - British English, male

## Choosing voices

```
python build_video.py --voices af_heart,bf_emma,am_adam --minutes 30 --out out/x.mp4
```

Other English voices available in the same model include `af_alloy`,
`af_jessica`, `af_kore`, `af_river`, `af_sarah`, `af_sky`, `am_echo`,
`am_fenrir`, `am_liam`, `am_onyx`, `am_puck`, `bf_lily`. All voice `.pt`
files are downloaded together with the model weights.

## Pacing

`--speed 1.0` is natural reading pace. For a "slow listening" build use
`--speed 0.9`; raise `--pad` (the silence between sentences) for more thinking
time, e.g. `--speed 0.9 --pad 0.8`. The on-screen accent label is derived
from the voice id, so custom voices need an entry in `DEFAULT_VOICES` inside
`scripts/build_video.py` to get a pretty label (they still work without one -
the raw voice id is shown).

## Notes on other engines

If Kokoro is missing and the network allows it, edge-tts (Microsoft's free
neural TTS, 40+ English voices) is the easiest alternative; note it needs
unblocked websocket access to `speech.platform.bing.com`. Local spaCy model
`en_core_web_sm` is required by misaki for the AmericanEnglish G2P path.
