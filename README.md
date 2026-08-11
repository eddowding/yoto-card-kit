# yoto-card-kit

Two scripts for building [Yoto](https://yotoplay.com) Make Your Own cards.

**The method lives in the skill, not here:**
`~/Sites/Odin/Operations/Claude/skills/operations/yoto/SKILL.md`.

That is deliberate. Nearly every step of this pipeline — silence-ranked
trimming, cut verification, icon search and vetting — is a dozen lines of ffmpeg
or Pillow that regenerates cleanly from a written description. It was tested: a
throwaway rebuild of the icon tool from the skill alone reproduced the original
almost line for line, down to the same four vetting thresholds. Keeping those
scripts around buys nothing and costs a second copy to maintain.

These two are here because they do not regenerate:

### `bin/transcribe.sh`

```bash
transcribe.sh source.m4a outdir/ [chunk_seconds]
```

Transcribes a long recording in fixed chunks and emits absolute-timestamped
lines, so you can look up what is being said at any candidate cut point.

Chunking is the whole point. whisper base.en falls into a repetition loop on
music and long runs — on one album side it emitted the same line for nine
straight minutes and silently poisoned everything after it. Chunks bound the
damage, and the per-chunk JSON offsets are shifted back to absolute time so the
output still reads as one transcript.

Needs `whisper-cpp` and the base.en model:

```bash
brew install whisper-cpp
mkdir -p ~/.local/share/whisper
curl -sL -o ~/.local/share/whisper/ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

Override the location with `WHISPER_MODEL` if you keep it elsewhere.

### `bin/cardart.py`

```bash
cardart.py <icons-dir> <out.png> "<Title>" "<Subtitle>" <theme>
```

Builds a 748×1248 sticker from a folder of 16×16 track icons.

The design constraint is not in Yoto's documentation: **only about the top 21%
of the card is visible once it is in the player** (~262 px of 1248), so the title
band lives up there and nothing below it is load-bearing. Icons sit on dark
rounded tiles because they are drawn for the player's dark screen — pale
subjects vanish on a cream card.

The layout work is the part worth keeping: titles wrap to two lines at the
largest size that fits, tile size is computed from the space available, and the
grid widens to four columns past nine icons. A rebuild from the prose
description got all of that wrong.

Themes are in the file — `pooh`, `donaldson`. Add one per card project.

## Requirements

ffmpeg, Python 3 with Pillow, and whisper-cpp for the transcriber.

## Licence

MIT.
