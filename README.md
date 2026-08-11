# yoto-card-kit

Command-line tools for building [Yoto](https://yotoplay.com) Make Your Own cards
from a long recording: split it into tracks, restore tired audio, find or vet the
16×16 track icons, and lay out card art that is still readable once the card is
in the player.

Yoto MYO cards are the officially supported way to put your own audio on the
platform — home recordings, your own transfers off vinyl, tape or CD, audio you
have bought, public-domain material. That is what this is for. Start from
something you have the right to use, and from the best-quality copy you can get:
every stage here either preserves quality or costs you some, and none of them
add it back.

Most of what is here is not code so much as accumulated knowledge of where this
process goes wrong. The interesting failures are in [`skill/SKILL.md`](skill/SKILL.md).

---

## Install

```bash
git clone <this repo> && cd yoto-card-kit
export PATH="$PWD/bin:$PATH"

brew install ffmpeg          # required by everything
pip3 install numpy pillow    # required by yoto-analyse / yoto-icons / yoto-cardart
brew install whisper-cpp     # optional, for confirming track boundaries
```

For use as a Claude Code skill, symlink or copy `skill/SKILL.md` into
`~/.claude/skills/yoto/`.

---

## The tools

### `yoto-split` — cut one long file into numbered tracks

```bash
yoto-split album.m4a --list                    # rank the gaps, cut nothing
yoto-split album.m4a --tracks 12 --album "Title" --artist "Reader"
yoto-split album.m4a --at 61.5,180.2,301.8     # place the cuts yourself
```

Silence detection is a starting point, not an answer — the longest gap in a file
is often a dramatic pause mid-track, and a real break can be under two seconds.
So `--list` shows you the distribution and you decide. Cuts land at the midpoint
of each silence and stream-copy, so there is no re-encode. Every cut is then
verified by measuring the first and last 0.6 s of each track: anything above
−40 dB means it landed mid-word.

### `yoto-analyse` — measure what is actually wrong

```bash
yoto-analyse track.m4a
yoto-analyse --compare original.m4a "original [clean].m4a"
```

Splits the file into quiet frames and loud frames, takes an averaged FFT of each,
and reports signal-to-noise per band. That is the number that distinguishes a
hiss problem from a rumble problem from a tonal hum — three things that need
different fixes and are routinely confused.

```
  band (Hz)       noise   signal      SNR
  150-300           2.4     51.4     49.0
  300-1k           -2.4     50.8     53.3
  2k-4k           -12.7     22.6     35.3
  4k-8k           -11.5     13.7     25.2  <- marginal
  8k-15k           -8.5     10.0     18.5  <- noisy
  tonal hum: none above +6 dB (any LF energy is broadband, not a tone)
```

It uses an FFT rather than ffmpeg's `highpass`/`lowpass` for a specific reason: a
2-pole filter's skirts leak several dB from neighbouring bands, and on a voice
recording — where nearly all the energy sits at 150 Hz–1 kHz — that leak reads
convincingly as rumble that is not there. Chasing it means high-pass filtering a
problem you do not have.

### `yoto-clean` — restore dull, hissy speech

```bash
yoto-clean *.m4a                # writes "NAME [clean].m4a" alongside
yoto-clean --nr 16 track.m4a    # gentler denoise
yoto-clean --dry-run track.m4a  # print the chain and stop
```

High-pass, spectral denoise, a small cut at 250 Hz, a presence lift at 2.8 kHz,
then two-pass loudness normalisation to −16 LUFS / −1.5 dBTP. On a 64 kbps mono
source this measured +17.5 dB SNR at 8–15 kHz and +10 dB at 2–8 kHz, with no
meaningful loss of signal in any band.

There is deliberately **no compressor**. It is the obvious thing to add and it
backfires on narrow-loudness-range material: by pulling up the gaps it lifts the
noise floor, which cost 4–7 dB of SNR across 60 Hz–1 kHz in testing and left
those bands worse than untreated, while halving the gain up top. If you add one
back, prove it with `--compare` first.

One thing no measurement here catches: spectral denoise can leave a watery,
swirling quality. Listen to a quiet passage *between* lines, not to the speech.
If it swirls, lower `--nr`.

### `yoto-icons` — find and vet 16×16 track icons

```bash
yoto-icons search hedgehog
yoto-icons get 6896 -o "04 Nathaniel Gnat.png" --preview
yoto-icons check icons/
```

Searches the community library at [yotoicons.com](https://yotoicons.com),
normalises upscaled icons back to 16×16 losslessly (they are always exact
multiples of 16), and checks the two things that ruin an icon on the player:
black subjects, which do not display at all, and fully opaque images, which print
as a filled square.

Tags are free text and search quality reflects that — "mouse" returns mostly
Mickey, "hedgehog" is largely Sonic. Sorting by popularity surfaces franchise art
rather than the best match, so filter and then look.

### `yoto-cardart` — 748×1248 art that survives the slot

```bash
yoto-cardart --title "Album" --subtitle "read by X" --icons icons/ -o card-art.png
yoto-cardart --check existing-art.png
```

The constraint that governs the whole design is not in Yoto's documentation:
**only about the top 21% of the card is visible once it is inserted** — roughly
the top 262 px of 1248. A title centred vertically, which is what every template
gives you, is completely hidden in normal use. So the title goes in a band at the
very top and the icon grid lives below it, on dark tiles, because icons drawn for
a dark screen disappear against a light card.

`--check` crops any existing design to the visible strip so you can see what
actually shows on the shelf.

---

## A worked pass

```bash
yoto-split source.m4a --list
yoto-split source.m4a --tracks 7 -o tracks/ --album "Album" --artist "Reader"

yoto-analyse tracks/*.m4a                       # what needs doing, if anything
yoto-clean -o final/ tracks/*.m4a
yoto-analyse --compare tracks/01*.m4a final/01*.m4a

yoto-icons search bear
yoto-icons get 1234 -o "icons/01 First Track.png" --preview
yoto-icons check icons/

yoto-cardart --title "Album" --subtitle "read by Reader" \
             --icons icons/ -o card-art-748x1248.png
```

Then upload at [my.yotoplay.com](https://my.yotoplay.com) — Add Playlist, drag
the tracks in, upload the cover, add each icon, then **Link To A Card** with a
blank MYO card inserted. The per-track icon click is the slow part; matching
filenames between audio and icons make it mechanical.

---

## Requirements

| | |
|---|---|
| ffmpeg / ffprobe | all tools |
| Python 3.9+ | all except `yoto-split` (stdlib only) |
| numpy | `yoto-analyse` |
| pillow | `yoto-icons`, `yoto-cardart` |
| whisper-cpp | optional — confirming track boundaries |

Tested on macOS with ffmpeg 7 and Python 3.13.

## Licence

MIT. See [LICENSE](LICENSE).
