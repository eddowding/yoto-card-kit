#!/usr/bin/env python3
"""Build a 748x1248 Yoto MYO sticker from a folder of 16x16 track icons.

The constraint that shapes the whole design: only about the top 21% of the card
is visible once it is pushed into the player (~262px of 1248). So the title
lives up there and nothing below it is load-bearing.

Icons sit on dark rounded tiles because they are drawn for the player's dark
screen — pale subjects (white mice, blue whales) disappear on a cream card.

  cardart.py <icons-dir> <out.png> "<Title>" "<Subtitle>" <theme>
"""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 748, 1248
VISIBLE = int(H * 0.21)          # ~262px — everything readable must be above this

THEMES = {
    "donaldson": dict(bg=(250, 246, 236), band=(30, 92, 78), band_text=(255, 252, 244),
                      sub=(150, 214, 196), tile=(38, 34, 46), caption=(92, 86, 80)),
    "pooh":      dict(bg=(252, 244, 226), band=(150, 84, 24), band_text=(255, 250, 238),
                      sub=(246, 200, 110), tile=(40, 32, 28), caption=(104, 78, 52)),
}

FONT_DIR = "/System/Library/Fonts/Supplemental"


def font(name, size):
    for cand in (f"{FONT_DIR}/{name}", f"/System/Library/Fonts/{name}"):
        if os.path.exists(cand):
            try:
                return ImageFont.truetype(cand, size)
            except OSError:
                pass
    return ImageFont.load_default()


def fit_lines(draw, text, fnt_name, max_size, min_size, max_w, max_lines):
    """Largest size at which `text` wraps into <= max_lines within max_w."""
    words = text.split()
    for size in range(max_size, min_size - 1, -2):
        f = font(fnt_name, size)
        lines, cur = [], ""
        for word in words:
            trial = f"{cur} {word}".strip()
            if draw.textlength(trial, font=f) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        if len(lines) <= max_lines and all(draw.textlength(l, font=f) <= max_w for l in lines):
            return f, lines
    return font(fnt_name, min_size), [text]


def rounded_tile(size, radius, colour):
    tile = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(tile).rounded_rectangle([0, 0, size - 1, size - 1], radius, fill=colour + (255,))
    return tile


def main():
    icons_dir, out, title, subtitle, theme_name = sys.argv[1:6]
    t = THEMES[theme_name]

    # Only real icons — square and a multiple of 16. Icon folders tend to
    # accumulate cover-square.png and the previous card art, and globbing *.png
    # silently lays them into the grid and miscounts the tracks.
    files, skipped = [], []
    for f in sorted(glob.glob(f"{icons_dir}/*.png")):
        w, h = Image.open(f).size
        (files if (w == h and w % 16 == 0 and w <= 336) else skipped).append(f)
    if skipped:
        print(f"skipped {len(skipped)} non-icon file(s): "
              + ", ".join(os.path.basename(s) for s in skipped))
    if not files:
        raise SystemExit(f"no icons in {icons_dir}")

    card = Image.new("RGB", (W, H), t["bg"])
    d = ImageDraw.Draw(card)

    # --- visible band: title + subtitle, all inside the top 21% ---
    d.rectangle([0, 0, W, VISIBLE], fill=t["band"])
    d.rectangle([0, VISIBLE - 7, W, VISIBLE], fill=t["sub"])

    tf, tlines = fit_lines(d, title, "Avenir Next.ttc", 84, 40, W - 90, 2)
    sf = font("Avenir Next.ttc", 27)
    line_h = tf.size + 10
    block_h = len(tlines) * line_h + 40
    y = (VISIBLE - 7 - block_h) // 2
    for line in tlines:
        d.text(((W - d.textlength(line, font=tf)) // 2, y), line, font=tf, fill=t["band_text"])
        y += line_h
    y += 6
    d.text(((W - d.textlength(subtitle, font=sf)) // 2, y), subtitle, font=sf, fill=t["sub"])

    # --- icon grid below the fold ---
    n = len(files)
    cols = 4 if n > 9 else 3
    rows = (n + cols - 1) // cols
    margin, gap = 56, 22
    tile_px = min((W - 2 * margin - (cols - 1) * gap) // cols,
                  (H - VISIBLE - 130 - (rows - 1) * gap) // rows)
    grid_w = cols * tile_px + (cols - 1) * gap
    x0 = (W - grid_w) // 2
    y0 = VISIBLE + 54
    cf = font("Avenir Next.ttc", 20)

    for i, f in enumerate(files):
        r, c = divmod(i, cols)
        in_row = min(cols, n - r * cols)          # centre a short final row
        row_x0 = x0 + (grid_w - (in_row * tile_px + (in_row - 1) * gap)) // 2
        x = row_x0 + c * (tile_px + gap)
        y = y0 + r * (tile_px + gap)
        card.paste(rounded_tile(tile_px, tile_px // 5, t["tile"]), (x, y),
                   rounded_tile(tile_px, tile_px // 5, t["tile"]))
        pad = tile_px // 8
        icon = Image.open(f).convert("RGBA").resize((tile_px - 2 * pad,) * 2, Image.NEAREST)
        card.paste(icon, (x + pad, y + pad), icon)

    foot = f"{n} tracks"
    d.text(((W - d.textlength(foot, font=cf)) // 2, y0 + rows * (tile_px + gap) + 12),
           foot, font=cf, fill=t["caption"])

    card.save(out)
    print(f"{out}  {card.size}  {n} icons, {cols}x{rows} @ {tile_px}px, title in top {VISIBLE}px")


if __name__ == "__main__":
    main()
