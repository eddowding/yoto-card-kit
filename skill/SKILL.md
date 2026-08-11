---
name: yoto
description: "Turn a long recording into a Yoto Make Your Own card — split into tracks by silence, verify boundaries by transcript, restore hissy audio, source or draw 16x16 track icons, build card art. Covers the specs and the failure modes."
last_updated: 2026-08-11
tools_required: [Bash, Read, Write]
---

# /yoto — Build a Make Your Own card

Turn one long audio file into everything a Yoto MYO card needs: numbered tracks,
a 16×16 icon per track, and card art.

```
/yoto <file>              # full pipeline
/yoto icons <tracks>      # icon sourcing only
/yoto art <folder>        # card art only
```

The tools in `bin/` do the mechanical parts. This file is the judgement: what
goes wrong, and how to tell.

---

## 0. Source

Start from audio you have the right to put on a card — your own transfers off
vinyl, tape or CD, your own recordings, or something bought or public domain.
Yoto MYO exists for exactly this: private cards for your own household. Whatever
the source, work from the best-quality file you can get, because every stage
below either preserves quality or loses it, and none adds it back.

If the file came from a low-bitrate stream, `yoto-analyse` will tell you what you
are working with before you invest any effort in it.

---

## 1. Find the track boundaries

Silence detection is a starting point, not an answer.

```bash
yoto-split SOURCE --list
```

**The threshold matters more than you'd expect.** On a vinyl or tape transfer the
surface noise sits above −40 dB, so a −40 dB threshold finds almost nothing —
on one 21-minute album side it returned a single hit. −30 dB returned 42. Neither
number is right in general; look at where the durations *cluster*. Real track
breaks group at 2–7 s, intra-track pauses at 0.5–2 s.

**Ranking by length still misjudges some.** On the same album a 7 s gap turned
out to be *inside* one song, a 1.8 s gap that looked intra-song was a real break,
and a 35 s "track" was a pause in a spoken-word piece. If the sorted durations
taper smoothly with no cliff, there is no clean answer in the silence alone.

## 2. Confirm by transcript

```bash
brew install whisper-cpp
curl -sL -o ggml-base.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin
ffmpeg -i SRC -vn -ac 1 -ar 16000 -c:a pcm_s16le audio.wav

for t in 430 640 780 900; do
  ffmpeg -ss $t -t 25 -i audio.wav -c copy clip_$t.wav -y
  echo "=== ${t}s ==="; whisper-cli -m ggml-base.en.bin -f clip_$t.wav -nt --no-prints
done
```

**Transcribe short clips at each candidate boundary, never the whole file.**
whisper base.en falls into a repetition loop on music: on a full-side run it
emitted the same line for nine straight minutes and made the back half of the
transcript worthless. Short clips never loop. Treat anything after the first
repeated line as garbage.

Match what each clip says against the tracklist. That settles it.

## 3. Cut

```bash
yoto-split SOURCE --tracks 12 --album "Title" --artist "Reader" \
           --titles "First,Second,Third"
```

Cuts land at the midpoint of each silence and stream-copy — AAC frames are ~23 ms,
so there is no reason to re-encode and lose a generation.

Every cut is verified automatically by measuring the first and last 0.6 s of each
track; anything above −40 dB means a cut landed mid-word. Note that
`-af volumedetect` prints at *info* level — running it with `-v error` gives empty
output that looks exactly like a pass.

Number tracks `01`–`NN` across the whole album, not per side. One card holds both.

---

## 4. Restore the audio (optional, but usually worth it)

Old transfers and low-bitrate sources are dull and hissy, and a Yoto's small mono
speaker is unforgiving. **Measure before you reach for a filter:**

```bash
yoto-analyse "track.m4a"
```

The characteristic spoken-word problem is that SNR collapses with frequency —
around 50 dB at 300 Hz–1 kHz but under 20 dB at 8–15 kHz. That tilt is what you
hear as hiss, and it is what to treat.

```bash
yoto-clean *.m4a
yoto-analyse --compare "original.m4a" "original [clean].m4a"
```

Three things that are easy to get wrong here:

**Do not trust IIR band measurements.** A 2-pole filter's skirts leak several dB
of neighbouring energy into the band you think you are measuring. On one file
that leak read as strong sub-80 Hz rumble and a 50 Hz mains hum; a proper FFT
showed the LF content was already ~30 dB below the voice and the "hum" was only
+2.7 dB over its neighbours — no tone at all. Two filters were being applied to
problems that did not exist.

**Do not add a compressor by reflex.** It is the obvious move and it measurably
backfires on narrow-loudness-range material: by pulling up the gaps it lifts the
noise floor, which cost 4–7 dB of SNR across 60 Hz–1 kHz in testing and left
those bands *worse than untreated*, while halving the benefit up top.

**Denoise artefacts are invisible to every measurement above.** Spectral
subtraction can leave a watery, swirling quality that no SNR figure reflects.
Listen to a quiet passage between lines, not to the speech. If it swirls, drop
`--nr` to 16 or 12.

Keep the output bitrate above the source (the default 128k is fine) so you are
not stacking a second generation of lossy coding on the first.

---

## 5. Track icons

**Specs** ([Yoto support](https://support.yotoplay.com/en-US/how-to-add-custom-icons-to-your-make-your-own-cards-21689),
[yoto.dev](https://yoto.dev/icons/uploading-icons/)): 16×16 px, PNG or GIF,
transparent background.

- **Black does not display.** A black *background* is harmless — it reads as
  transparent. A black *subject* vanishes.
- Anything larger is auto-downscaled to 16×16, which turns photos into smudges.
  Draw at 16×16 or use real pixel art.

```bash
yoto-icons search hedgehog
yoto-icons get 6896 -o "04 Nathaniel Gnat.png" --preview
yoto-icons check icons/            # audit the whole set before uploading
```

**Gotchas:**

- Some icons are stored **upscaled** (256, 320, 336 px). They are always exact
  multiples of 16, so `resize((16,16), NEAREST)` restores them losslessly.
  Normalise before use.
- Tags are noisy free text. "mouse" returns mostly Mickey; "hedgehog" is around
  40% Sonic; "frog" pulls in unrelated book scenes. Sorting by download count
  surfaces *popular franchise* icons, not the best match. Filter, then look.
- Check for opaque backgrounds — a 100%-opaque icon prints as a filled square.

### Drawing the gaps

Expect roughly 20–25% of tracks to have no usable community icon (on one album,
4 of 16 — the title character, a gnat, a haggis, a weasel). Draw those as explicit
pixel grids rather than downscaling art:

```python
P = {'.': None, 'W': (245,245,238), 'Y': (246,176,46), 'D': (52,46,60)}
ROWS = ["................", "......WWWW......", ...]   # 16 strings of 16 chars
assert len(ROWS) == 16 and all(len(r) == 16 for r in ROWS)
```

Keep the darkest colour above ~(50,45,40) so nothing hits the no-black rule.
Render at 8× to judge — 16×16 is unreadable on a monitor and perfectly clear on
the player.

**Name every icon file identically to its audio file** (`04 Nathaniel Gnat.png` ↔
`04 Nathaniel Gnat.m4a`). Upload is a manual per-track click; matching names
remove all guesswork.

---

## 6. Cover and card art

Recommended sticker size is **748×1248**. The critical constraint is not in the
docs:

**Only about the top 21% of the card is visible once it is in the player** —
roughly the top 262 px of 1248. (Measured from a photo of an inserted card; treat
as approximate.) A title centred vertically is unreadable in the slot.

```bash
yoto-cardart --title "Album" --subtitle "read by X" --icons icons/ -o card-art.png
yoto-cardart --check existing.png     # crops to what actually shows
```

A grid of the track icons makes good art for the lower portion — it says what is
on the card at a glance. Put each icon on a **dark rounded tile**: the icons are
drawn for a dark screen, so pale subjects vanish on a light card.

If your source was a video showing the sleeve, that is often the best available
scan of the cover. Detect the sleeve edges rather than eyeballing a crop:

```python
dark = (frame.sum(axis=2) < 690)
rows = np.where(dark.sum(axis=1) > 40)[0]; cols = np.where(dark.sum(axis=0) > 40)[0]
```

Uploaders often paste emoji or channel branding over the artwork in *every*
frame, so there may be no clean frame to grab. Mask and inpaint — with no cv2,
`scipy.ndimage.distance_transform_edt(mask, return_indices=True)` gives a
nearest-neighbour fill that is invisible on plain paper. Bound the mask tightly;
nearby printed text is often the same colour as the overlay.

---

## 7. Upload

Limits: **MP3 or AAC/M4A**, under 1 hour and ~100 MB per file, up to 100 files
and 500 MB per card. A double album is ~40 MB, so space is never the constraint.

1. [my.yotoplay.com](https://my.yotoplay.com) → **Add Playlist**, set title and author
2. Drag all tracks in at once — the `01`–`NN` prefixes preserve order; spot-check
   where side 2 begins
3. Upload the cover image
4. Per track: `+` → **Upload Icon** → the matching PNG (this is the slow part)
5. Three-dot menu → **Link To A Card**, insert a blank MYO card, press LINK

There is a documented API (`api.yotoplay.com/media/displayIcons/user/me/upload`)
but for a single card, manual clicking beats obtaining credentials.

---

## Checklist

- [ ] Boundaries from silence detection **and** confirmed by transcript clips
- [ ] All cuts stream-copied; head/tail of every file ≤ −40 dB
- [ ] If restored: `--compare` shows SNR up across the board, and a quiet passage
      listened to for artefacts
- [ ] Tracks numbered across the whole album, tagged `n/total`
- [ ] Icons 16×16, transparent, none opaque or black-dominant
- [ ] Icon filenames match audio filenames exactly
- [ ] Card art title inside the top ~21%
- [ ] Working files deleted (whisper model, WAVs, frames — easily 250 MB)
