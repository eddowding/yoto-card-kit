---
name: yoto
description: "Turn an album, audiobook or long recording into a Yoto Make Your Own card — download the source, cut it into tracks by silence, verify the boundaries against a transcript, source or draw 16x16 track icons, build the card art. Covers the specs and the failure modes."
tools_required: [Bash, Read, Write, WebFetch]
---

# /yoto — Build a Make Your Own card from source audio

Takes one long audio or video file and produces everything a Yoto MYO card
needs: numbered track files, a 16×16 icon per track, and card art.

```
/yoto <url-or-file>          # full pipeline
/yoto icons <track list>     # icon sourcing only
/yoto art <folder>           # card art only
```

Two helper scripts live in `bin/` of this repo — `transcribe.sh` (step 2) and
`cardart.py` (step 5). Everything else is a few lines of ffmpeg or Pillow
written on the spot; there's nothing to install beyond the requirements in the
README.

**Trim only — don't clean up the audio.** No denoise, no EQ, no loudness
normalisation. The source is the source.

---

## 0. Get the source

```bash
yt-dlp -f "bestvideo[height<=1080]+bestaudio" -o "%(title)s.%(ext)s" <url>   # keep video if the sleeve is on screen
yt-dlp -x --audio-format m4a -o "%(title)s.%(ext)s" <url>                    # audio only
```

Keep the video when the upload shows the record sleeve — it's often the best
available scan of the cover (see §5).

If a download fails with `Unable to extract`, run `brew upgrade yt-dlp` before
debugging anything else. YouTube breaks it every few weeks.

---

## 1. Find the track boundaries

Start with silence detection, but don't trust it alone.

```bash
ffmpeg -i SRC -af "silencedetect=noise=-30dB:d=0.5" -f null - 2>&1 | grep silence_
```

**The threshold matters more than you'd think.** On a vinyl rip the surface
noise sits above −40 dB, so `-40dB` finds almost nothing — on one 21-minute
album side it returned a single hit. `-30dB` returned 42. Neither number is the
answer: the real gaps are the *longest* ones.

Sort the gaps by duration and look at the distribution. Real track breaks
cluster at 2–7s; mid-song pauses are 0.5–2s. Take the count you need (n tracks
→ n−1 boundaries) from the top.

This still misjudges some. On one album: a 7s gap turned out to be *inside* a
song, a 1.8s gap that looked intra-song was a real break, and a 35s "track"
appeared that was just a pause in a spoken-word piece. So verify by content.

## 2. Verify the boundaries against a transcript

```bash
bin/transcribe.sh SRC out/ 600     # 10-minute chunks
# -> out/transcript.txt, lines of "<absolute seconds>\t<text>"
```

Then match the transcript against the sleeve tracklist around each candidate
gap. That's what settles the boundaries.

**Why chunks:** whisper base.en falls into a repetition loop on music and long
runs — on one full-side pass it emitted the same line for nine straight minutes
and silently poisoned the entire back half. Chunking bounds the damage to one
chunk, and each chunk's timestamps are shifted by its start time so the output
still reads as one continuous transcript.

Transcribing short clips at each candidate boundary instead also works, but
it's worse: you have to know the boundaries before you can check them, which is
the thing you're trying to find out. A full chunked pass gives you the whole
tracklist at once.

## 3. Cut

Cut at the **midpoint of each silence**, and stream-copy so there's no
re-encode:

```bash
ffmpeg -ss $START -to $END -i SRC -vn -c:a copy \
  -metadata "title=$TITLE" -metadata "artist=$ARTIST" \
  -metadata "album=$ALBUM" -metadata "album_artist=$ALBUM" \
  -metadata "date=$YEAR" -metadata "track=$N/$TOTAL" -metadata "disc=1" \
  "$(printf %02d $N) $TITLE.m4a"
```

AAC frames are ~23ms, so stream-copy is accurate enough — no reason to
re-encode and lose quality.

**Check every cut lands in silence.** This catches clipped words without
listening to the whole thing:

```bash
for f in *.m4a; do
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  head=$(ffmpeg -hide_banner -t 0.6 -i "$f" -af volumedetect -f null - 2>&1 | grep -o 'mean_volume: [-0-9.]* dB')
  tail=$(ffmpeg -hide_banner -ss $(echo "$d-0.6"|bc) -i "$f" -af volumedetect -f null - 2>&1 | grep -o 'mean_volume: [-0-9.]* dB')
  printf "%-40s %s | %s\n" "$f" "$head" "$tail"
done
```

Every head and tail should be ≤ −40 dB. Anything louder means a cut landed
mid-word.

`-af volumedetect` prints at info level — **don't use `-v error`**, or you get
empty output and think it passed.

Number tracks `01`–`NN` across the whole album, not per side. One card holds
both sides.

---

## 4. Track icons

**Specs** ([Yoto support](https://support.yotoplay.com/en-US/how-to-add-custom-icons-to-your-make-your-own-cards-21689), [yoto.dev](https://yoto.dev/icons/uploading-icons/)):

- 16×16 pixels, PNG or GIF, transparent background
- **Avoid black — it doesn't display.** A black background is therefore
  harmless (it reads as transparent); a black *subject* disappears.
- Anything larger is auto-downscaled to 16×16, which turns photos into smudges.
  Draw at 16×16 or use real pixel art.

### Sourcing from yotoicons.com

Community library, free, no API needed — plain `curl` works.

```bash
curl -s -A "Mozilla/5.0" "https://yotoicons.com/icons?category=&tag=hedgehog" -o out.html
```

The page embeds full metadata in an onclick handler, so you get the artist and
download count without fetching any images:

```
populate_icon_modal('<id>', '<category>', '<tag1>', '<tag2>', '<artist>', '<downloads>')
```

Images are at `https://yotoicons.com/static/uploads/<id>.png`.

Gotchas:

- Some icons are stored **upscaled** (256, 320, 336px). They're always exact
  multiples of 16, so `Image.resize((16,16), NEAREST)` restores them losslessly.
  Always normalise before use.
- Tags are noisy free text. "mouse" returns mostly Mickey Mouse; "hedgehog" is
  40% Sonic; "frog" pulls in unrelated book scenes. Filter with an exclusion
  list of brand names, then **look at the results** — sorting by download count
  surfaces popular franchise icons, not the best match.
- Check for opaque backgrounds before shipping: an icon that's 100% opaque
  prints as a filled square on the player.

```python
px=list(Image.open(f).convert('RGBA').getdata())
opaque=sum(1 for p in px if p[3]>200)                      # ==256 means solid background
black =sum(1 for p in px if p[3]>200 and max(p[:3])<12)    # >8 means it'll vanish
```

### Drawing the gaps

Expect roughly 20–25% of tracks to have no usable community icon. Draw those as
explicit pixel grids rather than downscaling artwork:

```python
P={'.':None,'W':(245,245,238),'Y':(246,176,46),'D':(52,46,60)}
ROWS=["................","......WWWW......", ...]    # 16 strings of 16 chars
assert len(ROWS)==16 and all(len(r)==16 for r in ROWS)
```

Keep the darkest colour above ~(50,45,40) so nothing hits the no-black rule.
Render at 8× to judge it — 16×16 is unreadable on a screen at actual size but
perfectly clear on the player.

**Name every icon file identically to its audio file** (`04 Nathaniel
Gnat.png` ↔ `04 Nathaniel Gnat.m4a`). The upload is a manual per-track click;
matching names remove all the guesswork.

---

## 5. Cover and card art

### Cover from the video

If the source video shows the sleeve, it beats anything findable online. Detect
the sleeve edges rather than eyeballing a crop:

```python
dark=(frame.sum(axis=2)<690)           # sleeve is darker than the white surround
rows=np.where(dark.sum(axis=1)>40)[0]; cols=np.where(dark.sum(axis=0)>40)[0]
```

**Uploaders often paste emoji or channel branding over the artwork** in every
frame, so there's no clean frame to grab. Check before assuming; then mask and
inpaint. Without cv2, `scipy.ndimage.distance_transform_edt(mask,
return_indices=True)` gives a nearest-neighbour fill that's invisible on plain
paper:

```python
ind=ndimage.distance_transform_edt(mask,return_indices=True,return_distances=False)
for c in range(3): filled[:,:,c]=a[:,:,c][tuple(ind)]
```

Bound the mask tightly — nearby printed text is often the same colour as the
overlay.

### Card art

Recommended sticker size is **748×1248**. The critical constraint isn't in
Yoto's docs:

**Only about the top 21% of the card is visible once it's in the player.**
(Measured from a photo of an inserted card: visible height ÷ full height at the
748:1248 aspect. Treat as approximate.) In a 1248px design that's the top
~262px.

So: **title in the top 262px, everything else below it.** A design with the
title centred vertically is unreadable in the slot.

A grid of the track icons makes good card art — it says what's on the card at a
glance. Put each icon on a **dark rounded tile**: the icons are drawn for a dark
screen, and pale subjects (white birds, white mice) vanish on a cream card.
Tiles fix the contrast and echo the player's display.

```bash
bin/cardart.py <icons-dir> <out.png> "<Title>" "<Subtitle>" <theme>
```

Themes are a dict at the top of the file — add one per card project rather than
passing six colours on the command line.

It filters the icons folder to square multiples of 16, because those folders
accumulate `cover-square.png` and the previous card art, and a bare `*.png` glob
lays them into the grid and miscounts the tracks.

---

## 6. Upload

Audio limits: **MP3 or AAC/M4A**, under 1 hour and ~100MB per file, up to 100
files and 500MB per card. A double album is typically ~40MB, so space is never
the constraint.

1. [my.yotoplay.com](https://my.yotoplay.com) → **Add Playlist**, set title and author
2. Drag all the tracks in at once — the `01`–`NN` prefixes preserve the order;
   spot-check where side 2 begins
3. Upload the cover image
4. Per track: `+` → **Upload Icon** → the matching PNG (this is the slow part)
5. Three-dot menu → **Link To A Card**, insert a blank MYO card, press LINK

There's a documented API
(`api.yotoplay.com/media/displayIcons/user/me/upload`), but it needs a bearer
token — for a single card, manual clicking is faster than getting credentials.

---

## Checklist

- [ ] Source downloaded; video kept if the sleeve is on screen
- [ ] Boundaries from silence detection **and** confirmed against a chunked transcript
- [ ] All cuts stream-copied; head and tail of every file ≤ −40 dB
- [ ] Audio trimmed only — no denoise, EQ or loudness processing
- [ ] Tracks numbered across the whole album, tagged `n/total`
- [ ] Icons 16×16, transparent, none opaque or black-dominant
- [ ] Icon filenames match audio filenames exactly
- [ ] Card art title inside the top ~21%
- [ ] Working files deleted (whisper model chunks, WAVs, video frames — easily 250MB+)
