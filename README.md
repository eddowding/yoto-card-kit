# yoto-card-kit

Make your own [Yoto](https://yotoplay.com) card from an album, an audiobook, or
anything else long — without doing the fiddly bits yourself.

Give it a YouTube link or an audio file. You get numbered tracks, an icon for
every track, and card art, ready to upload.

![A finished card in the Yoto app: card art made from the track icons, and a
tracklist with a matching icon on every track](docs/example.png)

## Install (once)

```bash
git clone https://github.com/eddowding/yoto-card-kit.git
mkdir -p ~/.claude/skills && cp -r yoto-card-kit/skills/yoto ~/.claude/skills/
```

## Use

In [Claude Code](https://claude.com/claude-code):

```
/yoto https://www.youtube.com/watch?v=...
```

It installs anything it needs, splits the recording into tracks, checks the
cuts, finds or draws an icon per track, and builds the card art. Then it walks
you through the upload at [my.yotoplay.com](https://my.yotoplay.com) — that part
is manual clicking, there's no way round it.

Expect an hour or so, most of it waiting.

---

Needs a Mac or Linux machine and Claude Code. MIT licensed. Not affiliated with
Yoto.
