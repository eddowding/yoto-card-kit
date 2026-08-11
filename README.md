# yoto-card-kit

Turn an album, audiobook or long recording into a [Yoto](https://yotoplay.com)
Make Your Own card.

Feed it one long file — a vinyl rip off YouTube, an audiobook, a radio
recording — and you end up with numbered track files, a 16×16 icon for every
track, and printable card art. Roughly an evening's work for a card your kid
can play a hundred times.

It's a Claude Code skill plus two scripts. The skill is the instructions:
where to cut, what the specs are, and the dozen things that go wrong. The
scripts do the two jobs that are fiddly to write from scratch.

## Requirements

- macOS or Linux
- `ffmpeg` and Python 3 with Pillow
- `yt-dlp` if your source is on YouTube
- `whisper-cpp` if you want the transcript check (recommended for spoken word)
- [Claude Code](https://claude.com/claude-code) if you want it to drive

```bash
brew install ffmpeg yt-dlp whisper-cpp
pip3 install pillow

# whisper model, ~148MB, one time
mkdir -p ~/.local/share/whisper
curl -sL -o ~/.local/share/whisper/ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
```

## Install

```bash
git clone https://github.com/eddowding/yoto-card-kit.git
cd yoto-card-kit

# make the skill available to Claude Code
mkdir -p ~/.claude/skills
cp -r skills/yoto ~/.claude/skills/

# put the scripts on your PATH (add to ~/.zshrc to keep it)
export PATH="$PWD/bin:$PATH"
```

Then in Claude Code:

```
/yoto https://www.youtube.com/watch?v=...
```

It downloads the source, finds the track boundaries, cuts them, sources or
draws an icon per track, and builds the card art. You upload the result at
[my.yotoplay.com](https://my.yotoplay.com) — that last step is manual clicking,
there's no way round it.

Or read [`skills/yoto/SKILL.md`](skills/yoto/SKILL.md) and do it by hand. It's
written to be followed by a person as well as a machine.

## The two scripts

Both are standalone — no Claude needed.

### `bin/transcribe.sh`

```bash
transcribe.sh source.m4a outdir/ [chunk_seconds]
```

Transcribes a long recording and writes `outdir/transcript.txt` as
`<absolute seconds>\t<text>`, so you can look up what's being said at any
candidate cut point and check it isn't mid-sentence.

It works in fixed chunks (10 minutes by default) because whisper falls into
repetition loops on music and long runs — one loop can silently poison
everything after it. Chunking keeps the damage to one chunk, and the timestamps
are stitched back to absolute time so it still reads as one transcript.

Set `WHISPER_MODEL` if your model lives somewhere other than
`~/.local/share/whisper/ggml-base.en.bin`.

### `bin/cardart.py`

```bash
cardart.py <icons-dir> <out.png> "<Title>" "<Subtitle>" <theme>
```

Builds a 748×1248 sticker from a folder of 16×16 track icons: a title band and
a grid of the icons, which tells you what's on the card at a glance.

The thing that isn't in Yoto's docs: **only about the top 21% of the card is
visible once it's in the player**, so the title goes up there and everything
below it is decoration. Icons sit on dark rounded tiles because they're drawn
for the player's dark screen — pale subjects vanish on a cream card.

Two themes ship in the file (`pooh`, `donaldson`). Add your own to the `THEMES`
dict at the top; it's six colours.

## Licence

MIT. Not affiliated with Yoto.
